# security_app/cli/handlers.py
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from security_app import config as CFG
from security_app.app.run import run_once
from security_app.maintenance.cleanup import run_cleanup

LOG_ROTATE_KEEP = getattr(CFG, "LOG_ROTATE_KEEP", 50)

def handle_cleanup(args) -> int:
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

def handle_run(args) -> int:
    if not args.input:
        print("[ERROR] Missing input checklist file.\n", file=sys.stderr)
        return 2
    if not os.path.exists(args.input):
        print(f"[ERROR] Input not found: {args.input}", file=sys.stderr)
        return 2

    run_kwargs_keys = ["input","logs_dir","top","workers","proc","timeout","retries",
                       "estimate","plan_only","json_out","html_out","csv_out_dir","save_report","out_dir","list_all_rules"]
    run_kwargs: dict[str, Any] = {k: getattr(args, k) for k in run_kwargs_keys}
    run_once(**run_kwargs)

    if getattr(args, "plan_only", False):
        return 0

    if getattr(args, "post_cleanup", False):
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
