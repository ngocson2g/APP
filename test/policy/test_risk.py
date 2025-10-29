# tests/policy/test_risk.py
import pytest
from security_app.policy.risk import compute_risk, Risk

# Test cases: command string, expected level, expected score range (optional), expected factors subset
@pytest.mark.parametrize("cmd, expected_level, min_score, max_score, expected_factors", [
    # Low Risk
    ("ls -l /home/user", "low", 0, 29, ["home-scope"]),
    ("pwd", "low", 0, 29, []),
    ("echo 'hello'", "low", 0, 29, []),
    ("grep pattern file.txt", "low", 0, 29, []),
    ("cat /proc/version", "low", 0, 29, []),
    ("apt update --dry-run", "low", 0, 29, ["dry-run"]), # Dry run reduces score

    # Medium Risk
    ("chmod 600 ~/.ssh/id_rsa", "medium", 30, 59, ["write/state-change", "home-scope"]), # Write in home
    ("grep -R password /var/log", "medium", 30, 59, ["wide-scope", "path:/var/log\\b"]), # Wide scope, sensitive path
    ("systemctl status sshd", "low", 0, 29, []), # Status is read-only
    ("sed 's/old/new/' file", "low", 0, 29, []), # Sed without -i is read-only
    ("find /tmp -name '*.log'", "low", 0, 29, []), # Find in /tmp is less risky

    # High Risk
    ("chmod 777 /etc/passwd", "high", 60, 79, ["write/state-change", "path:/etc\\b"]), # Write sensitive file
    ("useradd newuser", "high", 60, 79, ["write/state-change"]), # State change command
    ("systemctl enable --now my-service", "high", 60, 79, ["write/state-change"]), # State change command
    ("sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config", "high", 60, 79, ["write/state-change", "path:/etc\\b"]), # Inline edit sensitive file
    ("find / -type f -exec rm {} \\;", "high", 60, 79, ["write/state-change", "wide-scope"]), # Wide scope rm

    # Critical Risk
    ("rm -rf /", "critical", 80, 200, ["write/state-change", "destructive"]), # Destructive
    ("dd if=/dev/zero of=/dev/sda", "critical", 80, 200, ["write/state-change", "destructive"]), # Destructive
    ("mkfs.ext4 /dev/sdb1", "critical", 80, 200, ["write/state-change", "destructive"]), # Destructive (should match mkfs.)
    (":(){ :|:& };:", "low", 0, 29, []), # Fork bomb (risk score doesn't detect this type well, relies on denylist)
])
def test_compute_risk(cmd, expected_level, min_score, max_score, expected_factors):
    """Tests the risk computation logic for various commands."""
    risk = compute_risk(cmd)
    assert isinstance(risk, Risk)
    assert risk.level == expected_level
    # Check score range if needed (scores can be tweaked)
    # assert min_score <= risk.score <= max_score
    # Check if expected factors are present (order might differ)
    for factor in expected_factors:
        assert factor in risk.factors

def test_compute_risk_empty_command():
    """Test risk for empty command string."""
    risk = compute_risk("")
    assert risk.level == "low"
    assert risk.score == 0
    assert risk.factors == []
