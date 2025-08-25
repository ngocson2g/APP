#security_app/core/runner/plan.py
from __future__ import annotations
from typing import List, Tuple, Dict, Any
from security_app.models import Rule, CmdResult

def _prepare_tasks(
    pre: List[Tuple[int, Rule, List[str], List[CmdResult]]],
    per_command: bool = True,
) -> Tuple[List[Tuple[int, Rule, List[str]]], Dict[int, Dict[str, Any]], Dict[int, int]]:
    """
    Từ pre-extract tạo:
      - tasks: [(idx, rule, [cmds_chunk]), ...]  (per_command=True => mỗi task 1 lệnh)
      - agg:   {idx: {"rule": Rule, "denied": [CmdResult], "ran": [CmdResult]}}
      - pending: {idx: số task còn lại của rule}
    """
    tasks: List[Tuple[int, Rule, List[str]]] = []
    agg: Dict[int, Dict[str, Any]] = {}
    pending: Dict[int, int] = {}

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