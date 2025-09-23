# security_app/reporting/estimate_terminal.py
from __future__ import annotations

from typing import Dict

from security_app.utils.text import _table


def print_estimate(est: Dict[str, object]) -> None:
    """
    Render ước lượng pre-run ra terminal, đồng bộ phong cách với reporting/terminal.print_report
    (dùng cùng _table, đơn sắc, gọn gàng).
    """
    rows = [
        ["Rules", est.get("n_rules", 0)],
        ["Commands (allowed)", est.get("n_cmds", 0)],
        ["Commands (denied)", est.get("n_denied", 0)],
        ["Workers (suggested)", est.get("workers_suggested")],
        ["Pool type", "processes" if est.get("use_processes") else "threads"],
        ["p50 per-cmd (s)", est.get("p50_cmd")],
        ["p95 per-cmd (s)", est.get("p95_cmd")],
        ["Total CPU-seconds (∑)", est.get("cpu_seconds_sum")],
        ["Estimated wall-clock (s)", est.get("wall_seconds")],
        ["Complexity", est.get("complexity")],
    ]
    _table(rows, headers=["Metric", "Value"])
