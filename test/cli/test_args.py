# tests/cli/test_args.py
import pytest
from security_app.cli.args import build_parser

def test_build_parser_run_default():
    """Kiểm tra parse lệnh 'run' cơ bản."""
    parser = build_parser()
    args = parser.parse_args(["input.csv"])
    assert args.input == "input.csv"
    assert args.cleanup is False
    # Kiểm tra các giá trị mặc định khác
    assert args.logs_dir == "logs" # Giả sử DEFAULT_LOGS_DIR là "logs"
    assert args.workers is None
    assert args.proc is False
    assert args.json_out is None

def test_build_parser_run_with_flags():
    """Kiểm tra parse lệnh 'run' với nhiều cờ."""
    parser = build_parser()
    args = parser.parse_args([
        "scan.json",
        "--logs-dir", "/var/log/secapp",
        "--workers", "8",
        "--proc",
        "--timeout", "30.5",
        "--json-out", "report.json",
        "--estimate",
    ])
    assert args.input == "scan.json"
    assert args.logs_dir == "/var/log/secapp"
    assert args.workers == 8
    assert args.proc is True
    assert args.timeout == 30.5
    assert args.json_out == "report.json"
    assert args.estimate is True
    assert args.plan_only is False
    assert args.cleanup is False

def test_build_parser_cleanup_flag():
    """Kiểm tra parse với cờ --cleanup."""
    parser = build_parser()
    args = parser.parse_args(["--cleanup", "--keep-runs", "10", "--no-dry-run"])
    assert args.cleanup is True
    assert args.input is None # Input không cần thiết cho cleanup
    assert args.keep_runs == 10
    assert args.no_dry_run is True
    # Kiểm tra giá trị mặc định cho cleanup
    assert args.runs_older_than_days is None

# Thêm các test case khác cho các tổ hợp cờ khác nhau của 'run' và 'cleanup'
