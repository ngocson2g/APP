import argparse
import os
from security_app.parsers.dispatch import parse_file
from security_app.core.runner import run_all_rules
from security_app.reporting.terminal import compute_stats, print_report

def main():
    parser = argparse.ArgumentParser(
        prog="security-app",
        description="Run STIG/Checklist and report results."
    )
    parser.add_argument(
        "input",
        help="Path to checklist file (CSV/JSON/XML)."
    )
    parser.add_argument(
        "--logs-dir", default="logs",
        help="Base directory to store run logs (default: logs)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error(f"Input not found: {args.input}")

    rules = parse_file(args.input)  # expect a list[dict] with 'check', 'id', 'title', 'severity'/ 'impact'
    run_results = run_all_rules(rules, log_base_dir=args.logs_dir)
    stats = compute_stats(run_results)
    print_report(stats)

if __name__ == "__main__":
    main()
