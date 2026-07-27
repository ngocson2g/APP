# tests/cli/test_main.py
import pytest
from unittest.mock import patch, MagicMock
import sys
# Bỏ các import thừa từ test_metrics.py nếu bạn thêm vào trước đó
# import json, time, os
# from pathlib import Path
# from security_app.core.runner.metrics import WaveMetricsSink

# Import main ở cấp độ module
from security_app.cli.main import main

# Vẫn patch build_parser và query.main bằng decorator
@patch('security_app.cli.main.build_parser')
@patch('security_app.app.query.main')
# Patch ensure_root cho test run
@patch('security_app.app.run.ensure_root')
def test_main_dispatch_run(mock_ensure_root, mock_query, mock_build_parser):
    """Kiểm tra main gọi handle_run khi không có cờ đặc biệt."""
    mock_args = MagicMock()
    mock_args.cleanup = False
    # FIX: Gán giá trị chuỗi cho input
    mock_args.input = "input.csv"
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_args.return_value = mock_args
    mock_build_parser.return_value = mock_parser_instance
    test_argv = ["security-app", "input.csv", "--workers", "4"]

    # Patch handlers dùng context manager, target là namespace của main.py
    with patch('security_app.cli.main.handle_cleanup') as mock_cleanup_ctx, \
         patch('security_app.cli.main.handle_run') as mock_run_ctx:

        mock_run_ctx.return_value = 0 # Set return value

        with patch.object(sys, 'argv', test_argv):
            exit_code = main()

        # Assertions
        mock_build_parser.assert_called_once()
        mock_parser_instance.parse_args.assert_called_once_with(test_argv[1:])
        mock_run_ctx.assert_called_once_with(mock_args)
        mock_cleanup_ctx.assert_not_called()
        mock_query.assert_not_called()
        # mock_ensure_root should be called inside run_once -> handle_run
        # Since handle_run is mocked here, ensure_root might not be called directly
        # Let's remove this check for now as it depends on handle_run's internal calls
        # mock_ensure_root.assert_called_once()
        assert exit_code == 0

@patch('security_app.cli.main.build_parser')
@patch('security_app.app.query.main')
def test_main_dispatch_cleanup_flag(mock_query, mock_build_parser):
    """Kiểm tra main gọi handle_cleanup khi có cờ --cleanup."""
    mock_args = MagicMock()
    mock_args.cleanup = True
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_args.return_value = mock_args
    mock_build_parser.return_value = mock_parser_instance
    test_argv = ["security-app", "--cleanup", "--keep-runs", "5"]

    # Patch handlers dùng context manager, target là namespace của main.py
    with patch('security_app.cli.main.handle_cleanup') as mock_cleanup_ctx, \
         patch('security_app.cli.main.handle_run') as mock_run_ctx:

        mock_cleanup_ctx.return_value = 0 # Set return value

        with patch.object(sys, 'argv', test_argv):
            exit_code = main()

        # Assertions
        mock_parser_instance.parse_args.assert_called_once_with(test_argv[1:])
        mock_cleanup_ctx.assert_called_once_with(mock_args) # Should pass now
        mock_run_ctx.assert_not_called()
        mock_query.assert_not_called()
        assert exit_code == 0

@patch('security_app.cli.main.build_parser')
@patch('security_app.app.query.main')
def test_main_dispatch_cleanup_alias(mock_query, mock_build_parser):
    """Kiểm tra main xử lý alias 'cleanup' thành cờ --cleanup."""
    mock_args = MagicMock()
    mock_args.cleanup = True
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_args.return_value = mock_args
    mock_build_parser.return_value = mock_parser_instance
    test_argv = ["security-app", "cleanup", "--keep-runs", "5"]
    expected_parse_argv = ["--cleanup", "--keep-runs", "5"]

    # Patch handlers dùng context manager, target là namespace của main.py
    with patch('security_app.cli.main.handle_cleanup') as mock_cleanup_ctx, \
         patch('security_app.cli.main.handle_run') as mock_run_ctx:

        mock_cleanup_ctx.return_value = 0 # Set return value

        with patch.object(sys, 'argv', test_argv):
            exit_code = main()

        # Assertions
        mock_parser_instance.parse_args.assert_called_once_with(expected_parse_argv)
        mock_cleanup_ctx.assert_called_once_with(mock_args) # Should pass now
        mock_run_ctx.assert_not_called()
        mock_query.assert_not_called()
        assert exit_code == 0

@patch('security_app.cli.main.build_parser')
@patch('security_app.app.query.main')
def test_main_dispatch_query_alias(mock_query, mock_build_parser):
    """Kiểm tra main gọi query_main khi có alias 'query'."""
    test_argv = ["security-app", "query", "--last", "1"]
    mock_query.return_value = 0

    # Patch handlers (optional here but consistent)
    with patch('security_app.cli.main.handle_cleanup') as mock_cleanup_ctx, \
         patch('security_app.cli.main.handle_run') as mock_run_ctx:

        with patch.object(sys, 'argv', test_argv):
            exit_code = main()

        # Assertions
        mock_build_parser.assert_not_called()
        mock_run_ctx.assert_not_called()
        mock_cleanup_ctx.assert_not_called()
        mock_query.assert_called_once_with(test_argv[2:])
        assert exit_code == 0

# --- HÀM TEST THỪA ĐÃ BỊ XÓA ---