# tests/core/test_command.py
import pytest
import subprocess
import time
from unittest.mock import patch, MagicMock, call
from security_app.models import CmdResult, Settings
from security_app.core.command import (
    _build_clean_env,
    _run_once,
    _to_result,
    run_command,
    _SAFE_ENV_BASE # Import for comparison
)
# Assuming default_settings provides base settings
from security_app.settings import default_settings

# --- Test Helpers ---

def test_build_clean_env():
    """Tests that _build_clean_env creates the expected minimal environment."""
    # Pass a dummy parent env to ensure it's ignored when clean_env=True (default behavior implied)
    parent_env = {"SOME_VAR": "value", "PATH": "/usr/local/bin"}
    clean_env = _build_clean_env(parent_env)
    assert clean_env == _SAFE_ENV_BASE
    # Ensure parent env variables (except defaults) are not included
    assert "SOME_VAR" not in clean_env
    # Check PATH is overwritten, not extended
    assert clean_env["PATH"] == _SAFE_ENV_BASE["PATH"]

# --- Mock subprocess.run for _run_once ---
@patch('subprocess.run')
def test_run_once_success(mock_subprocess_run):
    """Tests _run_once simulating a successful command execution."""
    cmd = "echo success"
    settings = default_settings()
    # Configure the mock to return a CompletedProcess object
    mock_result = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="success\n", stderr="")
    mock_subprocess_run.return_value = mock_result

    result = _run_once(cmd, timeout=10.0, settings=settings)

    mock_subprocess_run.assert_called_once_with(
        cmd, shell=True, text=True, capture_output=True,
        timeout=10.0,
        cwd="/", # Default cwd from settings
        env=_SAFE_ENV_BASE, # Default clean env
        close_fds=True, start_new_session=True
    )
    assert result == mock_result

@patch('subprocess.run')
def test_run_once_failure(mock_subprocess_run):
    """Tests _run_once simulating a command failure."""
    cmd = "grep non_existent_pattern /dev/null"
    settings = default_settings()
    mock_result = subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="grep error")
    mock_subprocess_run.return_value = mock_result

    result = _run_once(cmd, timeout=5.0, settings=settings)

    mock_subprocess_run.assert_called_once() # Check args if needed
    assert result.returncode == 1
    assert result.stderr == "grep error"

@patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="sleep 5", timeout=1.0, output="partial out", stderr="partial err"))
def test_run_once_timeout(mock_subprocess_run):
    """Tests _run_once simulating a timeout."""
    cmd = "sleep 5"
    settings = default_settings()

    # The side_effect directly raises the exception
    with pytest.raises(subprocess.TimeoutExpired) as excinfo:
        _run_once(cmd, timeout=1.0, settings=settings)

    mock_subprocess_run.assert_called_once()
    # Check exception attributes if needed
    assert excinfo.value.cmd == cmd
    assert excinfo.value.timeout == 1.0
    assert excinfo.value.stdout == "partial out" # Check if these are captured by run

@patch('subprocess.run', side_effect=FileNotFoundError("command not found: fakecmd"))
def test_run_once_file_not_found(mock_subprocess_run):
    """Tests _run_once simulating FileNotFoundError."""
    cmd = "fakecmd"
    settings = default_settings()

    with pytest.raises(FileNotFoundError, match="fakecmd"):
        _run_once(cmd, timeout=5.0, settings=settings)

    mock_subprocess_run.assert_called_once()

# --- Test _to_result ---
def test_to_result():
    """Tests the conversion to CmdResult."""
    start_time = time.time() - 0.12345 # Simulate ~0.1235s duration
    res = _to_result("mycmd", 0, "output", "", start_time)
    assert isinstance(res, CmdResult)
    assert res.cmd == "mycmd"
    assert res.returncode == 0
    assert res.stdout == "output"
    assert res.stderr == ""
    assert res.ok is True
    assert res.duration_sec == pytest.approx(0.1235, abs=0.001)

    res_fail = _to_result("failcmd", 1, "", "error", start_time)
    assert res_fail.ok is False
    assert res_fail.returncode == 1

    res_timeout = _to_result("timeoutcmd", None, "partial", "TIMEOUT", start_time)
    assert res_timeout.ok is False
    assert res_timeout.returncode is None

# --- Test run_command (Main Logic) ---

# Mock dependencies used by run_command
@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None) # Mock sleep to speed up tests
def test_run_command_success_first_try(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests successful execution on the first attempt."""
    cmd = "echo ok"
    settings = default_settings()
    mock_compute_risk.return_value = MagicMock(level='low', score=0, factors=[])
    mock_assert_len.return_value = None # No exception
    mock_deny.return_value = None # Not denied
    mock_run_once.return_value = subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")

    result = run_command(cmd, settings)

    mock_compute_risk.assert_called_once_with(cmd)
    mock_assert_len.assert_called_once_with(cmd)
    mock_deny.assert_called_once_with(cmd)
    mock_run_once.assert_called_once_with(cmd, settings.shell_timeout, settings)
    mock_sleep.assert_not_called() # No retries -> no sleep
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout == "ok"

@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None)
def test_run_command_denied_by_length(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests command denied due to length check."""
    cmd = "long command..."
    settings = default_settings()
    mock_compute_risk.return_value = MagicMock(level='low', score=10, factors=['chars'])
    # Simulate assert_cmd_length_safe raising an exception
    mock_assert_len.side_effect = Exception("DENIED length-check: chars 100>50")

    result = run_command(cmd, settings)

    mock_compute_risk.assert_called_once_with(cmd)
    mock_assert_len.assert_called_once_with(cmd)
    mock_deny.assert_not_called() # Deny check doesn't run if length fails
    mock_run_once.assert_not_called() # Doesn't run if length fails
    assert result.ok is False
    assert result.returncode is None
    assert "DENIED length-check" in result.stderr
    assert "RISK=low(10)" in result.stderr # Check risk info appended

@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None)
def test_run_command_denied_by_policy(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests command denied by deny_reason."""
    cmd = "rm -rf /"
    settings = default_settings()
    mock_compute_risk.return_value = MagicMock(level='critical', score=100, factors=['destructive'])
    mock_assert_len.return_value = None
    mock_deny.return_value = "DENIED by safety policy: matched /rm.../" # Deny reason

    result = run_command(cmd, settings)

    mock_compute_risk.assert_called_once_with(cmd)
    mock_assert_len.assert_called_once_with(cmd)
    mock_deny.assert_called_once_with(cmd)
    mock_run_once.assert_not_called() # Doesn't run if denied
    assert result.ok is False
    assert result.returncode is None
    assert "DENIED by safety policy" in result.stderr
    assert "RISK=critical(100)" in result.stderr

@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None)
def test_run_command_retry_on_failure(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests retry logic on command failure."""
    cmd = "flaky_command"
    # Settings with 1 retry attempt
    settings = Settings(shell_timeout=5.0, retry_attempts=1, retry_delay_sec=0.1, retry_on_timeout=True, clean_env=True)
    mock_compute_risk.return_value = MagicMock(level='low', score=0, factors=[])
    mock_assert_len.return_value = None
    mock_deny.return_value = None

    # Simulate failure then success
    mock_run_once.side_effect = [
        subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="fail"), # First call fails
        subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr=""),   # Second call succeeds
    ]

    result = run_command(cmd, settings)

    assert mock_run_once.call_count == 2
    mock_sleep.assert_called_once() # Slept once between retries
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout == "ok"

@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None)
def test_run_command_fail_after_retries(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests final failure after exhausting retries."""
    cmd = "always_fails"
    settings = Settings(shell_timeout=5.0, retry_attempts=1, retry_delay_sec=0.1, retry_on_timeout=True, clean_env=True)
    mock_compute_risk.return_value = MagicMock(level='low', score=0, factors=[])
    mock_assert_len.return_value = None
    mock_deny.return_value = None

    # Simulate failure on both attempts
    fail_result = subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="fail")
    mock_run_once.side_effect = [fail_result, fail_result]

    result = run_command(cmd, settings)

    assert mock_run_once.call_count == 2 # Initial + 1 retry
    assert mock_sleep.call_count == 1
    assert result.ok is False
    assert result.returncode == 1
    assert result.stderr == "fail"

@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None)
def test_run_command_timeout_no_retry(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests timeout when retry_on_timeout is False."""
    cmd = "timeout_cmd"
    settings = Settings(shell_timeout=1.0, retry_attempts=1, retry_delay_sec=0.1, retry_on_timeout=False, clean_env=True) # retry_on_timeout=False
    mock_compute_risk.return_value = MagicMock(level='low', score=0, factors=[])
    mock_assert_len.return_value = None
    mock_deny.return_value = None

    # Simulate timeout on first call
    mock_run_once.side_effect = subprocess.TimeoutExpired(cmd=cmd, timeout=1.0, output="partial", stderr="timeout msg")

    result = run_command(cmd, settings)

    mock_run_once.assert_called_once() # Only called once
    mock_sleep.assert_not_called()
    assert result.ok is False
    assert result.returncode is None
    assert "TIMEOUT after 1.0s" in result.stderr
    assert result.stdout == "partial" # Check partial output capture

@patch('security_app.core.command.compute_risk')
@patch('security_app.core.command.assert_cmd_length_safe')
@patch('security_app.core.command.deny_reason')
@patch('security_app.core.command._run_once')
@patch('time.sleep', return_value=None)
def test_run_command_timeout_with_retry(mock_sleep, mock_run_once, mock_deny, mock_assert_len, mock_compute_risk):
    """Tests timeout retry logic."""
    cmd = "timeout_retry"
    settings = Settings(shell_timeout=1.0, retry_attempts=1, retry_delay_sec=0.1, retry_on_timeout=True, clean_env=True) # retry_on_timeout=True
    mock_compute_risk.return_value = MagicMock(level='low', score=0, factors=[])
    mock_assert_len.return_value = None
    mock_deny.return_value = None

    # Simulate timeout then success
    mock_run_once.side_effect = [
        subprocess.TimeoutExpired(cmd=cmd, timeout=1.0, output="p1", stderr="t1"),
        subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr=""),
    ]

    result = run_command(cmd, settings)

    assert mock_run_once.call_count == 2
    assert mock_sleep.call_count == 1
    assert result.ok is True
    assert result.returncode == 0
    assert result.stdout == "ok"
