# security_app/core/runner/__init__.py
"""
Main runner module - Điều phối parallel execution với auto-tuning + LPT + waves
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import os, time
from typing import Any, Dict, List, Tuple

from security_app.config import CMD_MARKER, DEFAULT_LOGS_DIR
from security_app.core.command import run_command
from security_app.core.logger import RunLogger
from security_app.models import CmdResult, Rule
from security_app.settings import Settings

from .merge import _merge_and_log
from .tuner import auto_guess_workers
from .scheduler import build_scheduled_tasks, suggest_wave_size


def _pilot_execute_chunks(
    tasks: list[tuple[int, Rule, list[str], float]],
    agg: dict[int, dict[str, Any]],
    pending: dict[int, int],
    settings: Settings,
    logger: RunLogger,
    budget: int,
) -> tuple[list[tuple[int, Rule, list[str], float]], list[float], list[dict[str, Any]]]:
    """
    Chạy tuần tự 'budget' task đầu để lấy mẫu duration.
    Task gồm chunk (list lệnh) → chạy lần lượt trong chunk.
    """
    if budget <= 0 or not tasks:
        return tasks, [], []

    take = min(budget, len(tasks))
    sample, rest = tasks[:take], tasks[take:]
    sample_durs: list[float] = []
    completed: list[dict[str, Any]] = []

    for (idx, _rule, chunk, _est) in sample:
        ran = [run_command(c, settings) for c in chunk]
        sample_durs.extend([r.duration_sec for r in ran if r is not None])

        state = agg[idx]
        state["ran"].extend(ran)
        pending[idx] -= 1
        if pending[idx] == 0:
            completed.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            del agg[idx]; del pending[idx]

    return rest, sample_durs, completed

def _count_timeouts(results: list[CmdResult]) -> int:
    n = 0
    for r in results or []:
        if r.returncode is None and ("TIMEOUT" in (r.stderr or "").upper()):
            n += 1
    return n

def run_all_rules(
    rules: list[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,
    use_processes: bool = False,
    settings: Settings = None,
    per_command: bool = True,  # giữ tham số cũ, nhưng đã thay bằng chunking động
) -> list[dict[str, Any]]:
    """Thực thi toàn bộ rule với concurrency + waves + LPT."""
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)

    # 1) Build tasks theo LPT (đã xử lý deny/allowed + chunking động)
    tasks, agg, pending = build_scheduled_tasks(rules, logs_base_dir=log_base_dir)

    results: list[dict[str, Any]] = []

    # Log ngay rule không còn task (chỉ có deny)
    for idx, state in list(agg.items()):
        if pending.get(idx, 0) == 0:
            results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            pending.pop(idx, None)

    # 2) Pilot + gợi ý workers nếu chưa set
    sample_durs: list[float] = []
    if tasks and workers is None:
        cpu = os.cpu_count() or 4
        budget = min(24, max(8, 2 * cpu))
        tasks, sample_durs, completed = _pilot_execute_chunks(tasks, agg, pending, settings, logger, budget)
        results.extend(completed)
        workers = auto_guess_workers(len(tasks), use_processes, sample_durs)

    # 3) Chạy theo waves với điều chỉnh workers giữa các wave
    if tasks:
        Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        guessed_cap = auto_guess_workers(len(tasks), use_processes, sample_durs or [0.1])

        max_workers = workers or guessed_cap
        wave_size = suggest_wave_size(len(tasks))

        prev_throughput = None

        while tasks:
            wave = tasks[:wave_size]
            tasks = tasks[wave_size:]

            t0 = time.time()
            cmds_in_wave = 0
            timeouts_in_wave = 0
            completed_this_wave: list[dict[str, Any]] = []

            with Executor(max_workers=max_workers) as ex:
                fut2idx = {}
                for (idx, rule, chunk, _est) in wave:
                    fut = ex.submit(_workers_chunk, (idx, rule, chunk, settings))
                    fut2idx[fut] = (idx, len(chunk))

                for fut in as_completed(fut2idx):
                    idx, chunk_len = fut2idx[fut]
                    try:
                        _idx, ran_part = fut.result()
                    except Exception as e:
                        ran_part = [CmdResult(cmd="(worker error)", returncode=None, stdout="", stderr=str(e), duration_sec=0.0, ok=False)]
                        chunk_len = max(chunk_len, len(ran_part))

                    state = agg[idx]
                    state["ran"].extend(ran_part)
                    pending[idx] -= 1
                    if pending[idx] == 0:
                        completed_this_wave.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
                        del agg[idx]; del pending[idx]

                    cmds_in_wave += max(chunk_len, len(ran_part))
                    timeouts_in_wave += _count_timeouts(ran_part)

            results.extend(completed_this_wave)
            t1 = time.time()
            elapsed = max(0.001, t1 - t0)
            throughput = cmds_in_wave / elapsed
            timeout_rate = (timeouts_in_wave / max(1, cmds_in_wave))

            # ---- Auto-tuning trước wave kế tiếp ----
            cap = min(512, guessed_cap, max(1, len(tasks)))  # không vượt số task còn lại
            next_workers = max_workers

            # Rule giảm khi timeout cao hoặc ≥2 TIMEOUT trong wave
            if timeout_rate > 0.02 or timeouts_in_wave >= 2:
                next_workers = max(1, int(max_workers * 0.75))
            # Rule tăng khi timeout = 0 và throughput tăng rõ rệt
            elif timeout_rate == 0.0 and prev_throughput and throughput > prev_throughput * 1.10:
                next_workers = int(max_workers * 1.25)

            # ràng buộc
            next_workers = max(1, min(next_workers, cap))
            prev_throughput = throughput
            max_workers = next_workers

        # end while

    # 4) Ổn định thứ tự theo index rule
    results.sort(key=lambda x: x["rule_index"])
    return results

def _workers_chunk(payload: tuple[int, Rule, list[str], Settings]) -> tuple[int, list[CmdResult]]:
    """Worker xử lý 1 chunk (n lệnh)."""
    idx, _rule, allowed_cmds, settings = payload
    results: list[CmdResult] = [run_command(cmd, settings) for cmd in allowed_cmds]
    return idx, results
