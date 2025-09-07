from __future__ import annotations
import argparse, os
from security_app import config as CFG

DEFAULT_LOGS_DIR = getattr(CFG, "DEFAULT_LOGS_DIR", "logs")
TOP_FAIL_LIMIT   = getattr(CFG, "TOP_FAIL_LIMIT", 20)
LOG_ROTATE_KEEP  = getattr(CFG, "LOG_ROTATE_KEEP", 50)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="security-app",
                                description="Ubuntu hardening checker & runner")
    # Alias cleanup qua --cleanup (không dùng subparsers)
    p.add_argument("--cleanup", action="store_true",
                   help="Chạy job dọn dẹp (logs/report/tmp). Dùng alias 'cleanup' cũng được.")
    # Positional cho run
    p.add_argument("input", nargs="?", help="Checklist (CSV/JSON/XML) khi chạy mặc định.")

    # ---- RUN args ----
    p.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR)
    p.add_argument("--top", type=int, default=TOP_FAIL_LIMIT)
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--proc", action="store_true")
    p.add_argument("--timeout", type=float, default=None)
    p.add_argument("--retries", type=int, default=None)
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--plan-only", action="store_true")
    p.add_argument("--json-out", default=None)
    p.add_argument("--csv-out-dir", default=None)
    p.add_argument("--save-report", action="store_true")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--post-cleanup", action="store_true")

    # ---- CLEANUP args ----
    p.add_argument("--report-dir", default=os.getenv("SECAPP_REPORT_DIR"))
    p.add_argument("--keep-runs", type=int, default=LOG_ROTATE_KEEP)
    p.add_argument("--runs-older-than-days", type=int, default=None)
    p.add_argument("--compress-runs-older-than-days", type=int, default=None)
    p.add_argument("--keep-reports-days", type=int, default=30)
    p.add_argument("--tmp-prefix", default="security_app_")
    p.add_argument("--tmp-older-than-hours", type=int, default=12)
    p.add_argument("--no-dry-run", action="store_true")
    return p
