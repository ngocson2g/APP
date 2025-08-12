import sys
from utils.parse_file import parse_file
from utils.runner import run_all_rules
from utils.report_terminal import compute_stats, print_report

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 main.py <path_to_checklist_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    rules = parse_file(file_path)
    print(f"Total rules parsed: {len(rules)}")

    # 1) Chạy & lưu log
    run_results = run_all_rules(rules, log_base_dir="logs")

    # 2) Tổng hợp & in ra terminal
    stats = compute_stats(run_results)
    print_report(stats, limit_top=10)
