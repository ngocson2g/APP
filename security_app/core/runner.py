from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

from security_app.models import Rule, CmdResult
from security_app.core.command import run_command
from security_app.core.command_extractor import extract_all_commands
from security_app.core.logger import RunLogger


def _execute_rule(idx_and_rule: Tuple[int, Rule]) -> Tuple[int, Rule, List[CmdResult]]:
    """Worker: chỉ chạy lệnh, KHÔNG ghi log."""
    idx, rule = idx_and_rule
    check_text = getattr(rule, "check", "") or ""
    cmds = extract_all_commands(check_text)
    cmd_results: List[CmdResult] = [run_command(c) for c in cmds]
    return (idx, rule, cmd_results)


def run_all_rules(
    rules: List[Rule],
    log_base_dir: str = "logs",
    workers: int | None = None,
    use_processes: bool = False,
) -> List[Dict[str, Any]]:
    """
    (single-writer): chạy song song phần thực thi, chỉ MAIN thread ghi log.
    """
    logger = RunLogger(base_dir=log_base_dir)
    Exec = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    max_workers = workers if workers is not None else (os.cpu_count() or 4)

    jobs = [(i, r) for i, r in enumerate(rules, start=1)]
    results: List[Dict[str, Any]] = []

    with Exec(max_workers=max_workers) as ex:
        futs = [ex.submit(_execute_rule, jr) for jr in jobs]
        for fut in as_completed(futs):
            idx, rule, cmd_results = fut.result()

            # CHỈ GHI LOG Ở ĐÂY (single-writer)
            logger.log_rule_result(idx, rule, cmd_results)

            n = len(cmd_results)
            ok = sum(1 for cr in cmd_results if getattr(cr, "ok", False))
            results.append({
                "rule_index": idx,
                "rule": rule,
                "cmd_results": cmd_results,
                "num_cmds": n,
                "num_ok": ok,
                "num_fail": n - ok,
            })

    results.sort(key=lambda x: x["rule_index"])
    return results
