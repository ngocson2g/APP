# security_app/core/runner/__init__.py
"""
Main runner module - Điều phối song song: LPT + waves + phân làn CPU-ish/IO-ish
- Phân loại theo token đầu + pattern (deep grep/find, quét /var/log, glob rộng)
- Gửi CPU-ish vào ProcessPool, IO-ish vào ThreadPool (hai executor chạy đồng thời)
- Ghi metrics theo wave (throughput, timeout rate, p50/p95) + in progress bar & ETA
"""
from __future__ import annotations

from dataclasses import replace as _dc_replace

import os
import re
import statistics
import sys
import time
from concurrent.futures import (ProcessPoolExecutor, ThreadPoolExecutor,
                                as_completed)
from typing import Any, Tuple

from security_app.config import DEFAULT_LOGS_DIR
from security_app.core.logger import RunLogger
from security_app.models import CmdResult, Rule
from security_app.settings import Settings
from security_app.utils.text import _bar

from .command_port import CommandRunner, default_command_runner
from .merge import _merge_and_log
from .metrics import WaveMetricsSink
from .scheduler import build_scheduled_tasks, suggest_wave_size
from .tuner import auto_guess_workers

# ======== AIMD Tuning (config qua ENV, có giá trị mặc định an toàn) ========
AIMD_TIMEOUT_RATE = float(os.getenv("SECAPP_AIMD_TIMEOUT_RATE", "0.15"))  # 15% timeouts coi là nghẽn
AIMD_P95_SPIKE    = float(os.getenv("SECAPP_AIMD_P95_SPIKE", "0.50"))     # p95 tăng >50% coi là nghẽn
AIMD_BETA         = float(os.getenv("SECAPP_AIMD_BETA", "0.70"))          # multiplicative decrease ×0.7
AIMD_ADD          = int(os.getenv("SECAPP_AIMD_ADD", "1"))                # additive increase +1
WAVE_SCALE_MIN    = float(os.getenv("SECAPP_WAVE_SCALE_MIN", "0.50"))     # thu nhỏ wave tối đa 50%
WAVE_SCALE_MAX    = float(os.getenv("SECAPP_WAVE_SCALE_MAX", "2.00"))     # phóng to wave tối đa 2x


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


def _count_timeouts(results: list[CmdResult]) -> int:
    n = 0
    for r in results or []:
        if r.returncode is None and ("TIMEOUT" in (r.stderr or "").upper()):
            n += 1
    return n


# ---------- Worker payload ----------
def _workers_chunk(payload: tuple[int, Rule, list[str], Settings, CommandRunner]) -> tuple[int, list[CmdResult]]:
    """Worker xử lý 1 chunk (n lệnh) bằng runner được tiêm vào."""
    idx, _rule, allowed_cmds, settings, run_fn = payload
    # run_fn là hàm top-level picklable: (cmd, settings) -> CmdResult
    rule_id = _rule.id
    
    results: list[CmdResult] = [run_fn(cmd, settings, rule_id) for cmd in allowed_cmds]
    return idx, results


# ---------- Hàm chính ----------
def run_all_rules(
    rules: list[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,          # nếu set → là “trần” cho từng pool
    use_processes: bool = False,         # giữ tham số cũ (không dùng khi dual-pool)
    settings: Settings | None = None,
    per_command: bool = True,            # giữ tham số cũ, chunking động ở scheduler
    command_runner: CommandRunner | None = None,  # NEW: DI port
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
    
    run_fn: CommandRunner = command_runner or default_command_runner

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

    # 3) Khởi tạo sink ghi metrics theo wave (SRP)
    sink = WaveMetricsSink(run_dir=logger.run_dir, total_cmds=total_cmds_planned)

    cmds_done = 0
    ema_thr: float | None = None  # EMA cho throughput để mượt ETA
    wave_no = 0
    
    
    # ======== Biến trạng thái cho AIMD & timeout động ========
    cap_cpu_cur = max(1, int(guessed_cap_cpu))  # bắt đầu từ ước lượng ban đầu
    cap_io_cur  = max(1, int(guessed_cap_io))
    # (bảo thủ) trần mềm: không vượt quá ước lượng ban đầu
    cap_cpu_max = max(1, int(guessed_cap_cpu))
    cap_io_max  = max(1, int(guessed_cap_io))
    wave_scale  = 1.0
    prev_p95: float | None = None
    #no_congest_waves = 0


    # 4) Chạy theo waves
    while tasks:
        # Lấy một wave hợp lý
        wave_size_base = suggest_wave_size(len(tasks))
        # áp dụng scale động (AIMD) và kẹp an toàn 8..128
        wave_size = int(max(8, min(128, wave_size_base * wave_scale)))
        wave_tasks = tasks[:wave_size]
        tasks = tasks[wave_size:]

        #Thu thập rule_id trong wave
        rule_ids_in_wave = sorted(list(set(
            task[1].id for task in wave_tasks if task[1] and task[1].id
        )))
        
        # Phân làn
        cpu_wave: list[Tuple[int, Rule, list[str], float]] = []
        io_wave:  list[Tuple[int, Rule, list[str], float]] = []
        for item in wave_tasks:
            idx, rule, chunk, est = item
            (cpu_wave if _classify_chunk(chunk) == "cpu" else io_wave).append(item)

        # Số worker mỗi làn (≤ số task còn lại của làn), dùng “cap hiện tại” của AIMD
        use_workers_cpu = max(1, min(cap_cpu_cur, len(cpu_wave))) if cpu_wave else 1
        use_workers_io  = max(1, min(cap_io_cur,  len(io_wave)))  if io_wave  else 1
        # Submit song song
        t0 = time.time()
        futures = {}
        cmds_in_wave_cpu = 0
        cmds_in_wave_io  = 0

        with ProcessPoolExecutor(max_workers=use_workers_cpu or 1) as ex_cpu, \
             ThreadPoolExecutor(max_workers=use_workers_io or 1) as ex_io:

            for (idx, rule, chunk, _est) in cpu_wave:
                fut = ex_cpu.submit(_workers_chunk, (idx, rule, chunk, settings, run_fn))
                futures[fut] = ("cpu", idx, len(chunk))
                cmds_in_wave_cpu += len(chunk)

            for (idx, rule, chunk, _est) in io_wave:
                fut = ex_io.submit(_workers_chunk, (idx, rule, chunk, settings, run_fn))
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

                # Lưu vào aggregator  agg:   {idx: {"rule": Rule, "denied": [CmdResult], "ran": []}}
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

        # ---- Timeout động cho WAVE KẾ TIẾP (theo p95 thực tế) ----
        try:
            t_dyn = None
            # dùng lại heuristic 3×p95 + 1s, clamp 5..60
            if p95 and p95 > 0:
                t_dyn = p95 * 3.0 + 1.0
                if t_dyn < 5.0:  
                    t_dyn = 5.0
                if t_dyn > 60.0: 
                    t_dyn = 60.0
            if t_dyn:
                # FIX: Settings là frozen dataclass → tạo bản mới thay vì mutate
                settings = _dc_replace(settings, shell_timeout=float(t_dyn))
        except Exception:
            pass

        # ---- AIMD: điều chỉnh cap_cpu/io và wave_scale cho WAVE KẾ TIẾP ----
        congested = (timeout_rate > AIMD_TIMEOUT_RATE) or (
            (prev_p95 is not None) and (p95 > prev_p95 * (1.0 + AIMD_P95_SPIKE))
        )
        if congested:
            # multiplicative decrease
            cap_cpu_cur = max(1, int(cap_cpu_cur * AIMD_BETA))
            cap_io_cur  = max(1, int(cap_io_cur  * AIMD_BETA))
            wave_scale  = max(WAVE_SCALE_MIN, wave_scale * AIMD_BETA)
            #no_congest_waves = 0
        else:
            # additive increase (không vượt trần mềm)
            if cap_cpu_cur < cap_cpu_max:
                cap_cpu_cur = min(cap_cpu_max, cap_cpu_cur + AIMD_ADD)
            if cap_io_cur < cap_io_max:
                cap_io_cur  = min(cap_io_max,  cap_io_cur  + AIMD_ADD)
            wave_scale = min(WAVE_SCALE_MAX, wave_scale + 0.10)
            #no_congest_waves += 1
        prev_p95 = p95

        # (tuỳ chọn) In debug ngắn gọn để quan sát điều chỉnh
        # print(f"[aimd] next caps: cpu={cap_cpu_cur} io={cap_io_cur} wave_scale={wave_scale:.2f} timeout={settings.shell_timeout}")
 

       # Ghi metrics (SRP: giao cho sink)
        sink.add_wave(
            wave_no + 1,
            started_at=t0, ended_at=t1,
            cmds_total=cmds_in_wave_total,
            thr_total=thr_total, thr_cpu=thr_cpu, thr_io=thr_io,
            timeouts=timeouts_total, timeout_rate=timeout_rate,
            p50=p50, p95=p95,
            rule_ids=rule_ids_in_wave,
        )

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
            f"p50={p50:.3f}s p95={p95:.3f}s | "
            f"Wcpu={use_workers_cpu} Wio={use_workers_io} ws×={wave_scale:.2f} | "
            f"tmo={settings.shell_timeout if settings.shell_timeout else 0:.1f}s | "
            f"ETA ~ {eta_min:02d}:{eta_s:02d}  [{bar}]"
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
    sink.finish()
    return results
