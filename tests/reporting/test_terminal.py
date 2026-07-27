# tests/reporting/test_terminal.py
import pytest
from unittest.mock import patch, MagicMock # <<< THÊM MagicMock VÀO ĐÂY
from security_app.models import Rule # Needed for stats structure
from security_app.reporting.terminal import print_report
from security_app.config import TOP_FAIL_LIMIT # Import default limit

# --- Sample Stats Data Fixtures ---

@pytest.fixture
def stats_all_ok():
    """Stats dict simulating a run where all rules passed."""
    return {
        "totals": {
            "total_rules": 2, "rules_all_ok": 2, "rules_with_fail": 0,
            "pass_rate": 100.0, "total_cmds": 3, "total_ok": 3, "total_fail": 0,
        },
        "by_severity": {
            "high": {"rules": 1, "rules_fail": 0, "cmds": 1, "ok": 1, "fail": 0},
            "medium": {"rules": 1, "rules_fail": 0, "cmds": 2, "ok": 2, "fail": 0},
        },
        "top_failing_rules": [],
        "all_results": [
            {"rule_index": 0, "rule": Rule(id="R-HIGH-OK", severity="high", title="High OK", check="",fix="",description=""), "num_ok": 1, "num_fail": 0, "cmd_results": []},
            {"rule_index": 1, "rule": Rule(id="R-MED-OK", severity="medium", title="Med OK", check="",fix="",description=""), "num_ok": 2, "num_fail": 0, "cmd_results": []},
        ]
    }

@pytest.fixture
def stats_mixed_results():
    """Stats dict simulating mixed pass/fail and denied rules."""
    # Simplified version of the one used in test_stats.py
    rule_high_fail = Rule(id="R-HIGH-FAIL", severity="high", title="High Fail Rule", check="$c1\n$c2",fix="",description="")
    rule_med_ok = Rule(id="R-MED-OK", severity="medium", title="Medium OK Rule", check="$c3",fix="",description="")
    rule_med_fail = Rule(id="R-MED-FAIL", severity="medium", title="Medium Fail Rule 2", check="$c4\n$c5",fix="",description="")
    rule_denied = Rule(id="R-DENIED", severity="low", title="Denied Rule", check="$rm file",fix="",description="") # Assume 'rm file' is denied
    return {
        "totals": {
            "total_rules": 4, "rules_all_ok": 1, "rules_with_fail": 2, # Note: Denied rule doesn't count as fail here based on stats logic
            "pass_rate": 25.0, "total_cmds": 5, "total_ok": 2, "total_fail": 3, # Assuming denied cmd counted in total but not ok/fail
        },
        "by_severity": {
            "high": {"rules": 1, "rules_fail": 1, "cmds": 2, "ok": 1, "fail": 1},
            "medium": {"rules": 2, "rules_fail": 1, "cmds": 3, "ok": 1, "fail": 2},
            "low": {"rules": 1, "rules_fail": 0, "cmds": 0, "ok": 0, "fail": 0}, # Denied rule cmds might not register here depending on logic
        },
        "top_failing_rules": [
            (2, "R-MED-FAIL", "medium", 2, "Medium Fail Rule 2"),
            (0, "R-HIGH-FAIL", "high", 1, "High Fail Rule"),
        ],
        "all_results": [
            {"rule_index": 0, "rule": rule_high_fail, "num_ok": 1, "num_fail": 1, "cmd_results": [MagicMock(stderr="")]*2}, # Mock CmdResult
            {"rule_index": 1, "rule": rule_med_ok, "num_ok": 1, "num_fail": 0, "cmd_results": [MagicMock(stderr="")]},
            {"rule_index": 2, "rule": rule_med_fail, "num_ok": 0, "num_fail": 2, "cmd_results": [MagicMock(stderr="")]*2},
            # Simulate a result for the denied rule
            {"rule_index": 3, "rule": rule_denied, "num_ok": 0, "num_fail": 0, # num_fail is 0 here
             "cmd_results": [MagicMock(stderr="DENIED by safety policy")]},
        ]
    }

# --- Test print_report ---

# Mock _term_width to ensure consistent table formatting regardless of actual terminal size
@patch('security_app.reporting.terminal._term_width', return_value=120)
def test_print_report_all_ok(mock_width, capsys, stats_all_ok):
    """Test print_report output when all rules pass."""
    print_report(stats_all_ok)
    captured = capsys.readouterr()
    output = captured.out

    # Check header
    assert "CHECKLIST EXECUTION SUMMARY" in output
    # Check Totals section
    assert "Total rules: 2" in output
    assert "All OK: 2" in output
    assert "With failures: 0" in output
    assert "Pass rate: 100.00%" in output
    assert "Total commands: 3" in output
    # Check By Severity section (presence of headers and severities)
    assert "By severity:" in output
    assert "Severity" in output and "Rules" in output and "OK bar" in output
    assert "high" in output and "1 ok / 0 fail" in output
    assert "medium" in output and "2 ok / 0 fail" in output
    # Check Top Failing section
    assert "Top failing rules" in output
    assert "(Không có rule lỗi)" in output # No failing rules message
    # Check Denied section
    assert "Denied by safety policy:" not in output # No denied rules
    # Check ID lists
    assert "Failing Rule IDs (0):" in output
    assert "OK Rule IDs (2):" in output
    assert "R-HIGH-OK" in output and "R-MED-OK" in output

@patch('security_app.reporting.terminal._term_width', return_value=120)
def test_print_report_mixed_results(mock_width, capsys, stats_mixed_results):
    """Test print_report output with mixed pass/fail/denied rules."""
    print_report(stats_mixed_results, limit_top=5) # Limit top failing to 5 for test
    captured = capsys.readouterr()
    output = captured.out

    # Check header
    assert "CHECKLIST EXECUTION SUMMARY" in output
    # Check Totals section
    assert "Total rules: 4" in output
    assert "All OK: 1" in output # Based on stats_mixed_results logic
    assert "With failures: 2" in output # Based on stats_mixed_results logic
    assert "Pass rate: 25.00%" in output
    # Check By Severity section
    assert "By severity:" in output
    assert "high" in output and "0 ok / 1 fail" in output # High severity row
    assert "medium" in output and "1 ok / 1 fail" in output # Medium severity row
    assert "low" in output and "1 ok / 0 fail" in output # Low severity row (denied)
    # Check Top Failing section (shows top 2)
    assert f"Top failing rules (max 5):" in output
    assert "#" in output and "Rule ID" in output and "Sev" in output and "#CmdFail" in output and "Title" in output
    assert "R-MED-FAIL" in output and "medium" in output and "2" in output # Top fail 1
    assert "R-HIGH-FAIL" in output and "high" in output and "1" in output # Top fail 2
    assert "(Không có rule lỗi)" not in output
    # Check Denied section
    assert "Denied by safety policy:" in output
    assert "R-DENIED" in output and "low" in output and "1" in output # Check denied rule info
    # Check ID lists
    assert "Failing Rule IDs (2):" in output
    assert "R-HIGH-FAIL" in output and "R-MED-FAIL" in output
    assert "OK Rule IDs (2):" in output # R-MED-OK and the denied R-DENIED (as num_fail=0)
    assert "R-MED-OK" in output and "R-DENIED" in output

@patch('security_app.reporting.terminal._term_width', return_value=120)
def test_print_report_no_results(mock_width, capsys):
    """Test print_report with empty stats."""
    empty_stats = {
        "totals": {"total_rules": 0, "rules_all_ok": 0, "rules_with_fail": 0, "pass_rate": 0.0,
                   "total_cmds": 0, "total_ok": 0, "total_fail": 0},
        "by_severity": {},
        "top_failing_rules": [],
        "all_results": []
    }
    print_report(empty_stats)
    captured = capsys.readouterr()
    output = captured.out

    assert "CHECKLIST EXECUTION SUMMARY" in output
    assert "Total rules: 0" in output
    assert "By severity:" in output # Section header still prints
    assert "Top failing rules" in output
    assert "(Không có rule lỗi)" in output
    assert "Denied by safety policy:" not in output
    assert "Failing Rule IDs (0):" in output
    assert "OK Rule IDs (0):" in output
