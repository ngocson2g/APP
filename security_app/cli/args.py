# security_app/cli/args.py
from __future__ import annotations

import argparse
import os

from security_app import config as CFG

# Tải các giá trị mặc định từ config
DEFAULT_LOGS_DIR = getattr(CFG, "DEFAULT_LOGS_DIR", "logs")
TOP_FAIL_LIMIT   = getattr(CFG, "TOP_FAIL_LIMIT", 20)
LOG_ROTATE_KEEP  = getattr(CFG, "LOG_ROTATE_KEEP", 50)

def build_parser() -> argparse.ArgumentParser:
    """Xây dựng trình phân tích cú pháp (parser) đối số dòng lệnh chính."""
    
    p = argparse.ArgumentParser(
        prog="security-app",
        description="Ubuntu hardening checker & runner",
        # Thêm định dạng trợ giúp để hiển thị giá trị mặc định
        formatter_class=argparse.ArgumentDefaultsHelpFormatter 
    )

    # --- Đối số Chính (Run & Cleanup) ---
    p.add_argument(
        "--cleanup", 
        action="store_true",
        help="Run the cleanup job for logs, reports, and tmp files. (Alias: 'cleanup')"
    )
    p.add_argument(
        "input", 
        nargs="?", 
        help="Path to the input checklist file (CSV, JSON, or XML) to run."
    )
    
    p.add_argument(
        "--list-all-rules", 
        action="store_true", 
        help="Print a space-separated list of all rules and their status.")

    # --- Nhóm Đối số CHẠY (RUN args) ---
    run_group = p.add_argument_group("Run Options", "Controls the execution of a security check")
    run_group.add_argument(
        "--silent",
        dest="print_report",
        action="store_false",
        help="Disable printing the summary report to the terminal. (Default: True)"
    )
    run_group.add_argument(
        "--logs-dir", 
        default=DEFAULT_LOGS_DIR,
        help="Base directory to store run logs."
    )
    run_group.add_argument(
        "--top", 
        type=int, 
        default=TOP_FAIL_LIMIT,
        help="Number of rules to show in the 'Top Failing Rules' table."
    )
    run_group.add_argument(
        "--workers", 
        type=int, 
        default=None,
        help="Set a fixed number of parallel workers. If unset, workers are auto-guessed based on load."
    )
    run_group.add_argument(
        "--proc", 
        action="store_true",
        help="Force the use of processes (ProcessPool) instead of threads. Recommended for CPU-bound tasks."
    )
    run_group.add_argument(
        "--timeout", 
        type=float, 
        default=None,
        help="Static timeout in seconds for *each* command. If unset, uses dynamic timeout based on p95 latency."
    )
    run_group.add_argument(
        "--retries", 
        type=int, 
        default=None,
        help="Number of times to retry a failed or timed-out command."
    )
    run_group.add_argument(
        "--estimate", 
        action="store_true",
        help="Show the pre-run execution plan and estimates, then proceed with the run."
    )
    run_group.add_argument(
        "--plan-only", 
        action="store_true",
        help="Show the pre-run execution plan and estimates, then exit *without* running."
    )
    run_group.add_argument(
        "--json-out", 
        default=None,
        help="Path to output the final summary report as a single JSON file."
    )
    run_group.add_argument(
        "--csv-out-dir", 
        default=None,
        help="Directory to output the final summary report as a bundle of CSV files."
    )
    run_group.add_argument(
        "--save-report", 
        action="store_true",
        help="Flag to trigger saving persistent report artifacts (e.g., for the web dashboard)."
    )
    run_group.add_argument(
        "--out-dir", 
        default=None,
        help="Specify a general output directory for saved reports or artifacts."
    )
    run_group.add_argument(
        "--post-cleanup", 
        action="store_true",
        help="Run a 'cleanup --dry-run' automatically after the check finishes to show what *could* be pruned."
    )

    # --- Nhóm Đối số DỌN DẸP (CLEANUP args) ---
    cleanup_group = p.add_argument_group("Cleanup Options", "Controls the cleanup job (invoked with --cleanup)")
    cleanup_group.add_argument(
        "--report-dir", 
        default=os.getenv("SECAPP_REPORT_DIR"),
        help="[Cleanup Mode] Directory where generated reports (PDF/Excel) are stored for pruning."
    )
    cleanup_group.add_argument(
        "--keep-runs", 
        type=int, 
        default=LOG_ROTATE_KEEP,
        help="[Cleanup Mode] Number of *most recent* run log directories to keep."
    )
    cleanup_group.add_argument(
        "--runs-older-than-days", 
        type=int, 
        default=None,
        help="[Cleanup Mode] Delete run log directories older than this many days."
    )
    cleanup_group.add_argument(
        "--compress-runs-older-than-days", 
        type=int, 
        default=None,
        help="[Cleanup Mode] Archive (tar.gz) run log directories older than this many days, instead of deleting."
    )
    cleanup_group.add_argument(
        "--keep-reports-days", 
        type=int, 
        default=30,
        help="[Cleanup Mode] Delete generated reports (in --report-dir) older than this many days."
    )
    cleanup_group.add_argument(
        "--tmp-prefix", 
        default="security_app_",
        help="[Cleanup Mode] Prefix for finding temporary files to clean."
    )
    cleanup_group.add_argument(
        "--tmp-older-than-hours", 
        type=int, 
        default=12,
        help="[Cleanup Mode] Delete temporary files older than this many hours."
    )
    cleanup_group.add_argument(
        "--no-dry-run", 
        action="store_true",
        help="[Cleanup Mode] **Required** to actually delete or compress files. Default is to only preview actions."
    )
    
    return p