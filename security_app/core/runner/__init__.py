# security_app/core/runner/__init__.py
"""
Main runner module - Điều phối song song: LPT + waves + phân làn CPU-ish/IO-ish
- Phân loại theo token đầu + pattern (deep grep/find, quét /var/log, glob rộng)
- Gửi CPU-ish vào ProcessPool, IO-ish vào ThreadPool (hai executor chạy đồng thời)
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import os, time, re
from typing import Any, Dict, List, Tuple

from security_app.config import CMD_MARKER, DEFAULT_LOGS_DIR
from security_app.core.command import run_command
from security_app.core.logger import RunLogger
from security_app.models import CmdResult, Rule
from security_app.settings import Settings

from .merge import _merge_and_log
from .tuner import auto_guess_workers
from .scheduler import build_scheduled_tasks, suggest_wave_size


# ---------- Phân loại CPU-ish / IO-ish ----------
_CPUISH_TOKENS = {
    "find", "grep", "egrep", "fgrep", "awk", "sed", "sort",
    "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum",
    "md5sum"
}
_CPUISH_PATTERNS = [
    re.compile(r"\bgrep\s+-R\b", re.I),            # grep đệ quy
    re.compile(r"\bfind\s+/\b", re.I),             # find từ gốc
    re.compile(r"/var/log\b", re.I),               # quét log
    re.compile(r"[\*\?\[]"),                       # glob rộng
]

def _first_token(cmd: str) -> str:
    return (cmd.strip().split() or [""])[0].lower()

def _is_cpuish_cmd(cmd: str) -> bool:
    s = cmd.strip()
    tok = _first_token(s)
    if tok in _CPUISH_TOKENS:
        return True
    for rx in _CPUISH_PATTERNS:
        if rx.search(s):
            return True
    return False

def _classify_chunk(chunk_cmds: list[str]) -> str:
    """Trả về 'cpu' nếu bất kỳ lệnh nào trong chunk là CPU-ish, ngược lại 'io'."""
    return "cpu" if any(_is_cpuish_cmd(c) for c in chunk_cmds or []) else "io"


# ---------- Pilot chạy tuần tự lấy mẫu ----------
def _pilot_execute_chunks(
    tasks: list[tuple[int, Rule, list[str], float]],
    agg: dict[int, dict[str, Any]],
    pending: dict[int, int],
    settings: Settings,
    logger: RunLogger,
    budget: int,
) -> tuple[list[tuple[int, Rule, list[str], float]], list[float], list[float], list[dict[str, Any]]]:
    """
    Chạy tuần tự 'budget' task đầu để lấy mẫu duration theo từng loại (cpu/io).
    Mỗi task là 1 chunk (list lệnh) → chạy lần lượt trong chunk.
    """
    if budget <= 0 or not tasks:
        return tasks, [], [], []

    take = min(budget, len(tasks))
    sample, rest = tasks[:take], tasks[take:]
    sample_cpu: list[float] = []
    sample_io: list[float] = []
    completed: list[dict[str, Any]] = []

    for (idx, _rule, chunk, _est) in sample:
        ran = [run_command(c, settings) for c in chunk]
        durs = [r.duration_sec for r in ran if r is not None]
        if _classify_chunk(chunk) == "cpu":
            sample_cpu.extend(durs)
        else:
            sample_io.extend(durs)

        state = agg[idx]
        state["ran"].extend(ran)
        pending[idx] -= 1
        if pending[idx] == 0:
            completed.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            del agg[idx]; del pending[idx]

    return rest, sample_cpu, sample_io, completed


def _count_timeouts(results: list[CmdResult]) -> int:
    n = 0
    for r in results or []:
        if r.returncode is None and ("TIMEOUT" in (r.stderr or "").upper()):
            n += 1
    return n


def run_all_rules(
    rules: list[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,          # nếu set → là “trần” cho từng pool
    use_processes: bool = False,          # vẫn giữ tham số cũ (không dùng khi dual-pool)
    settings: Settings = None,
    per_command: bool = True,             # giữ tham số cũ, chunking động ở scheduler
) -> list[dict[str, Any]]:
    """Thực thi toàn bộ rule với LPT + waves + dual-pool (ProcessPool + ThreadPool)."""
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)

    # 1) Lập danh sách task theo LPT (đã deny/allowed + chunking động)
    tasks, agg, pending = build_scheduled_tasks(rules, logs_base_dir=log_base_dir)
    results: list[dict[str, Any]] = []

    # Log ngay rule không còn task (chỉ có deny)
    for idx, state in list(agg.items()):
        if pending.get(idx, 0) == 0:
            results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            pending.pop(idx, None)

    # 2) Pilot + ước lượng workers riêng cho CPU/IO nếu chưa set
    sample_cpu: list[float] = []
    sample_io: list[float] = []
    if tasks and workers is None:
        cpu = os.cpu_count() or 4
        budget = min(24, max(8, 2 * cpu))
        tasks, sample_cpu, sample_io, completed = _pilot_execute_chunks(tasks, agg, pending, settings, logger, budget)
        results.extend(completed)

    # Đếm task CPU/IO còn lại để gợi ý capacity
    def _count_types(ts):
        n_cpu = n_io = 0
        for (_i, _r, ch, _e) in ts:
            if _classify_chunk(ch) == "cpu":
                n_cpu += 1
            else:
                n_io += 1
        return n_cpu, n_io

    n_cpu_all, n_io_all = _count_types(tasks)
    guessed_cap_cpu = auto_guess_workers(n_cpu_all, True, sample_cpu or [0.1])
    guessed_cap_io  = auto_guess_workers(n_io_all, False, sample_io or [0.1])

    # Nếu CLI truyền --workers, dùng như “trần” cho mỗi pool; nếu không, lấy guessed
    max_workers_cpu = min(guessed_cap_cpu, workers) if workers else guessed_cap_cpu
    max_workers_io  = min(guessed_cap_io,  workers) if workers else guessed_cap_io

    # 3) Chạy theo waves, điều chỉnh workers riêng cho mỗi pool
    if tasks:
        wave_size = suggest_wave_size(len(tasks))

        prev_throughput_cpu = None
        prev_throughput_io  = None

        while tasks:
            wave = tasks[:wave_size]
            tasks = tasks[wave_size:]

            # Phân làn
            cpu_wave = []
            io_wave  = []
            for (idx, rule, chunk, est) in wave:
                (cpu_wave if _classify_chunk(chunk) == "cpu" else io_wave).append((idx, rule, chunk, est))

            t0 = time.time()
            cmds_in_wave_cpu = 0
            cmds_in_wave_io  = 0
            timeouts_cpu = 0
            timeouts_io  = 0
            completed_this_wave: list[dict[str, Any]] = []

            # Cap không vượt số task còn lại theo từng làn
            cap_cpu = max(1, min(512, len(cpu_wave), guessed_cap_cpu))
            cap_io  = max(1, min(512, len(io_wave),  guessed_cap_io))
            use_workers_cpu = max(1, min(max_workers_cpu, cap_cpu)) if cpu_wave else 0
            use_workers_io  = max(1, min(max_workers_io,  cap_io))  if io_wave  else 0

            futures = {}
            # Chạy 2 executor song song (nếu có work)
            if use_workers_cpu or use_workers_io:
                # Nest 2 context để đóng gọn gàng
                with ProcessPoolExecutor(max_workers=use_workers_cpu or 1) as ex_cpu, \
                     ThreadPoolExecutor(max_workers=use_workers_io or 1) as ex_io:
                    for (idx, rule, chunk, _est) in cpu_wave:
                        fut = ex_cpu.submit(_workers_chunk, (idx, rule, chunk, settings))
                        futures[fut] = ("cpu", idx, len(chunk))
                    for (idx, rule, chunk, _est) in io_wave:
                        fut = ex_io.submit(_workers_chunk, (idx, rule, chunk, settings))
                        futures[fut] = ("io", idx, len(chunk))

                    for fut in as_completed(list(futures.keys())):
                        lane, idx, chunk_len = futures[fut]
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

                        if lane == "cpu":
                            cmds_in_wave_cpu += max(chunk_len, len(ran_part))
                            timeouts_cpu     += _count_timeouts(ran_part)
                        else:
                            cmds_in_wave_io  += max(chunk_len, len(ran_part))
                            timeouts_io      += _count_timeouts(ran_part)

            results.extend(completed_this_wave)
            t1 = time.time()
            elapsed = max(0.001, t1 - t0)

            # Throughput & timeout rate theo làn
            thr_cpu = (cmds_in_wave_cpu / elapsed) if cmds_in_wave_cpu else 0.0
            thr_io  = (cmds_in_wave_io  / elapsed) if cmds_in_wave_io  else 0.0
            to_rate_cpu = (timeouts_cpu / max(1, cmds_in_wave_cpu)) if cmds_in_wave_cpu else 0.0
            to_rate_io  = (timeouts_io  / max(1, cmds_in_wave_io))  if cmds_in_wave_io  else 0.0

            # ---- Auto-tuning trước wave kế tiếp ----
            def _tune(prev_thr, thr, to_rate, curr_workers, cap, tasks_left):
                next_workers = curr_workers
                # Giảm nếu timeout đáng kể
                if to_rate > 0.02 or (to_rate > 0 and tasks_left > 0):
                    next_workers = max(1, int(curr_workers * 0.75))
                # Tăng nếu không timeout và throughput tăng rõ rệt
                elif to_rate == 0.0 and prev_thr and thr > prev_thr * 1.10:
                    next_workers = int(curr_workers * 1.25)
                # Ràng buộc theo cap & số task còn
                next_workers = max(1, min(next_workers, cap, tasks_left if tasks_left > 0 else next_workers))
                return next_workers

            # Tính số task còn theo từng làn (nhìn vào tasks còn lại)
            remain_cpu, remain_io = _count_types(tasks)
            max_workers_cpu = _tune(prev_throughput_cpu, thr_cpu, to_rate_cpu, max_workers_cpu, guessed_cap_cpu, remain_cpu) if remain_cpu else max_workers_cpu
            max_workers_io  = _tune(prev_throughput_io,  thr_io,  to_rate_io,  max_workers_io,  guessed_cap_io,  remain_io)  if remain_io  else max_workers_io

            prev_throughput_cpu = thr_cpu if cmds_in_wave_cpu else prev_throughput_cpu
            prev_throughput_io  = thr_io  if cmds_in_wave_io  else prev_throughput_io

        # end while

    # 4) Ổn định thứ tự theo index rule
    results.sort(key=lambda x: x["rule_index"])
    return results


def _workers_chunk(payload: tuple[int, Rule, list[str], Settings]) -> tuple[int, list[CmdResult]]:
    """Worker xử lý 1 chunk (n lệnh)."""
    idx, _rule, allowed_cmds, settings = payload
    results: list[CmdResult] = [run_command(cmd, settings) for cmd in allowed_cmds]
    return idx, results
