# security_app/app/run.py
from __future__ import annotations

import os
from typing import Any

from security_app.config import DEFAULT_LOGS_DIR, TOP_FAIL_LIMIT
from security_app.core.estimator import estimate_plan
from security_app.core.runner import run_all_rules
from security_app.parsers.dispatch import parse_file
from security_app.reporting.estimate_terminal import print_estimate
from security_app.reporting.exporters import dump_stats_json, write_stats_csv_bundle
from security_app.reporting.stats import compute_stats
from security_app.reporting.terminal import print_report
from security_app.runtime.sudo import ensure_root
from security_app.settings import default_settings, require_sudo_by_default, with_overrides


def _autotimeout_from_est(p95: float | None) -> float | None:
    if not p95 or p95 <= 0:
        return None
    t = p95 * 3.0 + 1.0
    # clamp 5..60
    if t < 5.0:  t = 5.0
    if t > 60.0: t = 60.0
    return float(t)

def run_once(
    input: str,
    logs_dir: str = DEFAULT_LOGS_DIR,
    top: int = TOP_FAIL_LIMIT,
    workers: int | None = None,
    proc: bool = False,
    timeout: float | None = None,
    retries: int | None = None,
    estimate: bool = False,
    plan_only: bool = False,
    json_out: str | None = None,
    csv_out_dir: str | None = None,
    save_report: bool = False,
    out_dir: str | None = None,
    list_all_rules: bool = False,
    
) -> dict[str, Any]:
    
    #1. Chuẩn bị 
    if require_sudo_by_default():
        ensure_root(required=True)
    if not os.path.exists(input):
        raise FileNotFoundError(f"Input not found: {input}")

    base = default_settings()
    rules = parse_file(input)
    
    # NOTE: list_cmds / parse_rc_stigs có thể tích hợp lại khi cần
    # so sánh expected RC vs actual trong reporting pipeline.

    #2. Ước lượng trước (nếu cần in) + để suy ra timeout động
    est_pre = estimate_plan(
        rules, logs_base_dir=logs_dir, workers=workers, use_processes=proc, per_command=True
    )
    est = dict(est_pre)
    est["workers_used"] = workers
    
    if estimate or plan_only:
        print("=" * 80)
        print("PRE-RUN ESTIMATE".center(80))
        print("=" * 80)
        print_estimate(est_pre)
        print()
        if plan_only:
            return {"estimate": est_pre, "stats": None}

    # Nếu CLI không truyền --timeout, đặt timeout_cmd theo p95
    shell_timeout = timeout if timeout else _autotimeout_from_est(est_pre.get("p95_cmd"))
    settings = with_overrides(base, shell_timeout=shell_timeout, retry_attempts=retries)

    # Tái dùng est_pre để lấy workers_suggested (tránh gọi estimate_plan lần 2)
    if not workers:
        try:
            workers = int(est_pre.get("workers_suggested") or 1)
        except Exception:
            workers = 1
    # Dùng lại est_pre cho phần trả về/report
    est = est_pre

    #4. thực thi
    run_results = run_all_rules(
        rules, log_base_dir=logs_dir, workers=workers, use_processes=proc, settings=settings
    )
    
    #5. Báo cáo
    stats = compute_stats(run_results)
    print_report(stats, limit_top=top, list_all_rules=list_all_rules)

    if json_out:
        dump_stats_json(stats, json_out)
    if csv_out_dir:
        write_stats_csv_bundle(stats, out_dir=csv_out_dir)

    return {"estimate": est, "stats": stats}
