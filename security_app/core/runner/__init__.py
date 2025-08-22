# security_app/core/runner/__init__.py
from __future__ import annotations
import os
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from security_app.models import Rule, CmdResult
from security_app.config import CMD_MARKER, DEFAULT_LOGS_DIR
from security_app.core.logger import RunLogger

from .extract import _pre_extract_rules
from .plan import _prepare_tasks
from .workers import _worker
from .merge import _merge_and_log

def run_all_rules(
    rules: List[Rule],
    log_base_dir: str = DEFAULT_LOGS_DIR,
    workers: int | None = None,
    use_processes: bool = False,
    per_command: bool = True,
) -> List[Dict[str, Any]]:
    """Thực thi toàn bộ rule với concurrency; chỉ main thread ghi log (single-writer)."""
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
            fut2idx = {}
            for task in tasks:
                idx, rule, chunk = task
                fut = ex.submit(_worker, (idx, rule, chunk))
                fut2idx[fut] = idx

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