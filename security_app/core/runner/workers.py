from __future__ import annotations
from typing import Tuple, List
from security_app.models import CmdResult, Rule
from security_app.core.command import run_command

def _worker(payload: Tuple[int, Rule, List[str]]) -> Tuple[int, List[CmdResult]]:
    """Worker: nhận (idx, rule, allowed_cmds_chunk) và trả về (idx, [CmdResult])."""
    idx, _rule, allowed_cmds = payload
    results: List[CmdResult] = [run_command(cmd) for cmd in allowed_cmds]
    return idx, results