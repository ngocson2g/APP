# tests/core/runner/test_merge.py
import pytest
from unittest.mock import MagicMock
from security_app.models import Rule, CmdResult
from security_app.core.runner.merge import _merge_and_log

@pytest.fixture
def mock_logger():
    """Fixture to create a mock RunLogger."""
    logger = MagicMock()
    logger.log_rule_result = MagicMock()
    return logger

def test_merge_and_log_all_ran_ok(mock_logger):
    """Test merging when all commands ran successfully."""
    # FIX: Add description and fix
    rule = Rule(id="R1", description="", check="$ cmd1\n$ cmd2", fix="", severity="high")
    idx = 0
    denied = []
    ran = [
        CmdResult(cmd="cmd1", returncode=0, stdout="ok1", stderr="", duration_sec=0.1, ok=True),
        CmdResult(cmd="cmd2", returncode=0, stdout="ok2", stderr="", duration_sec=0.2, ok=True),
    ]

    result = _merge_and_log(idx, rule, denied, ran, mock_logger)

    # Check logger call
    mock_logger.log_rule_result.assert_called_once()
    call_args = mock_logger.log_rule_result.call_args[0]
    assert call_args[0] == idx
    assert call_args[1] == rule
    assert call_args[2] == ran # merged list is just ran

    # Check returned summary
    assert result["rule_index"] == idx
    assert result["rule"] == rule
    assert result["cmd_results"] == ran
    assert result["num_cmds"] == 2
    assert result["num_ok"] == 2
    assert result["num_fail"] == 0

def test_merge_and_log_mixed_results(mock_logger):
    """Test merging with denied, failed, and ok commands."""
    # FIX: Add description and fix
    rule = Rule(id="R-MIX", description="Mixed rule desc", check="$ denied_cmd\n$ fail_cmd\n$ ok_cmd", fix="Mixed fix", severity="medium")
    idx = 1
    denied = [CmdResult(cmd="denied_cmd", returncode=None, stdout="", stderr="DENIED", duration_sec=0.0, ok=False)]
    ran = [
        CmdResult(cmd="fail_cmd", returncode=1, stdout="", stderr="error", duration_sec=0.3, ok=False),
        CmdResult(cmd="ok_cmd", returncode=0, stdout="success", stderr="", duration_sec=0.1, ok=True),
    ]
    merged_expected = denied + ran

    result = _merge_and_log(idx, rule, denied, ran, mock_logger)

    # Check logger call
    mock_logger.log_rule_result.assert_called_once_with(idx, rule, merged_expected)

    # Check returned summary
    assert result["rule_index"] == idx
    assert result["rule"] == rule
    assert result["cmd_results"] == merged_expected
    assert result["num_cmds"] == 3
    assert result["num_ok"] == 1 # Only ok_cmd
    assert result["num_fail"] == 2 # denied_cmd and fail_cmd

def test_merge_and_log_only_denied(mock_logger):
    """Test merging when all commands were denied."""
    # FIX: Add description and fix
    rule = Rule(id="R-DENY", description="", check="$ cmd1", fix="", severity="low")
    idx = 2
    denied = [CmdResult(cmd="cmd1", returncode=None, stdout="", stderr="DENIED", duration_sec=0.0, ok=False)]
    ran = []
    merged_expected = denied

    result = _merge_and_log(idx, rule, denied, ran, mock_logger)

    mock_logger.log_rule_result.assert_called_once_with(idx, rule, merged_expected)

    assert result["rule_index"] == idx
    assert result["num_cmds"] == 1
    assert result["num_ok"] == 0
    assert result["num_fail"] == 1