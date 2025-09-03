# security_app/core/runner/__init__.py
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import os
from typing import Any, Dict, List, Tuple

from security_app.config import CMD_MARKER, DEFAULT_LOGS_DIR
from security_app.core.command import run_command  # <-- dùng cho pilot run
from security_app.core.logger import RunLogger
from security_app.models import CmdResult, Rule
from security_app.settings import Settings

from .extract import _pre_extract_rules
from .merge import _merge_and_log
from .plan import _prepare_tasks
from .tuner import auto_guess_workers  # <-- mới
from .workers import _workers


def _pilot_execute(
    tasks: list[tuple[int, Rule, list[str]]],
    agg: dict[int, dict[str, Any]],
    pending: dict[int, int],
    settings: Settings,
    logger: RunLogger,
    budget: int
) -> tuple[list[tuple[int, Rule, list[str]]], list[float], list[dict[str, Any]]]:
    """
    Chạy tuần tự 'budget' task đầu để lấy mẫu duration.
    Trả về (tasks_còn_lại, sample_durations, results_đã_hoàn_tất_rule).
    """
    if budget <= 0 or not tasks:
        return tasks, [], []

    take = min(budget, len(tasks))
    sample = tasks[:take]
    rest = tasks[take:]
    sample_durs: list[float] = []
    completed: list[dict[str, Any]] = []

    for (idx, _rule, chunk) in sample:
        # chunk là list các cmd (per_command=True thì độ dài 1)
        ran = [run_command(c, settings) for c in chunk]
        sample_durs.extend([r.duration_sec for r in ran if r is not None])

        state = agg[idx]
        state["ran"].extend(ran)
        pending[idx] -= 1
        if pending[idx] == 0:
            completed.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            del agg[idx]
            del pending[idx]

    return rest, sample_durs, completed

def run_all_rules(
    rules: list[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,
    use_processes: bool = False,
    settings: Settings = None,
    per_command: bool = True,
) -> list[dict[str, Any]]:
    """Thực thi toàn bộ rule với concurrency; chỉ main thread ghi log (single-writer)."""
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)

    # 1) Trích xuất & chuẩn bị task
    pre = _pre_extract_rules(rules, marker=CMD_MARKER)
    tasks, agg, pending = _prepare_tasks(pre, per_command=per_command)

    results: list[dict[str, Any]] = []

    # Log ngay những rule không có allowed-cmd
    for idx, state in list(agg.items()):
        if pending.get(idx, 0) == 0:
            results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            pending.pop(idx, None)

    # 2) Pilot run + tự chọn số worker nếu chưa chỉ định
    sample_durs: list[float] = []
    if tasks and workers is None:
        # ngân sách pilot:  max(8, 2*CPU) nhưng không quá 24 task
        cpu = os.cpu_count() or 4
        budget = min(24, max(8, 2 * cpu))
        tasks, sample_durs, completed = _pilot_execute(tasks, agg, pending, settings, logger, budget)
        results.extend(completed)
        # Sau pilot, chọn số worker dựa trên độ dài task còn lại
        workers = auto_guess_workers(len(tasks), use_processes, sample_durs)

    # 3) Chạy song song phần còn lại
    if tasks:
        Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        sample = [max(1, len(t[2]))*0.1 for t in tasks[:50]]  # giả định 0.1s/lệnh nếu chưa có thống kê thật
        guessed = auto_guess_workers(len(tasks), use_processes, sample)
        max_workers = workers or guessed
        with Executor(max_workers=max_workers) as ex:
            fut2idx = {}
            for task in tasks:
                idx, rule, chunk = task
                fut = ex.submit(_workers, (idx, rule, chunk, settings))
                fut2idx[fut] = idx

            for fut in as_completed(fut2idx):
                idx = fut2idx[fut]
                try:
                    _idx, ran_part = fut.result()
                except Exception as e:
                    ran_part = [CmdResult(cmd="(worker error)", returncode=None, stdout="", stderr=str(e), duration_sec=0.0, ok=False)]

                state = agg[idx]
                state["ran"].extend(ran_part)
                pending[idx] -= 1
                if pending[idx] == 0:
                    results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
                    del agg[idx]
                    del pending[idx]

    # 4) Ổn định thứ tự theo index rule
    results.sort(key=lambda x: x["rule_index"])
    return results

