from typing import List, Dict, Any
from security_app.models import Rule, CmdResult
from security_app.core.command import run_command
from security_app.core.command_extractor import extract_all_commands
from security_app.core.logger import RunLogger

def run_all_rules(rules: List[Rule], log_base_dir: str = "logs"):
    """
    Trả về danh sách dict để giữ tương thích với reporting:
      - rule: Rule
      - cmd_results: list[CmdResult]
    """
    logger = RunLogger(base_dir=log_base_dir)
    results: list[Dict[str, Any]] = []

    for idx, rule in enumerate(rules, start=1):
        cmds: List[str] = extract_all_commands(rule.check)
        cmd_results: List[CmdResult] = [run_command(cmd) for cmd in cmds]

        logger.log_rule_result(idx, rule, cmd_results)

        num_cmds = len(cmd_results)
        num_ok   = sum(1 for r in cmd_results if r.ok)
        num_fail = num_cmds - num_ok

        results.append({
            "rule_index": idx,
            "rule": rule,
            "cmd_results": cmd_results,
            "per_rule_log": f"rule-{idx:03d}_",
            "num_cmds": num_cmds,
            "num_ok": num_ok,
            "num_fail": num_fail
        })
    return results
