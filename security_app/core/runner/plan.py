#security_app/core/runner/plan.py
from __future__ import annotations

from typing import Any

from security_app.models import CmdResult, Rule


def _prepare_tasks(
    pre: list[tuple[int, Rule, list[str], list[CmdResult]]],
    per_command: bool = True,
) -> tuple[list[tuple[int, Rule, list[str]]], dict[int, dict[str, Any]], dict[int, int]]:
    """
    Từ pre-extract tạo:
      - tasks: [(idx, rule, [cmds_chunk]), ...]  (per_command=True => mỗi task 1 lệnh)
      - agg:   {idx: {"rule": Rule, "denied": [CmdResult], "ran": [CmdResult]}}
      - pending: {idx: số task còn lại của rule}
    """
    tasks: list[tuple[int, Rule, list[str]]] = []
    agg: dict[int, dict[str, Any]] = {}
    pending: dict[int, int] = {}

    for idx, rule, allowed, denied in pre:
        agg[idx] = {"rule": rule, "denied": list(denied), "ran": []}
        if not allowed:
            pending[idx] = 0
            continue

        if per_command:
            for c in allowed:
                tasks.append((idx, rule, [c]))
            pending[idx] = len(allowed)
        else:
            tasks.append((idx, rule, list(allowed)))
            pending[idx] = 1
    return tasks, agg, pending

