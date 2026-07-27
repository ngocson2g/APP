# security_app/core/estimator.py
"""
Ước lượng thời gian chạy và đề xuất cấu hình tối ưu
Sử dụng historical data và heuristic analysis
"""
from __future__ import annotations

import glob
import os
import re
import statistics
from collections.abc import Sequence

from security_app.config import DEFAULT_LOGS_DIR
from security_app.core.command_extractor import extract_all_commands
from security_app.core.runner.tuner import auto_guess_workers
from security_app.models import Rule
from security_app.policy.safety import deny_reason

# --- Heuristic base costs (seconds) theo dạng regex --
PAT_COST = [
    (re.compile(r"\bapt(-get)?\s+(install|remove|update|upgrade)\b", re.I), 5.0),
    (re.compile(r"\bdpkg\s+-l\b", re.I), 0.8),
    (re.compile(r"\bjournalctl\b", re.I), 0.8),
    (re.compile(r"\bsystemctl\b", re.I), 0.2),
    (re.compile(r"\b(find)\b", re.I), 1.2),
    (re.compile(r"\bgrep\b", re.I), 0.15),
    (re.compile(r"\b(du|ls|stat)\b", re.I), 0.06),
    (re.compile(r"\b(cat|awk|sed|cut|sort|head|tail)\b", re.I), 0.05),
    (re.compile(r"\b(sysctl|uname|id|whoami|date)\b", re.I), 0.03),
]

def _base_cost(cmd: str) -> float:
    s = cmd.strip()
    for rx, c in PAT_COST:
        if rx.search(s):
            return c
    # fallback
    toks = len(s.split())
    return 0.05 + 0.01 * max(0, toks - 2)

def _shape_multipliers(cmd: str) -> float:
    s = cmd
    mult = 1.0
    # số pipe tăng latency
    pipes = s.count("|")
    mult *= (1.0 + 0.15 * pipes)
    # đệ quy / glob
    if re.search(r"\s-[Rr]\b", s): mult *= 1.6
    if re.search(r"[\*\?\[]", s): mult *= 1.25
    # quét rộng: /var/log, /etc, / (cực rộng)
    if re.search(r"\s/var/log\b", s): mult *= 1.4
    if re.search(r"\s/etc\b", s):      mult *= 1.1
    if re.search(r"\s/(\s|$)", s):     mult *= 1.8  # nghi ngờ quét gốc
    return mult

def _first_token(cmd: str | None) -> str: # Thêm | None vào type hint
    if not cmd: # Kiểm tra None hoặc chuỗi rỗng
        return ""
    return (cmd.strip().split() or [""])[0].lower()

def _read_history(logs_base: str, max_files: int = 4000) -> dict[str, tuple[float, float, int]]:
    """
    Quét nhanh duration theo base command từ logs/<run>/rule-*.log
    Trả về: {base_cmd: (mean, p95, n)}
    """
    durations: dict[str, list[float]] = {}
    picked = 0
    for run_dir in glob.glob(os.path.join(logs_base, "*")):
        if not os.path.isdir(run_dir):
            continue
        for fp in glob.glob(os.path.join(run_dir, "rule-*.log")):
            if picked >= max_files: break
            try:
                with open(fp, encoding="utf-8", errors="ignore") as f:
                    last_cmd = None
                    for line in f:
                        line = line.rstrip("\n")
                        if line.startswith("$ "):
                            last_cmd = line[2:].strip()
                        elif " | " in line and line.endswith("s"):
                            # dòng RC=... | OK=... | 0.123s
                            m = re.search(r"([0-9.]+)s$", line)
                            if m and last_cmd:
                                d = float(m.group(1))
                                b = _first_token(last_cmd)
                                durations.setdefault(b, []).append(d)
                                last_cmd = None
                                picked += 1
                                if picked >= max_files: break
            except (OSError, ValueError) as e:
                from security_app.utils.log import internal_logger
                internal_logger.warning(f"Failed to read/parse {f}: {e}")

    out: dict[str, tuple[float, float, int]] = {}
    for b, ds in durations.items():
        if not ds: continue
        ds = [max(0.0, float(x)) for x in ds]
        mean = sum(ds)/len(ds)
        try:
            p95 = statistics.quantiles(ds, n=20)[18]
        except statistics.StatisticsError:
            p95 = max(ds)
        out[b] = (mean, p95, len(ds))
    return out

def _estimate_cmd_seconds(cmd: str, hist: dict[str, tuple[float, float, int]]) -> float:
    b = _first_token(cmd)
    base = _base_cost(cmd) * _shape_multipliers(cmd)
    if b in hist and hist[b][2] >= 5:
        # blend nhẹ với lịch sử khi đủ mẫu
        mean = hist[b][0]
        return 0.5 * base + 0.5 * mean
    return base

def _list_allowed_cmds(rules: list[Rule], marker: str = "$ ") -> tuple[list[str], int]:
    allowed: list[str] = []
    denied_cnt = 0
    for r in rules:
        cmds = extract_all_commands(getattr(r, "check", "") or "")
        for c in cmds:
            if deny_reason(c):
                denied_cnt += 1
            else:
                allowed.append(c)
    return allowed, denied_cnt

def _simulate_makespan(durs: Sequence[float], workers: int, overhead: float = 0.08) -> float:
    """
    List-scheduling (LPT) xấp xỉ makespan. Đơn giản & đủ nhanh cho pre-run.
    """
    if not durs:
        return 0.0
    w = max(1, int(workers))
    bins = [0.0] * w
    for d in sorted(durs, reverse=True):
        i = min(range(w), key=lambda k: bins[k])
        bins[i] += max(0.0, float(d))
    return max(bins) * (1.0 + overhead)

def estimate_plan(
    rules: list[Rule],
    logs_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,
    use_processes: bool = False,
    per_command: bool = True,
) -> dict[str, object]:
    """
    Trả về bản ước lượng pre-run.
    """
    allowed, denied_cnt = _list_allowed_cmds(rules)
    # nếu per_command=False: gom chunk theo rule; ở đây giữ per-command cho đơn giản
    hist = _read_history(logs_base_dir)
    cmd_durs = [_estimate_cmd_seconds(c, hist) for c in allowed]

    # Nếu caller chưa chỉ định workers, lấy gợi ý sớm
    sample = cmd_durs[:50] or [0.1]
    guessed = auto_guess_workers(len(cmd_durs), use_processes, sample)
    w = workers or guessed

    wall = _simulate_makespan(cmd_durs, w, overhead=(0.03 if use_processes else 0.08))
    cpu_sum = sum(cmd_durs)

    # grades
    if   wall < 60:   grade = "S ( <60s )"
    elif wall < 180:  grade = "M ( 1–3 phút )"
    elif wall < 600:  grade = "L ( 3–10 phút )"
    else:             grade = "XL ( >10 phút )"

    p50 = statistics.median(cmd_durs) if cmd_durs else 0.0
    p95 = (statistics.quantiles(cmd_durs, n=20)[18] if len(cmd_durs) >= 20 else max(cmd_durs) if cmd_durs else 0.0)

    return {
        "n_rules": len(rules),
        "n_cmds": len(allowed),
        "n_denied": denied_cnt,
        "workers_suggested": w,
        "use_processes": use_processes,
        "p50_cmd": round(p50, 3),
        "p95_cmd": round(p95, 3),
        "cpu_seconds_sum": round(cpu_sum, 1),
        "wall_seconds": round(wall, 1),
        "complexity": grade,
    }

