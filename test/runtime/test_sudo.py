# tests/runtime/test_sudo.py
import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Import functions to test
from security_app.runtime.sudo import (
    _needs_root,
    _preserve_env_flags,
    _resolve_entrypoint,
    reexec_with_sudo,
    ensure_root
)

# --- Test _needs_root ---

@patch('security_app.runtime.sudo.os.name', 'posix')
@patch('security_app.runtime.sudo.hasattr')
@patch('security_app.runtime.sudo.os.geteuid')
def test_needs_root_yes(mock_geteuid, mock_hasattr):
    """Test when running as non-root on posix."""
    mock_hasattr.return_value = True
    mock_geteuid.return_value = 1000 # Non-root UID
    assert _needs_root() is True

@patch('security_app.runtime.sudo.os.name', 'posix')
@patch('security_app.runtime.sudo.hasattr')
@patch('security_app.runtime.sudo.os.geteuid')
def test_needs_root_already_root(mock_geteuid, mock_hasattr):
    """Test when already running as root."""
    mock_hasattr.return_value = True
    mock_geteuid.return_value = 0 # Root UID
    assert _needs_root() is False

@patch('security_app.runtime.sudo.os.name', 'nt') # Simulate Windows
@patch('security_app.runtime.sudo.hasattr')
@patch('security_app.runtime.sudo.os.geteuid') # Should not be called
def test_needs_root_non_posix(mock_geteuid, mock_hasattr):
    """Test on non-posix systems."""
    assert _needs_root() is False
    mock_hasattr.assert_not_called()
    mock_geteuid.assert_not_called()

@patch('security_app.runtime.sudo.os.name', 'posix')
@patch('security_app.runtime.sudo.hasattr') # Simulate system without geteuid
def test_needs_root_no_geteuid(mock_hasattr):
    """Test on posix system without geteuid function."""
    mock_hasattr.return_value = False
    assert _needs_root() is False

# --- Test _preserve_env_flags ---

@patch('security_app.runtime.sudo.os.getenv')
def test_preserve_env_flags(mock_getenv):
    """Test generation of --preserve-env flag."""
    # Case 1: No relevant vars set
    mock_getenv.side_effect = lambda key: None
    assert _preserve_env_flags() == []

    # Case 2: Only PATH set
    mock_getenv.side_effect = lambda key: "/usr/bin" if key == "PATH" else None
    assert _preserve_env_flags() == ["--preserve-env=PATH"]

    # Case 3: Both PATH and LOGS_DIR set
    mock_getenv.side_effect = lambda key: {"PATH": "/bin", "LOGS_DIR": "/logs"}.get(key)
    # Order might vary, check content
    result = _preserve_env_flags()
    assert len(result) == 1
    assert "--preserve-env=" in result[0]
    assert "PATH" in result[0]
    assert "LOGS_DIR" in result[0]
    # Check comma separation (flexible order)
    assert ("PATH,LOGS_DIR" in result[0] or "LOGS_DIR,PATH" in result[0])

# --- Test _resolve_entrypoint ---

@patch('security_app.runtime.sudo.shutil.which')
def test_resolve_entrypoint(mock_which):
    """Test resolving the script entrypoint."""
    # Case 1: shutil.which finds the script in venv
    mock_which.return_value = "/path/to/venv/bin/security-app"
    assert _resolve_entrypoint("/usr/local/bin/security-app") == "/path/to/venv/bin/security-app"
    mock_which.assert_called_once_with("security-app")

    # Case 2: shutil.which does not find it, use argv[0]
    mock_which.reset_mock()
    mock_which.return_value = None
    assert _resolve_entrypoint("/usr/local/bin/security-app") == "/usr/local/bin/security-app"
    mock_which.assert_called_once_with("security-app")

# --- Test reexec_with_sudo ---

@patch('security_app.runtime.sudo.sys.argv', ['/usr/bin/python', 'arg1', '--flag'])
@patch('security_app.runtime.sudo._resolve_entrypoint', return_value='/resolved/script')
@patch('security_app.runtime.sudo._preserve_env_flags', return_value=['--preserve-env=VAR'])
@patch('security_app.runtime.sudo.os.execvp')
def test_reexec_with_sudo(mock_execvp, mock_preserve, mock_resolve):
    """Test the structure of the call to os.execvp."""
    # Simulate calling reexec without explicit argv
    with pytest.raises(SystemExit): # os.execvp raises this implicitly on success/replacement
         reexec_with_sudo()

    mock_resolve.assert_called_once_with('/usr/bin/python') # Called with sys.argv[0]
    mock_preserve.assert_called_once()
    # Check the arguments passed to os.execvp
    expected_args = [
        "sudo",                  # Command itself
        "--preserve-env=VAR",    # Flags from _preserve_env_flags
        "/resolved/script",      # Script path from _resolve_entrypoint
        "arg1",                  # Original arg 1
        "--flag",                # Original arg 2
    ]
    mock_execvp.assert_called_once_with("sudo", expected_args)

# --- Test ensure_root ---

@patch('security_app.runtime.sudo._needs_root')
@patch('security_app.runtime.sudo.reexec_with_sudo')
def test_ensure_root_not_required(mock_reexec, mock_needs):
    """Test ensure_root when required=False."""
    ensure_root(required=False)
    mock_needs.assert_not_called()
    mock_reexec.assert_not_called()

@patch('security_app.runtime.sudo._needs_root', return_value=False) # Simulate already root
@patch('security_app.runtime.sudo.reexec_with_sudo')
def test_ensure_root_already_root(mock_reexec, mock_needs):
    """Test ensure_root when already root."""
    ensure_root(required=True)
    mock_needs.assert_called_once()
    mock_reexec.assert_not_called()

@patch('security_app.runtime.sudo._needs_root', return_value=True) # Simulate needs root
@patch('security_app.runtime.sudo.reexec_with_sudo')
def test_ensure_root_needs_reexec(mock_reexec, mock_needs):
    """Test ensure_root triggers re-execution."""
    ensure_root(required=True)
    mock_needs.assert_called_once()
    mock_reexec.assert_called_once() # Should call reexec
