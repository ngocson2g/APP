# security_app/core/runner/__init__.py
"""
Main runner module - Điều phối song song: LPT + waves + phân làn CPU-ish/IO-ish
- Phân loại theo token đầu + pattern (deep grep/find, quét /var/log, glob rộng)
- Gửi CPU-ish vào ProcessPool, IO-ish vào ThreadPool (hai executor chạy đồng thời)
- Ghi metrics theo wave (throughput, timeout rate, p50/p95) + in progress bar & ETA
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import json
import os
import re
import statistics
import time
from typing import Any, Dict, List, Tuple

from security_app.config import CMD_MARKER, DEFAULT_LOGS_DIR
from security_app.core.command import run_command
from security_app.core.logger import RunLogger
from security_app.models import CmdResult, Rule
from security_app.settings import Settings
from security_app.utils.text import _bar

from .merge import _merge_and_log
from .scheduler import build_scheduled_tasks, suggest_wave_size
from .tuner import auto_guess_workers

import sys


# ---------- Phân loại CPU-ish / IO-ish ----------
_CPUISH_TOKENS = {
    # tệp/chuỗi, duyệt file, hash…
    "find", "grep", "egrep", "fgrep", "awk", "sed", "sort",
    "sha1sum", "sha224sum", "sha256sum", "sha384sum", "sha512sum",
    "md5sum", "zgrep", "xzgrep", "rg"
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
    """
    Heuristic nhẹ để chia làn:
    - token đầu thuộc danh sách CPU-ish
    - hoặc pattern đặc trưng deep scan / log scan / glob
    """
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
    return "cpu" if any(_is_cpuish_cmd(c) for c in (chunk_cmds or [])) else "io"

def _count_types(tasks: list[Tuple[int, Rule, list[str], float]]) -> tuple[int, int]:
    cpu = io = 0
    for _idx, _rule, chunk, _est in tasks:
        if _classify_chunk(chunk) == "cpu":
            cpu += 1
        else:
            io += 1
    return cpu, io

def _count_timeouts(results: list[CmdResult]) -> int:
    n = 0
    for r in results or []:
        if r.returncode is None and ("TIMEOUT" in (r.stderr or "").upper()):
            n += 1
    return n


# ---------- Worker payload ----------
def _workers_chunk(payload: tuple[int, Rule, list[str], Settings]) -> tuple[int, list[CmdResult]]:
    """Worker xử lý 1 chunk (n lệnh)."""
    idx, _rule, allowed_cmds, settings = payload
    results: list[CmdResult] = [run_command(cmd, settings) for cmd in allowed_cmds]
    return idx, results


# ---------- Hàm chính ----------
def run_all_rules(
    rules: list[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,          # nếu set → là “trần” cho từng pool
    use_processes: bool = False,         # giữ tham số cũ (không dùng khi dual-pool)
    settings: Settings | None = None,
    per_command: bool = True,            # giữ tham số cũ, chunking động ở scheduler
) -> list[dict[str, Any]]:
    """
    Thực thi toàn bộ rule với LPT + waves + dual-pool (ProcessPool + ThreadPool),
    đồng thời:
      - Ghi metrics theo wave: throughput (cmd/s), timeout rate, p50/p95
      - In progress bar & ETA cho CLI
      - Flush an toàn 'waves.json' vào logs/<RUN_ID>/ mỗi wave
    """
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)
    settings = settings or Settings(
        shell_timeout=None,
        retry_attempts=0,
        retry_delay_sec=0.0,
        retry_on_timeout=False,
        exec_cwd=None,
        clean_env=True,
    )

    # 1) Lập danh sách task theo LPT (đã deny/allowed + chunking động)
    tasks, agg, pending = build_scheduled_tasks(rules, logs_base_dir=log_base_dir)
    results: list[dict[str, Any]] = []

    # Log ngay rule không còn task (chỉ có deny)
    for idx, state in list(agg.items()):
        if pending.get(idx, 0) == 0:
            results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            pending.pop(idx, None)

    # Snapshot để đếm tổng số cmd kế hoạch (phục vụ progress/ETA)
    tasks_all_snapshot = list(tasks)
    total_cmds_planned = 0
    for (_i, _r, ch, _e) in tasks_all_snapshot:
        total_cmds_planned += len(ch)

    # 2) Ước lượng sơ bộ từ 'est' của task để đoán workers
    cpu_ests = []
    io_ests = []
    for (_i, _r, ch, est) in tasks:
        (cpu_ests if _classify_chunk(ch) == "cpu" else io_ests).append(float(est or 0.05))
    sample_cpu = cpu_ests[:64]  # đủ đại diện
    sample_io  = io_ests[:64]

    guessed_cap_cpu = auto_guess_workers(len([1 for _i,_r,ch,_e in tasks if _classify_chunk(ch) == "cpu"]),
                                         use_processes=True, sample_durs=sample_cpu)
    guessed_cap_io  = auto_guess_workers(len([1 for _i,_r,ch,_e in tasks if _classify_chunk(ch) == "io"]),
                                         use_processes=False, sample_durs=sample_io)

    # Nếu user truyền --workers, coi như trần cho mỗi pool
    if workers and workers > 0:
        guessed_cap_cpu = min(guessed_cap_cpu, int(workers))
        guessed_cap_io  = min(guessed_cap_io, int(workers))

    # 3) Khởi tạo metrics lưu waves.json
    metrics = {
        "run_id": os.path.basename(logger.run_dir),
        "started_at": time.time(),
        "total_cmds": int(total_cmds_planned),
        "waves": [],
    }
    def _write_metrics():
        p_tmp = os.path.join(logger.run_dir, "waves.json.tmp")
        p_dst = os.path.join(logger.run_dir, "waves.json")
        with open(p_tmp, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        os.replace(p_tmp, p_dst)

    cmds_done = 0
    ema_thr: float | None = None  # EMA cho throughput để mượt ETA
    wave_no = 0

    # 4) Chạy theo waves
    while tasks:
        # Lấy một wave hợp lý
        wave_size = suggest_wave_size(len(tasks))
        wave_tasks = tasks[:wave_size]
        tasks = tasks[wave_size:]

        # Phân làn
        cpu_wave: list[Tuple[int, Rule, list[str], float]] = []
        io_wave:  list[Tuple[int, Rule, list[str], float]] = []
        for item in wave_tasks:
            idx, rule, chunk, est = item
            (cpu_wave if _classify_chunk(chunk) == "cpu" else io_wave).append(item)

        # Số worker mỗi làn (≤ số task còn lại của làn)
        use_workers_cpu = max(1, min(guessed_cap_cpu, len(cpu_wave))) if cpu_wave else 1
        use_workers_io  = max(1, min(guessed_cap_io,  len(io_wave)))  if io_wave  else 1

        # Submit song song
        t0 = time.time()
        futures = {}
        cmds_in_wave_cpu = 0
        cmds_in_wave_io  = 0

        with ProcessPoolExecutor(max_workers=use_workers_cpu or 1) as ex_cpu, \
             ThreadPoolExecutor(max_workers=use_workers_io or 1) as ex_io:

            for (idx, rule, chunk, _est) in cpu_wave:
                fut = ex_cpu.submit(_workers_chunk, (idx, rule, chunk, settings))
                futures[fut] = ("cpu", idx, len(chunk))
                cmds_in_wave_cpu += len(chunk)

            for (idx, rule, chunk, _est) in io_wave:
                fut = ex_io.submit(_workers_chunk, (idx, rule, chunk, settings))
                futures[fut] = ("io", idx, len(chunk))
                cmds_in_wave_io += len(chunk)

            # Thu kết quả
            durations_wave: list[float] = []
            timeouts_cpu = timeouts_io = 0

            for fut in as_completed(list(futures.keys())):
                lane, idx, _chunk_len = futures[fut]
                try:
                    _idx, ran_part = fut.result()
                except Exception as e:
                    # Không nổ wave: wrap exception thành CmdResult để log
                    ran_part = [CmdResult(cmd="(worker error)", returncode=None, stdout="", stderr=str(e), duration_sec=0.0)]

                # Lưu vào aggregator
                state = agg[idx]
                state["ran"].extend(ran_part)
                pending[idx] = max(0, pending[idx] - 1)

                # Thống kê theo làn
                if lane == "cpu":
                    timeouts_cpu += _count_timeouts(ran_part)
                else:
                    timeouts_io += _count_timeouts(ran_part)

                # Thu duration cho p50/p95
                for x in (ran_part or []):
                    try:
                        durations_wave.append(float(getattr(x, "duration_sec", 0.0) or 0.0))
                    except Exception:
                        pass

                # Nếu rule đã xong → merge & log
                if pending[idx] == 0:
                    rec = _merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger)
                    results.append(rec)

        # Kết thúc wave → tính metrics
        t1 = time.time()
        elapsed = max(1e-9, t1 - t0)

        thr_cpu = (cmds_in_wave_cpu / elapsed) if cmds_in_wave_cpu else 0.0
        thr_io  = (cmds_in_wave_io  / elapsed) if cmds_in_wave_io  else 0.0
        cmds_in_wave_total = cmds_in_wave_cpu + cmds_in_wave_io
        thr_total = (cmds_in_wave_total / elapsed) if cmds_in_wave_total else 0.0

        timeouts_total = timeouts_cpu + timeouts_io
        timeout_rate = (timeouts_total / max(1, cmds_in_wave_total)) if cmds_in_wave_total else 0.0

        if durations_wave:
            p50 = statistics.median(durations_wave)
            try:
                # quantiles n=20 → p95 ~ q[18] (5% upper tail)
                p95 = statistics.quantiles(durations_wave, n=20)[18]
            except Exception:
                p95 = max(durations_wave)
        else:
            p50 = p95 = 0.0

        # Ghi metrics JSON
        metrics["waves"].append({
            "wave": wave_no + 1,
            "started_at": t0,
            "ended_at": t1,
            "elapsed_sec": round(elapsed, 6),
            "cmds": int(cmds_in_wave_total),
            "thr_total": round(thr_total, 6),
            "thr_cpu": round(thr_cpu, 6),
            "thr_io": round(thr_io, 6),
            "timeouts": int(timeouts_total),
            "timeout_rate": round(timeout_rate, 6),
            "p50": round(p50, 6),
            "p95": round(p95, 6),
        })
        metrics["updated_at"] = time.time()
        _write_metrics()

        # In progress + ETA (CLI)
        cmds_done += cmds_in_wave_total
        ema_thr = thr_total if ema_thr is None else (0.3 * thr_total + 0.7 * ema_thr)
        remaining = max(0, total_cmds_planned - cmds_done)
        eta_sec = (remaining / ema_thr) if (ema_thr and ema_thr > 1e-9) and remaining else 0.0
        eta_min, eta_s = divmod(int(eta_sec), 60)
        bar = _bar(cmds_done, total_cmds_planned, 30) if total_cmds_planned else ""

        line = (
            f"[wave {wave_no+1}] cmds={cmds_in_wave_total} | {elapsed:.2f}s | "
            f"thr={thr_total:.2f} cmd/s | to={timeout_rate*100:.1f}% | "
            f"p50={p50:.3f}s p95={p95:.3f}s | ETA ~ {eta_min:02d}:{eta_s:02d}  [{bar}]"
        )
        if sys.stdout.isatty():
            print(line, end="\r", flush=True)   # cập nhật cùng 1 dòng
        else:
            print(line, flush=True)             # nếu redirect ra file: mỗi wave 1 dòng
        wave_no += 1

    if sys.stdout.isatty():
        print()  # xuống dòng sau khi kết thúc để không dính prompt
    
    # 5) Ổn định thứ tự theo index rule trước khi trả về
    results.sort(key=lambda x: x["rule_index"])

    # Đánh dấu kết thúc
    metrics["finished_at"] = time.time()
    _write_metrics()
    return results
