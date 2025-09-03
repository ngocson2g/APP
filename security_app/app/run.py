# security_app/app/run.py
from __future__ import annotations
from typing import Any, Optional
import os

from security_app.parsers.dispatch import parse_file
from security_app.core.estimator import estimate_plan
from security_app.reporting.estimate_terminal import print_estimate
from security_app.core.runner import run_all_rules
from security_app.reporting.stats import compute_stats
from security_app.reporting.terminal import print_report
from security_app.reporting.exporters import dump_stats_json, write_stats_csv_bundle
from security_app.settings import default_settings, with_overrides
from security_app.runtime.sudo import ensure_root
from security_app.settings import require_sudo_by_default
from security_app.config import DEFAULT_LOGS_DIR, TOP_FAIL_LIMIT

def run_once(
    input: str,
    logs_dir: str = DEFAULT_LOGS_DIR,
    top: int = TOP_FAIL_LIMIT,
    workers: Optional[int] = None,
    proc: bool = False,
    timeout: Optional[float] = None,
    retries: Optional[int] = None,
    estimate: bool = False,
    plan_only: bool = False,
    json_out: Optional[str] = None,
    csv_out_dir: Optional[str] = None,
    save_report: bool = False,      # dự phòng (giữ flag cũ)
    out_dir: Optional[str] = None,  # dự phòng (giữ flag cũ)
) -> dict[str, Any]:
    """
    Điều phối một lần chạy: parse→estimate→execute→report→export.
    Trả về dict chứa 'estimate' (đề xuất workers, thời gian) và 'stats' (kết quả).
    """

    # (Giữ hành vi cũ) Yêu cầu quyền nếu policy bật
    if require_sudo_by_default():
        ensure_root(required=True)

    if not os.path.exists(input):
        raise FileNotFoundError(f"Input not found: {input}")

    # Tạo Settings từ CLI overrides (timeout/retries)
    base = default_settings()
    settings = with_overrides(base, shell_timeout=timeout, retry_attempts=retries)

    # 1) Parse checklist thành list[Rule]
    rules = parse_file(input)

    # 2) In ước lượng trước khi chạy (nếu được yêu cầu)
    if estimate or plan_only:
        est_pre = estimate_plan(
            rules, logs_base_dir=logs_dir, workers=workers, use_processes=proc, per_command=True
        )
        print("=" * 80)
        print("PRE-RUN ESTIMATE".center(80))
        print("=" * 80)
        print_estimate(est_pre)
        print()
        if plan_only:
            return {"estimate": est_pre, "stats": None}

    # 3) Ước lượng để gợi ý số workers (nếu chưa set)
    est = estimate_plan(rules, logs_base_dir=logs_dir, workers=workers, use_processes=proc)
    if not workers:
        workers = est["workers_suggested"]  # giữ logic auto như cũ

    # 4) Thực thi toàn bộ rules
    run_results = run_all_rules(
        rules, log_base_dir=logs_dir, workers=workers, use_processes=proc, settings=settings
    )

    # 5) Tính stats và in báo cáo ra terminal
    stats = compute_stats(run_results)
    print_report(stats, limit_top=top)

    # 6) Export nếu có yêu cầu
    if json_out:
        dump_stats_json(stats, json_out)
    if csv_out_dir:
        write_stats_csv_bundle(stats, out_dir=csv_out_dir)

    return {"estimate": est, "stats": stats}
