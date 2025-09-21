# security_app/core/runner/scheduler.py
from __future__ import annotations
from typing import Any, List, Tuple
import math

from security_app.models import CmdResult, Rule
from security_app.core.command_extractor import extract_all_commands
from security_app.policy.safety import deny_reason
# ❌ BỎ import gây vòng lặp:
# from security_app.core.estimator import _read_history, _estimate_cmd_seconds
from security_app.config import (
    LPT_WAVE_MIN, LPT_WAVE_MAX,
    CHUNK_SHORT_THRESHOLD, CHUNK_SIZE_DEFAULT
)

def _mk_denied(cmd: str, reason: str) -> CmdResult:
    return CmdResult(cmd=cmd, returncode=None, stdout="", stderr=reason, duration_sec=0.0, ok=False)

def _chunk_by_size(cmds: List[str], size: int) -> List[List[str]]:
    return [cmds[i:i+size] for i in range(0, len(cmds), size)]

def _chunk_dynamic(cmds: List[str], ests: List[float]) -> List[List[str]]:
    """
    Quy tắc chunking động:
    - Nếu rule có >=10 lệnh và >=60% lệnh có est <= CHUNK_SHORT_THRESHOLD:
      + nếu max(est) < 0.10s -> chunk 5; else chunk 4.
    - Ngược lại: mỗi task 1 lệnh.
    """
    if len(cmds) >= 10:
        short_ratio = sum(1 for e in ests if e <= CHUNK_SHORT_THRESHOLD) / max(1, len(ests))
        if short_ratio >= 0.60:
            size = 5 if (ests and max(ests) < 0.10) else CHUNK_SIZE_DEFAULT
            return _chunk_by_size(cmds, size)
    return [[c] for c in cmds]

# ✅ Thêm helper lazy-import để tránh vòng lặp:
def _get_estimators():
    # estimator.py import runner.tuner; runner.__init__ import scheduler.
    # Lazy-import ngay trong runtime sẽ cắt vòng lặp import-time.
    from security_app.core import estimator as _est
    return _est._read_history, _est._estimate_cmd_seconds

def build_scheduled_tasks(
    rules: List[Rule],
    logs_base_dir: str,
) -> Tuple[List[Tuple[int, Rule, List[str], float]], dict[int, dict[str, Any]], dict[int, int]]:
    """
    Trả về:
      - tasks: list[(idx, rule, chunk_cmds, est_sec)]
      - agg:   {idx: {"rule": Rule, "denied": [CmdResult], "ran": []}}
      - pending: {idx: số task còn lại}
    """
    # dùng lazy import ngay khi cần
    _read_history, _estimate_cmd_seconds = _get_estimators()

    hist = _read_history(logs_base_dir)
    tasks: List[Tuple[int, Rule, List[str], float]] = []
    agg: dict[int, dict[str, Any]] = {}
    pending: dict[int, int] = {}

    for idx, rule in enumerate(rules):
        cmds_all = extract_all_commands(getattr(rule, "check", "") or "")
        allowed: List[str] = []
        denied: List[CmdResult] = []

        for c in cmds_all:
            r = deny_reason(c)
            if r:
                denied.append(_mk_denied(c, r))
            else:
                allowed.append(c)

        agg[idx] = {"rule": rule, "denied": denied, "ran": []}

        if not allowed:
            pending[idx] = 0
            continue

        ests = [_estimate_cmd_seconds(c, hist) for c in allowed]
        chunks = _chunk_dynamic(allowed, ests)

        for ch in chunks:
            est_chunk = sum(_estimate_cmd_seconds(c, hist) for c in ch) or 0.01
            tasks.append((idx, rule, ch, float(est_chunk)))

        pending[idx] = len(chunks)

    tasks.sort(key=lambda t: t[3], reverse=True)
    return tasks, agg, pending

# def suggest_wave_size(n_tasks: int) -> int:
#     if n_tasks <= 0:
#         return LPT_WAVE_MIN
#     target = 300
#     return int(max(LPT_WAVE_MIN, min(LPT_WAVE_MAX, target, n_tasks)))

def suggest_wave_size(backlog: int) -> int:
    # cập nhật 0.5–2 giây/lần: wave tối đa 128 chunk, tối thiểu 8
    return max(8, min(128, backlog // 4 or 1))