# security_app/app/cli.py
import argparse
import os

from security_app.parsers.dispatch import parse_file
from security_app.core.runner import run_all_rules
from security_app.reporting.stats import compute_stats
from security_app.reporting.terminal import print_report
from security_app.config import DEFAULT_LOGS_DIR, TOP_FAIL_LIMIT
from security_app.settings import default_settings, with_overrides
from security_app.runtime.sudo import ensure_root
from security_app.settings import require_sudo_by_default


def main():
    if require_sudo_by_default():
        ensure_root(required=True)
    parser = argparse.ArgumentParser(
        prog="security-app",
        description="Run STIG/Checklist and report results."
    )
    parser.add_argument("input", help="Path to checklist file (CSV/JSON/XML).")
    parser.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR,
                        help=f"Base directory to store run logs (default: {DEFAULT_LOGS_DIR})")
    parser.add_argument("--top", type=int, default=TOP_FAIL_LIMIT,
                        help=f"Show at most N failing rules (default: {TOP_FAIL_LIMIT})")

    # Concurrency + timeout/retry (override trên Settings, không mutate globals)
    parser.add_argument("--workers", type=int, default=None, help="Max concurrent workers (default: CPU count).")
    parser.add_argument("--proc", action="store_true", help="Use process pool instead of threads.")
    parser.add_argument("--timeout", type=float, default=None, help="Per-command timeout in seconds.")
    parser.add_argument("--retries", type=int, default=None, help="Retry attempts.")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error(f"Input not found: {args.input}")

    # Tạo Settings cho phiên chạy này
    base = default_settings()
    settings = with_overrides(base, shell_timeout=args.timeout, retry_attempts=args.retries)

    rules = parse_file(args.input)  # list[Rule]
    run_results = run_all_rules(
        rules,
        log_base_dir=args.logs_dir,
        workers=args.workers,
        use_processes=args.proc,
        settings=settings,
    )
    stats = compute_stats(run_results)
    print_report(stats, limit_top=args.top)

if __name__ == "__main__":
    main()
