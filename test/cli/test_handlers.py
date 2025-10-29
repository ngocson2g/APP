# tests/cli/test_handlers.py
import pytest
from unittest.mock import patch, MagicMock, ANY
import argparse
from pathlib import Path

# Giả lập các module/hàm được gọi bởi handlers
# Patch trực tiếp vào nơi chúng được import và sử dụng trong handlers.py
@patch('security_app.cli.handlers.run_once')
@patch('security_app.cli.handlers.run_cleanup')
@patch('security_app.cli.handlers.os.path.exists', return_value=True) # Giả sử file input tồn tại
def test_handle_run_calls_run_once(mock_os_exists, mock_run_cleanup, mock_run_once):
    """Kiểm tra handle_run gọi run_once với đúng đối số."""
    from security_app.cli.handlers import handle_run
    args = argparse.Namespace(
        input="input.csv",
        logs_dir="logs",
        top=10,
        workers=4,
        proc=False,
        timeout=None,
        retries=1,
        estimate=False,
        plan_only=False,
        json_out="out.json",
        csv_out_dir=None,
        save_report=False,
        out_dir=None,
        post_cleanup=False # Tắt cleanup sau khi chạy để test đơn giản
    )

    exit_code = handle_run(args)

    assert exit_code == 0
    mock_run_once.assert_called_once()
    # Kiểm tra một vài đối số quan trọng được truyền đúng
    call_kwargs = mock_run_once.call_args.kwargs
    assert call_kwargs.get('input') == "input.csv"
    assert call_kwargs.get('workers') == 4
    assert call_kwargs.get('retries') == 1
    assert call_kwargs.get('json_out') == "out.json"
    mock_run_cleanup.assert_not_called() # Vì post_cleanup=False

@patch('security_app.cli.handlers.run_once')
@patch('security_app.cli.handlers.run_cleanup')
def test_handle_run_calls_post_cleanup(mock_run_cleanup, mock_run_once):
    """Kiểm tra handle_run gọi run_cleanup khi có cờ --post-cleanup."""
    from security_app.cli.handlers import handle_run
    args = argparse.Namespace(
        input="input.csv",
        logs_dir="logs",
        top=10, workers=None, proc=False, timeout=None, retries=None,
        estimate=False, plan_only=False, json_out=None, csv_out_dir=None,
        save_report=False, out_dir=None,
        post_cleanup=True # Bật cleanup
    )
    # Giả lập run_once trả về kết quả nào đó (không quan trọng nội dung)
    mock_run_once.return_value = {"estimate": {}, "stats": {}}

    exit_code = handle_run(args)

    assert exit_code == 0
    mock_run_once.assert_called_once()
    mock_run_cleanup.assert_called_once()
    # Kiểm tra cleanup được gọi với dry_run=True (mặc định cho post-cleanup)
    call_kwargs_cleanup = mock_run_cleanup.call_args.kwargs
    assert call_kwargs_cleanup.get('dry_run') is True
    assert call_kwargs_cleanup.get('logs_dir') == Path("logs")

@patch('security_app.cli.handlers.run_once')
@patch('security_app.cli.handlers.os.path.exists', return_value=False) # Giả sử file input KHÔNG tồn tại
def test_handle_run_input_not_found(mock_os_exists, mock_run_once, capsys):
    """Kiểm tra handle_run trả về lỗi nếu input không tồn tại."""
    from security_app.cli.handlers import handle_run
    args = argparse.Namespace(input="nonexistent.csv")

    exit_code = handle_run(args)

    assert exit_code == 2
    mock_run_once.assert_not_called()
    captured = capsys.readouterr()
    assert "[ERROR] Input not found" in captured.err

def test_handle_run_missing_input(capsys):
    """Kiểm tra handle_run trả về lỗi nếu thiếu input."""
    from security_app.cli.handlers import handle_run
    args = argparse.Namespace(input=None) # Thiếu input

    exit_code = handle_run(args)

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "[ERROR] Missing input checklist file" in captured.err


@patch('security_app.cli.handlers.run_cleanup')
@patch('builtins.print') # Mock hàm print để kiểm tra output JSON
def test_handle_cleanup_calls_run_cleanup(mock_print, mock_run_cleanup):
    """Kiểm tra handle_cleanup gọi run_cleanup với đúng đối số."""
    from security_app.cli.handlers import handle_cleanup
    # Giả lập kết quả trả về từ run_cleanup
    mock_report = {"runs": {"deleted": ["run1"], "kept": ["run2"]}, "tmp": {"removed": []}}
    mock_run_cleanup.return_value = mock_report

    args = argparse.Namespace(
        logs_dir="logs_path",
        report_dir="reports_path",
        keep_runs=15,
        runs_older_than_days=30,
        compress_runs_older_than_days=60,
        keep_reports_days=45,
        tmp_prefix="secapp_",
        tmp_older_than_hours=24,
        no_dry_run=True # Test với dry_run=False
    )

    exit_code = handle_cleanup(args)

    assert exit_code == 0
    mock_run_cleanup.assert_called_once()
    call_kwargs = mock_run_cleanup.call_args.kwargs
    assert call_kwargs.get('logs_dir') == Path("logs_path")
    assert call_kwargs.get('report_dir') == Path("reports_path")
    assert call_kwargs.get('keep_runs') == 15
    assert call_kwargs.get('runs_older_than_days') == 30
    assert call_kwargs.get('compress_runs_older_than_days') == 60
    assert call_kwargs.get('keep_reports_days') == 45
    assert call_kwargs.get('tmp_prefix') == "secapp_"
    assert call_kwargs.get('tmp_older_than_hours') == 24
    assert call_kwargs.get('dry_run') is False # Vì --no-dry-run được set

    # Kiểm tra output JSON được in ra
    mock_print.assert_called_once()
    # Kiểm tra nội dung JSON được in ra (có thể cần json.loads để so sánh cấu trúc)
    # print_args = mock_print.call_args[0][0]
    # import json
    # assert json.loads(print_args) == mock_report
