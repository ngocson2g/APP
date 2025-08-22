from __future__ import annotations
from typing import List, Dict, Any
from security_app.models import Rule, CmdResult
from security_app.core.logger import RunLogger

def _merge_and_log(
    idx: int,
    rule: Rule,
    denied: List[CmdResult],
    ran: List[CmdResult],
    logger: RunLogger,
) -> Dict[str, Any]:
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