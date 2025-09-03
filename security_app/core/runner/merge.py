#security_app/core/runner/merge.py
from __future__ import annotations

from typing import Any

from security_app.core.logger import RunLogger
from security_app.models import CmdResult, Rule


def _merge_and_log(
    idx: int,
    rule: Rule,
    denied: list[CmdResult],
    ran: list[CmdResult],
    logger: RunLogger,
) -> dict[str, Any]:
    """Gộp kết quả deny + đã chạy, ghi log 1 lần, trả về summary cho reporting."""
    merged = list(denied) + list(ran)
    logger.log_rule_result(idx, rule, merged)

    n = len(merged)
    ok = sum(1 for r in merged if getattr(r, "ok", False))
    return {
        "rule_index": idx,
        "rule": rule,
        "cmd_results": merged,
        "num_cmds": n,
        "num_ok": ok,
        "num_fail": n - ok,
    }

