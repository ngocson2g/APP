# security_app/core/runner/workers.py
from __future__ import annotations
from typing import Tuple, List
from security_app.models import CmdResult, Rule
from security_app.core.command import run_command
from security_app.settings import Settings

def _workers(payload: Tuple[int, Rule, List[str], Settings]) -> Tuple[int, List[CmdResult]]:
    """Worker: nhận (idx, rule, allowed_cmds_chunk, settings) và trả về (idx, [CmdResult])."""
    idx, _rule, allowed_cmds, settings = payload
    results: List[CmdResult] = [run_command(cmd, settings) for cmd in allowed_cmds]
    return idx, results
