# security_app/app/cli.py
"""
Module CLI chính - Xử lý arguments và điều phối luồng chính của ứng dụng
"""
import argparse
import os
import sys

from security_app.config import DEFAULT_LOGS_DIR, TOP_FAIL_LIMIT
from security_app.app.run import run_once

def main():
    # Xử lý subcommand "query"
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        from security_app.app.query import main as query_main
        return query_main(sys.argv[2:])
    
    # (root-check chuyển vào run_once để CLI gọn & dễ test)
    
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

    # Điều phối toàn bộ qua run.py
    run_once(**vars(args))

    if args.plan_only:
        return None  # Thoát sau khi in estimate

    
    return None
    

if __name__ == "__main__":
    main()

