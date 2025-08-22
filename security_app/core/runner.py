from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import re

from security_app.models import Rule, CmdResult
from security_app.core.command import run_command
from security_app.core.command_extractor import extract_all_commands
from security_app.core.logger import RunLogger
from security_app.config import CMD_DENYLIST


# ---------- PRE-EXTRACT & DENYLIST ----------

_DENY_RE = [re.compile(p, re.IGNORECASE) for p in CMD_DENYLIST]

def _deny_reason(cmd: str) -> str | None:
    s = (cmd or "").strip()
    if not s:
        return "DENIED: empty command"
    for rx in _DENY_RE:
        if rx.search(s):
            return f"DENIED by safety policy: matched /{rx.pattern}/"
    return None

def _pre_extract_rules(rules: List[Rule]) -> List[Tuple[int, Rule, List[str], List[CmdResult]]]:
    """
    Trả về danh sách tuple:
      (rule_index, rule, allowed_cmds, denied_cmd_results)

    - Extract tất cả lệnh từ rule.check trước (fail-fast).
    - Lọc denylist sớm; lệnh bị chặn sẽ có CmdResult 'DENIED' sinh ra tại đây
      (không gửi sang worker).
    """
    out: List[Tuple[int, Rule, List[str], List[CmdResult]]] = []

    for idx, rule in enumerate(rules, 1):
        check_text = getattr(rule, "check", "") or ""
        cmds_raw = extract_all_commands(check_text) or []

        allowed: List[str] = []
        denied_results: List[CmdResult] = []

        for c in cmds_raw:
            reason = _deny_reason(c)
            if reason:
                denied_results.append(CmdResult(
                    cmd=c, returncode=None, stdout="", stderr=reason,
                    duration_sec=0.0, ok=False
                ))
            else:
                allowed.append(c)

        out.append((idx, rule, allowed, denied_results))

    return out


# ---------- WORKER (CHỈ CHẠY LỆNH, KHÔNG GHI LOG) ----------

def _execute_rule_with_cmds(payload: Tuple[int, Rule, List[str]]) -> Tuple[int, Rule, List[CmdResult]]:
    """
    Worker: nhận (idx, rule, allowed_cmds) và trả lại list CmdResult đã chạy.
    KHÔNG ghi log ở đây (giữ single-writer).
    """
    idx, rule, allowed_cmds = payload
    results: List[CmdResult] = []

    for cmd in allowed_cmds:
        cr = run_command(cmd)
        results.append(cr)

    return idx, rule, results


# ---------- ORCHESTRATOR (SINGLE-WRITER) ----------

def run_all_rules(
    rules: List[Rule],
    log_base_dir: str = "logs",
    workers: int | None = None,
    use_processes: bool = False,
) -> List[Dict[str, Any]]:
    """
    Orchestrator:
      1) Pre-extract & lọc denylist cho *tất cả* rule (fail-fast, chuẩn hoá input).
      2) Dispatch song song việc *chạy lệnh được phép* (allowed_cmds).
      3) Main thread (single-writer) *gộp* với kết quả denied & ghi log theo rule.
    """
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)

    # 1) Pre-extract toàn bộ
    pre = _pre_extract_rules(rules)

    # Chuẩn bị payload cho executor: chỉ các rule có allowed_cmds
    tasks: List[Tuple[int, Rule, List[str]]] = []
    denied_by_rule: Dict[int, List[CmdResult]] = {}
    empty_rules: List[int] = []  # rule không có lệnh (sau khi lọc)

    for idx, rule, allowed, denied in pre:
        if denied:
            denied_by_rule[idx] = denied
        if allowed:
            tasks.append((idx, rule, allowed))
        else:
            # Không còn lệnh nào để chạy (hoặc trống), vẫn cần log
            empty_rules.append(idx)

    # 2) Chạy song song các allowed_cmds theo đơn vị "mỗi rule"
    results: List[Dict[str, Any]] = []
    futures = []

    if tasks:
        Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        max_workers = workers or (os.cpu_count() or 4)

        with Executor(max_workers=max_workers) as ex:
            for payload in tasks:
                futures.append(ex.submit(_execute_rule_with_cmds, payload))

            for fut in as_completed(futures):
                idx, rule, ran_results = fut.result()
                # gộp với phần bị deny trước đó (nếu có)
                merged = list(denied_by_rule.get(idx, [])) + list(ran_results)

                # SINGLE-WRITER: chỉ ghi log ở đây
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

    # 3) Ghi log cho các rule không có allowed_cmds (chỉ deny hoặc trống)
    for idx in empty_rules:
        # tìm lại rule & denied
        # (pre giữ nguyên thứ tự; an toàn để tra cứu)
        _, rule, _, denied = next(item for item in pre if item[0] == idx)
        merged = list(denied)  # có thể rỗng nếu check không có lệnh

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

    # Trả về theo thứ tự rule_index
    results.sort(key=lambda x: x["rule_index"])
    return results
