# tests/core/runner/test_init.py (Create this file)
import pytest
from security_app.core.runner import _is_cpuish_cmd, _classify_chunk, _count_timeouts
from security_app.models import CmdResult

# --- Test _is_cpuish_cmd ---

@pytest.mark.parametrize("cmd, expected", [
    ("grep -R 'pattern' /etc", True), # grep -R
    ("find / -name '*.log'", True),   # find /
    ("sha256sum /bin/bash", True),     # CPUish token
    ("awk '{print $1}' file.txt", True), # CPUish token
    ("cat /var/log/syslog | grep error", True), # Contains CPUish token (grep)
    ("ls -l /home", False),           # Basic IO
    ("systemctl status sshd", False), # Basic status check
    ("echo 'hello'", False),          # Simple echo
    ("curl http://example.com", False), # Network IO
    ("zgrep 'error' /var/log/syslog.gz", True), # zgrep token
    ("command with * glob", True),    # Glob pattern
])
def test_is_cpuish_cmd(cmd, expected):
    """Test the CPU-ish command heuristic."""
    assert _is_cpuish_cmd(cmd) == expected

# --- Test _classify_chunk ---

def test_classify_chunk():
    """Test classifying a chunk based on its commands."""
    assert _classify_chunk(["ls", "pwd", "echo"]) == "io"
    assert _classify_chunk(["ls", "grep -R home", "echo"]) == "cpu" # One CPUish makes chunk CPUish
    assert _classify_chunk(["find /", "sha256sum file"]) == "cpu"
    assert _classify_chunk([]) == "io" # Empty chunk defaults to IO
    assert _classify_chunk(None) == "io" # None chunk defaults to IO

# --- Test _count_timeouts ---

def test_count_timeouts():
    """Test counting timeout results."""
    results = [
        CmdResult(cmd="c1", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True),
        CmdResult(cmd="c2", returncode=None, stdout="", stderr="TIMEOUT after 10s", duration_sec=10.0, ok=False),
        CmdResult(cmd="c3", returncode=1, stdout="", stderr="Error", duration_sec=0.2, ok=False),
        CmdResult(cmd="c4", returncode=None, stdout="partial", stderr="Some error then TIMEOUT", duration_sec=5.0, ok=False),
        CmdResult(cmd="c5", returncode=None, stdout="", stderr="DENIED", duration_sec=0.0, ok=False), # Not a timeout
    ]
    assert _count_timeouts(results) == 2
    assert _count_timeouts([]) == 0
    assert _count_timeouts(None) == 0
    assert _count_timeouts([results[0], results[2], results[4]]) == 0 # No timeouts
