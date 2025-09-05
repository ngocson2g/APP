# security_app/app/cli.py
"""
CLI chính cho security-app.

Thiết kế đơn giản, KHÔNG dùng subparsers để tránh nuốt positional 'input'.
- Run mặc định:  security-app <input> [các cờ...]
- Cleanup:       security-app cleanup [các cờ cleanup...]  (alias của --cleanup)
- Cleanup:       security-app --cleanup [các cờ cleanup...]
"""
from __future__ import annotations
import argparse
import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from security_app import config as CFG
from security_app.app.run import run_once
from security_app.maintenance.cleanup import run_cleanup

# Fallbacks nếu thiếu hằng số trong config.py
DEFAULT_LOGS_DIR = getattr(CFG, "DEFAULT_LOGS_DIR", "logs")
TOP_FAIL_LIMIT = getattr(CFG, "TOP_FAIL_LIMIT", 20)
LOG_ROTATE_KEEP = getattr(CFG, "LOG_ROTATE_KEEP", 50)

# ----------------------------
# Parser
# ----------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="security-app",
        description="Ubuntu hardening checker & runner",
        add_help=True,
    )

    # Alias: nếu người dùng gõ 'cleanup' như subcommand, ta sẽ chuyển thành --cleanup ở main()
    # Ở đây chỉ khai báo cờ.
    p.add_argument("--cleanup", action="store_true",
                   help="Chạy job dọn dẹp (logs/report/tmp). Dùng alias 'cleanup' đứng đầu cũng được.")

    # Positional input CHO LUỒNG CHẠY CHÍNH
    p.add_argument("input", nargs="?", help="Checklist (CSV/JSON/XML) khi chạy mặc định.")

    # ----- Tham số RUN (mặc định) -----
    p.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR,
                   help=f"Thư mục logs (default: {DEFAULT_LOGS_DIR})")
    p.add_argument("--top", type=int, default=TOP_FAIL_LIMIT,
                   help=f"Số rule fail tối đa để hiển thị (default: {TOP_FAIL_LIMIT})")

    p.add_argument("--workers", type=int, default=None,
                   help="Số worker tối đa (default: CPU count).")
    p.add_argument("--proc", action="store_true",
                   help="Dùng process pool thay vì threads.")
    p.add_argument("--timeout", type=float, default=None,
                   help="Timeout mỗi lệnh (giây).")
    p.add_argument("--retries", type=int, default=None,
                   help="Số lần retry mỗi lệnh.")

    p.add_argument("--estimate", action="store_true",
                   help="In ước lượng thời gian/độ phức tạp trước khi chạy.")
    p.add_argument("--plan-only", action="store_true",
                   help="Chỉ in kế hoạch/ước lượng rồi thoát (không thực thi).")

    p.add_argument("--json-out", default=None,
                   help="Ghi thống kê JSON ra file.")
    p.add_argument("--csv-out-dir", default=None,
                   help="Thư mục ghi các CSV.")
    p.add_argument("--save-report", action="store_true",
                   help="(Legacy) Lưu artefact báo cáo.")
    p.add_argument("--out-dir", default=None,
                   help="(Legacy) Thư mục báo cáo.")

    p.add_argument("--post-cleanup", action="store_true",
                   help="Sau khi chạy xong, dọn dẹp an toàn (dry-run).")

    # ----- Tham số CLEANUP (chỉ dùng khi --cleanup hoặc alias 'cleanup') -----
    p.add_argument("--report-dir", default=os.getenv("SECAPP_REPORT_DIR"),
                   help="Thư mục report gốc (ví dụ APP/reportAPP).")
    p.add_argument("--keep-runs", type=int, default=LOG_ROTATE_KEEP,
                   help=f"Giữ lại N run mới nhất (default: {LOG_ROTATE_KEEP}).")
    p.add_argument("--runs-older-than-days", type=int, default=None,
                   help="Xoá run cũ hơn X ngày (tuỳ chọn).")
    p.add_argument("--compress-runs-older-than-days", type=int, default=None,
                   help="Nén .tar.gz run cũ hơn X ngày (tuỳ chọn).")
    p.add_argument("--keep-reports-days", type=int, default=30,
                   help="Giữ báo cáo trong X ngày (default: 30).")
    p.add_argument("--tmp-prefix", default="security_app_",
                   help="Prefix file/thư mục tạm ở /tmp (default: security_app_).")
    p.add_argument("--tmp-older-than-hours", type=int, default=12,
                   help="Xoá file tạm cũ hơn X giờ (default: 12).")
    p.add_argument("--no-dry-run", action="store_true",
                   help="Thực thi thật (mặc định dry-run).")

    return p

# ----------------------------
# Handlers
# ----------------------------

def _handle_cleanup(args: argparse.Namespace) -> int:
    report = run_cleanup(
        logs_dir=Path(args.logs_dir),
        report_dir=Path(args.report_dir) if args.report_dir else None,
        keep_runs=args.keep_runs,
        runs_older_than_days=args.runs_older_than_days,
        compress_runs_older_than_days=args.compress_runs_older_than_days,
        keep_reports_days=args.keep_reports_days,
        tmp_prefix=args.tmp_prefix,
        tmp_older_than_hours=args.tmp_older_than_hours,
        dry_run=not args.no_dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

def _handle_run(args: argparse.Namespace) -> int:
    if not args.input:
        print("[ERROR] Missing input checklist file.\n", file=sys.stderr)
        return 2
    if not os.path.exists(args.input):
        print(f"[ERROR] Input not found: {args.input}", file=sys.stderr)
        return 2

    # Chỉ lấy các tham số thuộc RUN để truyền vào run_once
    run_kwargs_keys = [
        "input", "logs_dir", "top", "workers", "proc", "timeout", "retries",
        "estimate", "plan_only", "json_out", "csv_out_dir", "save_report", "out_dir"
    ]
    run_kwargs: Dict[str, Any] = {k: getattr(args, k) for k in run_kwargs_keys}

    run_once(**run_kwargs)

    if getattr(args, "plan_only", False):
        return 0

    if getattr(args, "post_cleanup", False):
        # cleanup an toàn (dry-run)
        report_dir = getattr(args, "out_dir", None) or os.getenv("SECAPP_REPORT_DIR")
        report = run_cleanup(
            logs_dir=Path(args.logs_dir),
            report_dir=Path(report_dir) if report_dir else None,
            keep_runs=LOG_ROTATE_KEEP,
            runs_older_than_days=None,
            compress_runs_older_than_days=None,
            keep_reports_days=30,
            tmp_prefix="security_app_",
            tmp_older_than_hours=12,
            dry_run=True,
        )
        print("\n[POST-CLEANUP] (dry-run)")
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0

# ----------------------------
# Entry
# ----------------------------

def main(argv: Optional[list[str]] = None) -> int:
    # Giữ alias 'query' nếu codebase có (không bắt buộc)
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "query":
        try:
            from security_app.app.query import main as query_main
        except Exception as e:
            print(f"[ERROR] query subcommand unavailable: {e}", file=sys.stderr)
            return 2
        return query_main(argv[1:])

    # Alias 'cleanup' -> chuyển thành '--cleanup' rồi parse
    if argv and argv[0] == "cleanup":
        argv = ["--cleanup"] + argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cleanup:
        return _handle_cleanup(args)
    else:
        return _handle_run(args)

if __name__ == "__main__":
    raise SystemExit(main())
