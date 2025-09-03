# security_app/app/cli.py
"""
Module CLI chính - Xử lý arguments và điều phối luồng chính của ứng dụng
"""
import argparse
import os
import sys

from security_app.config import DEFAULT_LOGS_DIR, TOP_FAIL_LIMIT
from security_app.core.estimator import estimate_plan, print_estimate
from security_app.core.runner import run_all_rules
from security_app.parsers.dispatch import parse_file
from security_app.reporting.exporters import dump_stats_json, write_stats_csv_bundle
from security_app.reporting.stats import compute_stats
from security_app.reporting.terminal import print_report
from security_app.runtime.sudo import ensure_root
from security_app.settings import default_settings, require_sudo_by_default, with_overrides

def main():
    # Xử lý subcommand "query"
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        from security_app.app.query import main as query_main
        return query_main(sys.argv[2:])
    
    # Kiểm tra yêu cầu quyền root
    if require_sudo_by_default():
        ensure_root(required=True)
    
    # Thiết lập parser cho command chính
    parser = argparse.ArgumentParser(
        prog="security-app",
        description="Run STIG/Checklist and report results."
    )
    
    # Các arguments cơ bản
    parser.add_argument("input", help="Path to checklist file (CSV/JSON/XML).")
    parser.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR,
                        help=f"Base directory to store run logs (default: {DEFAULT_LOGS_DIR})")
    parser.add_argument("--top", type=int, default=TOP_FAIL_LIMIT,
                        help=f"Show at most N failing rules (default: {TOP_FAIL_LIMIT})")

    # Các arguments cho xử lý đồng thời
    parser.add_argument("--workers", type=int, default=None, 
                        help="Max concurrent workers (default: CPU count).")
    parser.add_argument("--proc", action="store_true", 
                        help="Use process pool instead of threads.")
    parser.add_argument("--timeout", type=float, default=None, 
                        help="Per-command timeout in seconds.")
    parser.add_argument("--retries", type=int, default=None, 
                        help="Retry attempts.")
    
    # Các arguments cho báo cáo và ước lượng
    parser.add_argument("--estimate", action="store_true",
                        help="Print pre-run estimate before executing.")
    parser.add_argument("--plan-only", action="store_true",
                        help="Only print pre-run estimate and exit.")
    parser.add_argument("--json-out", default=None,
                        help="Đường dẫn file JSON (hoặc '-' để in ra stdout) chứa số liệu tổng hợp.")
    parser.add_argument("--csv-out-dir", default=None,
                        help="Thư mục để ghi các file CSV (summary.csv, by_severity.csv, top_failing.csv, rules.csv).")
    parser.add_argument("--save-report", action="store_true",
                        help="Lưu JSON/CSV/Excel vào APP/reportAPP/<timestamp>/ và cập nhật symlink 'latest'.")
    parser.add_argument("--out-dir", default=None,
                        help="Ghi đè thư mục gốc (mặc định APP/reportAPP hoặc ENV SECAPP_REPORT_DIR).")

    args = parser.parse_args()

    # Kiểm tra file input tồn tại
    if not os.path.exists(args.input):
        parser.error(f"Input not found: {args.input}")

    # Thiết lập cấu hình runtime
    base = default_settings()
    settings = with_overrides(base, 
                             shell_timeout=args.timeout, 
                             retry_attempts=args.retries)

    # Bước 1: Parse file input thành danh sách rules
    rules = parse_file(args.input)

    # Xử lý pre-run estimation
    if args.estimate or args.plan_only:
        est = estimate_plan(
            rules,
            logs_base_dir=args.logs_dir,
            workers=args.workers,
            use_processes=args.proc,
            per_command=True,
        )
        print("=" * 80)
        print("PRE-RUN ESTIMATE".center(80))
        print("=" * 80)
        print_estimate(est)
        print()

    if args.plan_only:
        return None  # Thoát sau khi in estimate

    # Bước 2: Chạy estimation để đề xuất workers
    est = estimate_plan(
        rules,
        logs_base_dir=args.logs_dir,
        workers=args.workers,
        use_processes=args.proc,
    )

    # Tự động chọn số workers nếu không specified
    if not args.workers:
        args.workers = est["workers_suggested"]

    # Bước 3: Thực thi tất cả rules
    run_results = run_all_rules(
        rules,
        log_base_dir=args.logs_dir,
        workers=args.workers,
        use_processes=args.proc,
        settings=settings,
    )
    
    # Bước 4: Tính toán thống kê và hiển thị báo cáo
    stats = compute_stats(run_results)
    print_report(stats, limit_top=args.top)

    # Bước 5: Xuất báo cáo nếu được yêu cầu
    if args.json_out:
        dump_stats_json(stats, args.json_out)

    if args.csv_out_dir:
        write_stats_csv_bundle(stats, out_dir=args.csv_out_dir)
        
    return None
    

if __name__ == "__main__":
    main()

