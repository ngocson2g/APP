# security_app/core/runner.py
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

from security_app.models import Rule, CmdResult
from security_app.core.command import run_command
from security_app.core.command_extractor import extract_all_commands
from security_app.core.logger import RunLogger
from security_app.policy.safety import deny_reason
from security_app.config import CMD_MARKER, DEFAULT_LOGS_DIR


# ---------- Pre-extract ----------
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


# ---------- Task prep & worker ----------
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


def _worker(payload: Tuple[int, Rule, List[str]]) -> Tuple[int, List[CmdResult]]:
    """
    Worker: nhận (idx, rule, allowed_cmds_chunk) và trả về (idx, [CmdResult]).
    """
    idx, _rule, allowed_cmds = payload
    results: List[CmdResult] = [run_command(cmd) for cmd in allowed_cmds]
    return idx, results


# ---------- Merge & log (single-writer) ----------
def _merge_and_log(
    idx: int,
    rule: Rule,
    denied: List[CmdResult],
    ran: List[CmdResult],
    logger: RunLogger,
) -> Dict[str, Any]:
    """
    Gộp kết quả deny + đã chạy, ghi log 1 lần, trả về summary cho reporting.
    """
    merged = list(denied) + list(ran)
    logger.log_rule_result(idx, rule, merged)

    n = len(merged)
    ok = sum(1 for r in merged if getattr(r, "ok", False))
    return {
        "rule_index": idx,
        "rule": rule,
        "cmd_results": merged,
        "num_cmds": n,
        "num_ok": ok,
        "num_fail": n - ok,
    }


# ---------- Public API ----------
def run_all_rules(
    rules: List[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,
    use_processes: bool = False,
    per_command: bool = True,  # flag nội bộ: cân bằng tải tốt hơn khi nhiều lệnh chậm
) -> List[Dict[str, Any]]:
    """
    Thực thi toàn bộ rule với concurrency; chỉ main thread ghi log (single-writer).
    """
    os.makedirs(log_base_dir, exist_ok=True)
    logger = RunLogger(base_dir=log_base_dir)

    # 1) Trích xuất & chuẩn bị task
    pre = _pre_extract_rules(rules, marker=CMD_MARKER)
    tasks, agg, pending = _prepare_tasks(pre, per_command=per_command)

    results: List[Dict[str, Any]] = []

    # Rule không có allowed-cmd (chỉ deny hoặc trống) -> log ngay
    for idx, state in list(agg.items()):
        if pending.get(idx, 0) == 0:
            results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
            pending.pop(idx, None)

    # 2) Chạy song song phần allowed
    if tasks:
        Executor = ProcessPoolExecutor if use_processes else ThreadPoolExecutor
        max_workers = workers or os.cpu_count() or 4
        with Executor(max_workers=max_workers) as ex:
            fut2idx = {ex.submit(_worker, payload): payload[0] for payload in tasks}
            for fut in as_completed(fut2idx):
                idx = fut2idx[fut]
                try:
                    _idx, ran_part = fut.result()
                except Exception as e:
                    ran_part = [CmdResult(cmd="(worker error)", returncode=None, stdout="", stderr=str(e), duration_sec=0.0, ok=False)]

                state = agg[idx]
                state["ran"].extend(ran_part)
                pending[idx] -= 1
                if pending[idx] == 0:
                    results.append(_merge_and_log(idx, state["rule"], state["denied"], state["ran"], logger))
                    del agg[idx]
                    del pending[idx]

    # 3) Ổn định thứ tự theo index rule
    results.sort(key=lambda x: x["rule_index"])
    return results
