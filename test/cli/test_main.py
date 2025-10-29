# tests/cli/test_main.py
import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock các hàm handlers và parser
@patch('security_app.cli.main.build_parser')
@patch('security_app.cli.main.handle_run')
@patch('security_app.cli.main.handle_cleanup')
@patch('security_app.cli.main.query_main') # Mock cả query_main nếu có
def test_main_dispatch_run(mock_query, mock_cleanup, mock_run, mock_build_parser):
    """Kiểm tra main gọi handle_run khi không có cờ đặc biệt."""
    from security_app.cli.main import main
    # Giả lập parser trả về args cho lệnh run
    mock_args = MagicMock()
    mock_args.cleanup = False
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_args.return_value = mock_args
    mock_build_parser.return_value = mock_parser_instance

    # Giả lập sys.argv
    test_argv = ["security-app", "input.csv", "--workers", "4"]
    with patch.object(sys, 'argv', test_argv):
        exit_code = main() # Gọi main không có đối số

    mock_build_parser.assert_called_once()
    # parse_args được gọi với ['input.csv', '--workers', '4']
    mock_parser_instance.parse_args.assert_called_once_with(test_argv[1:])
    mock_run.assert_called_once_with(mock_args)
    mock_cleanup.assert_not_called()
    mock_query.assert_not_called()
    # Giả sử handle_run trả về 0
    mock_run.return_value = 0
    assert exit_code == 0

@patch('security_app.cli.main.build_parser')
@patch('security_app.cli.main.handle_run')
@patch('security_app.cli.main.handle_cleanup')
@patch('security_app.cli.main.query_main')
def test_main_dispatch_cleanup_flag(mock_query, mock_cleanup, mock_run, mock_build_parser):
    """Kiểm tra main gọi handle_cleanup khi có cờ --cleanup."""
    from security_app.cli.main import main
    mock_args = MagicMock()
    mock_args.cleanup = True # Parser nhận diện cờ cleanup
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_args.return_value = mock_args
    mock_build_parser.return_value = mock_parser_instance

    test_argv = ["security-app", "--cleanup", "--keep-runs", "5"]
    with patch.object(sys, 'argv', test_argv):
        exit_code = main()

    mock_parser_instance.parse_args.assert_called_once_with(test_argv[1:])
    mock_cleanup.assert_called_once_with(mock_args)
    mock_run.assert_not_called()
    mock_query.assert_not_called()
    mock_cleanup.return_value = 0
    assert exit_code == 0

@patch('security_app.cli.main.build_parser')
@patch('security_app.cli.main.handle_run')
@patch('security_app.cli.main.handle_cleanup')
@patch('security_app.cli.main.query_main')
def test_main_dispatch_cleanup_alias(mock_query, mock_cleanup, mock_run, mock_build_parser):
    """Kiểm tra main xử lý alias 'cleanup' thành cờ --cleanup."""
    from security_app.cli.main import main
    mock_args = MagicMock()
    mock_args.cleanup = True # Parser được gọi với cờ --cleanup đã chuyển đổi
    mock_parser_instance = MagicMock()
    mock_parser_instance.parse_args.return_value = mock_args
    mock_build_parser.return_value = mock_parser_instance

    test_argv = ["security-app", "cleanup", "--keep-runs", "5"] # Dùng alias
    expected_parse_argv = ["--cleanup", "--keep-runs", "5"] # Argv sau khi chuyển đổi alias
    with patch.object(sys, 'argv', test_argv):
        exit_code = main()

    # parse_args được gọi với argv đã sửa đổi
    mock_parser_instance.parse_args.assert_called_once_with(expected_parse_argv)
    mock_cleanup.assert_called_once_with(mock_args)
    mock_run.assert_not_called()
    mock_query.assert_not_called()
    mock_cleanup.return_value = 0
    assert exit_code == 0

@patch('security_app.cli.main.build_parser')
@patch('security_app.cli.main.handle_run')
@patch('security_app.cli.main.handle_cleanup')
@patch('security_app.cli.main.query_main')
def test_main_dispatch_query_alias(mock_query, mock_cleanup, mock_run, mock_build_parser):
    """Kiểm tra main gọi query_main khi có alias 'query'."""
    from security_app.cli.main import main

    test_argv = ["security-app", "query", "--last", "1"] # Dùng alias query
    with patch.object(sys, 'argv', test_argv):
        exit_code = main()

    # Parser và handlers khác không được gọi
    mock_build_parser.assert_not_called()
    mock_run.assert_not_called()
    mock_cleanup.assert_not_called()
    # query_main được gọi với các đối số sau alias
    mock_query.assert_called_once_with(test_argv[2:]) # ['--last', '1']
    mock_query.return_value = 0
    assert exit_code == 0
