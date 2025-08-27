#security_app/core/runner/extract.py
from __future__ import annotations
from typing import List, Tuple
from security_app.models import Rule, CmdResult
from security_app.core.command_extractor import extract_all_commands
from security_app.policy.safety import deny_reason

def _mk_denied(cmd: str, reason: str) -> CmdResult:
    return CmdResult(cmd=cmd, returncode=None, stdout="", stderr=reason, duration_sec=0.0, ok=False)

def _pre_extract_rules(rules: List[Rule], marker: str) -> List[Tuple[int, Rule, List[str], List[CmdResult]]]:
    """
    Trả về: [(rule_index, rule, allowed_cmds, denied_cmd_results), ...]
    """
    pre: List[Tuple[int, Rule, List[str], List[CmdResult]]] = []
    for idx, rule in enumerate(rules):
        cmds = extract_all_commands(getattr(rule, "check", "") or "")
        allowed, denied = [], []
        for c in cmds:
            reason = deny_reason(c)
            if reason:
                denied.append(_mk_denied(c, reason))
            else:
                allowed.append(c)
        pre.append((idx, rule, allowed, denied))
    return pre

