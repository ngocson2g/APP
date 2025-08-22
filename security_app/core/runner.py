from __future__ import annotations
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

from security_app.models import Rule, CmdResult
from security_app.core.command import run_command
from security_app.core.command_extractor import extract_all_commands
from security_app.core.logger import RunLogger
from security_app.policy.safety import deny_reason   # << dùng nguồn chung

# ---------- PRE-EXTRACT & DENYLIST ----------
def _pre_extract_rules(rules: List[Rule]) -> List[Tuple[int, Rule, List[str], List[CmdResult]]]:
    """
    Trả về danh sách tuple: (rule_index, rule, allowed_cmds, denied_cmd_results)
    """
    out: List[Tuple[int, Rule, List[str], List[CmdResult]]] = []
    for idx, rule in enumerate(rules, 1):
        check_text = getattr(rule, "check", "") or ""
        cmds_raw = extract_all_commands(check_text) or []

        allowed: List[str] = []
        denied_results: List[CmdResult] = []

        for c in cmds_raw:
            reason = deny_reason(c)  # << nguồn sự thật
            if reason:
                denied_results.append(CmdResult(
                    cmd=c, returncode=None, stdout="", stderr=reason,
                    duration_sec=0.0, ok=False
                ))
            else:
                allowed.append(c)

        out.append((idx, rule, allowed, denied_results))
    return out

def _execute_rule_with_cmds(payload: Tuple[int, Rule, List[str]]) -> Tuple[int, Rule, List[CmdResult]]:
    """
    Worker: nhận (idx, rule, allowed_cmds); KHÔNG ghi log ở đây.
    """
    idx, rule, allowed_cmds = payload
    results: List[CmdResult] = [run_command(cmd) for cmd in allowed_cmds]
    return idx, rule, results

def run_all_rules(
    rules: List[Rule],
    log_base_dir: str = "logs",
    workers: int | None = None,
    use_processes: bool = False,
) -> List[Dict[str, Any]]:
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)

    pre = _pre_extract_rules(rules)
    empty_rules = [idx for (idx, _, allowed, denied) in pre if not allowed]

    Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
    max_workers = workers or os.cpu_count() or 4
    results: List[Dict[str, Any]] = []

    with Executor(max_workers=max_workers) as ex:
        futs = {ex.submit(_execute_rule_with_cmds, (idx, rule, allowed)): idx
                for (idx, rule, allowed, denied) in pre if allowed}
        for fut in as_completed(futs):
            idx, rule, ran = fut.result()
            # gộp với denied tương ứng
            denied = next(d for (i, _, _, d) in pre if i == idx)
            merged = list(denied) + list(ran)

            logger.log_rule_result(idx, rule, merged)

            n = len(merged)
            ok = sum(1 for x in merged if getattr(x, "ok", False))
            results.append({
                "rule_index": idx,
                "rule": rule,
                "cmd_results": merged,
                "num_cmds": n,
                "num_ok": ok,
                "num_fail": n - ok,
            })

    # rule chỉ có deny hoặc không có lệnh
    for idx in empty_rules:
        _, rule, _, denied = next(item for item in pre if item[0] == idx)
        merged = list(denied)
        logger.log_rule_result(idx, rule, merged)
        n = len(merged); ok = sum(1 for x in merged if getattr(x, "ok", False))
        results.append({
            "rule_index": idx, "rule": rule, "cmd_results": merged,
            "num_cmds": n, "num_ok": ok, "num_fail": n - ok,
        })

    results.sort(key=lambda x: x["rule_index"])
    return results
