# security_app/core/runner/scheduler.py
from __future__ import annotations

from typing import Any

from security_app.core.command_extractor import extract_all_commands
from security_app.models import CmdResult, Rule
from security_app.policy.safety import RULE_DENY_ASSESSMENT_STATUS, deny_reason

# ❌ BỎ import gây vòng lặp:
# from security_app.core.estimator import _read_history, _estimate_cmd_seconds


def _mk_denied(cmd: str, reason: str) -> CmdResult:
    return CmdResult(cmd=cmd, returncode=None, stdout="", stderr=reason, duration_sec=0.0, ok=False)



# ✅ Thêm helper lazy-import để tránh vòng lặp:
def _get_estimators():
    # estimator.py import runner.tuner; runner.__init__ import scheduler.
    # Lazy-import ngay trong runtime sẽ cắt vòng lặp import-time.
    from security_app.core import estimator as _est
    return _est._read_history, _est._estimate_cmd_seconds

def build_scheduled_tasks(
    rules: list[Rule],
    logs_base_dir: str,
) -> tuple[list[tuple[int, Rule, list[str], float]], dict[int, dict[str, Any]], dict[int, int]]:
    """
    Trả về:
      - tasks: list[(idx, rule, chunk_cmds, est_sec)]
      - agg:   {idx: {"rule": Rule, "denied": [CmdResult], "ran": []}}
      - pending: {idx: số task còn lại}
    """
    # dùng lazy import ngay khi cần
    _read_history, _estimate_cmd_seconds = _get_estimators()

    hist = _read_history(logs_base_dir)
    tasks: list[tuple[int, Rule, list[str], float]] = []
    agg: dict[int, dict[str, Any]] = {}
    pending: dict[int, int] = {}

    for idx, rule in enumerate(rules):
        cmds_all = extract_all_commands(getattr(rule, "check", "") or "")
        allowed: list[str] = []
        denied: list[CmdResult] = []

        rule_status = (rule.assessment_status or "").lower().strip()

        if rule_status in RULE_DENY_ASSESSMENT_STATUS: 
            # Nếu status bị cấm (vd: "manual"), deny tất cả commands
            reason = f"DENIED: Assessment Status is '{rule_status}'"
            for c in cmds_all:
                denied.append(_mk_denied(c, reason))
        else:
            # Nếu status hợp lệ, chạy logic deny-list lệnh như cũ
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

        # 1. Ước tính thời gian cho TẤT CẢ lệnh trong rule này
        ests = [_estimate_cmd_seconds(c, hist) for c in allowed]
        
        # 2. Tổng thời gian ước tính cho TOÀN BỘ rule (đây là trọng số LPT mới)
        total_rule_est = sum(ests) or 0.01

        # 3. Tạo MỘT task duy nhất chứa TẤT CẢ các lệnh (thay vì 'ch' (chunk))
        tasks.append((idx, rule, allowed, float(total_rule_est)))

        # 4. Mỗi rule giờ chỉ có 1 task (thay vì len(chunks))
        pending[idx] = 1

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