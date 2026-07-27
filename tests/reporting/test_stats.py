# tests/reporting/test_stats.py
import pytest
from security_app.models import Rule, CmdResult
from security_app.reporting.stats import compute_stats

# --- Fixtures ---

@pytest.fixture
def sample_run_results_ok():
    """Sample run results where all rules passed."""
    return [
        {
            "rule_index": 0,
            "rule": Rule(id="R1", title="Rule One", severity="high", check="$c1", fix="", description=""),
            "num_cmds": 1, "num_ok": 1, "num_fail": 0,
            "cmd_results": [CmdResult(cmd="c1", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True)]
        },
        {
            "rule_index": 1,
            "rule": Rule(id="R2", title="Rule Two", severity="medium", check="$c2\n$c3", fix="", description=""),
            "num_cmds": 2, "num_ok": 2, "num_fail": 0,
            "cmd_results": [
                CmdResult(cmd="c2", returncode=0, stdout="ok", stderr="", duration_sec=0.2, ok=True),
                CmdResult(cmd="c3", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True),
            ]
        },
    ]

@pytest.fixture
def sample_run_results_mixed():
    """Sample run results with mixed pass/fail and severities."""
    return [
        { # Rule 0: High, Fail (1/2 cmds fail)
            "rule_index": 0,
            "rule": Rule(id="R-HIGH-FAIL", title="High Fail Rule", severity="high", check="$c1\n$c2", fix="", description=""),
            "num_cmds": 2, "num_ok": 1, "num_fail": 1,
            "cmd_results": [
                CmdResult(cmd="c1", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True),
                CmdResult(cmd="c2", returncode=1, stdout="", stderr="err", duration_sec=0.3, ok=False),
            ]
        },
        { # Rule 1: Medium, OK
            "rule_index": 1,
            "rule": Rule(id="R-MED-OK", title="Medium OK Rule", severity="medium", check="$c3", fix="", description=""),
            "num_cmds": 1, "num_ok": 1, "num_fail": 0,
            "cmd_results": [CmdResult(cmd="c3", returncode=0, stdout="ok", stderr="", duration_sec=0.2, ok=True)]
        },
        { # Rule 2: Medium, Fail (both cmds fail)
            "rule_index": 2,
            "rule": Rule(id="R-MED-FAIL", title="Medium Fail Rule", severity="medium", check="$c4\n$c5", fix="", description=""),
            "num_cmds": 2, "num_ok": 0, "num_fail": 2,
            "cmd_results": [
                CmdResult(cmd="c4", returncode=1, stdout="", stderr="e1", duration_sec=0.4, ok=False),
                CmdResult(cmd="c5", returncode=127, stdout="", stderr="e2", duration_sec=0.1, ok=False),
            ]
        },
        { # Rule 3: Low, OK (No severity specified -> unknown -> low by default?) Check code. Assume unknown.
            "rule_index": 3,
            "rule": Rule(id="R-UNK-OK", title="Unknown OK Rule", severity="", check="$c6", fix="", description=""),
            "num_cmds": 1, "num_ok": 1, "num_fail": 0,
            "cmd_results": [CmdResult(cmd="c6", returncode=0, stdout="ok", stderr="", duration_sec=0.05, ok=True)]
        },
    ]

# --- Test compute_stats ---

def test_compute_stats_all_ok(sample_run_results_ok):
    """Test stats computation when all rules pass."""
    stats = compute_stats(sample_run_results_ok)

    # Totals
    totals = stats["totals"]
    assert totals["total_rules"] == 2
    assert totals["rules_all_ok"] == 2
    assert totals["rules_with_fail"] == 0
    assert totals["pass_rate"] == pytest.approx(100.0)
    assert totals["total_cmds"] == 3
    assert totals["total_ok"] == 3
    assert totals["total_fail"] == 0

    # By Severity
    by_sev = stats["by_severity"]
    assert "high" in by_sev and "medium" in by_sev
    assert by_sev["high"]["rules"] == 1
    assert by_sev["high"]["rules_fail"] == 0
    assert by_sev["high"]["cmds"] == 1
    assert by_sev["high"]["ok"] == 1
    assert by_sev["high"]["fail"] == 0
    assert by_sev["medium"]["rules"] == 1
    assert by_sev["medium"]["rules_fail"] == 0
    assert by_sev["medium"]["cmds"] == 2
    assert by_sev["medium"]["ok"] == 2
    assert by_sev["medium"]["fail"] == 0
    assert "low" not in by_sev
    assert "unknown" not in by_sev

    # Top Failing
    assert stats["top_failing_rules"] == []

    # All Results (check normalization)
    assert len(stats["all_results"]) == 2
    assert isinstance(stats["all_results"][0]["rule"], Rule)
    assert stats["all_results"][0]["rule"].id == "R1"


def test_compute_stats_mixed(sample_run_results_mixed):
    """Test stats computation with mixed results."""
    stats = compute_stats(sample_run_results_mixed)

    # Totals (2 OK, 2 Fail out of 4 rules)
    totals = stats["totals"]
    assert totals["total_rules"] == 4
    assert totals["rules_all_ok"] == 2 # R-MED-OK, R-UNK-OK
    assert totals["rules_with_fail"] == 2 # R-HIGH-FAIL, R-MED-FAIL
    assert totals["pass_rate"] == pytest.approx(50.0)
    assert totals["total_cmds"] == 6 # 2+1+2+1
    assert totals["total_ok"] == 3 # 1+1+0+1
    assert totals["total_fail"] == 3 # 1+0+2+0

    # By Severity
    by_sev = stats["by_severity"]
    assert "high" in by_sev and "medium" in by_sev and "unknown" in by_sev
    assert "low" not in by_sev # Severity "" becomes "unknown"

    # High: 1 rule, 1 fail rule, 2 cmds, 1 ok, 1 fail
    assert by_sev["high"] == {"rules": 1, "rules_fail": 1, "cmds": 2, "ok": 1, "fail": 1}
    # Medium: 2 rules, 1 fail rule, 3 cmds, 1 ok, 2 fail
    assert by_sev["medium"] == {"rules": 2, "rules_fail": 1, "cmds": 3, "ok": 1, "fail": 2}
    # Unknown: 1 rule, 0 fail rules, 1 cmd, 1 ok, 0 fail
    assert by_sev["unknown"] == {"rules": 1, "rules_fail": 0, "cmds": 1, "ok": 1, "fail": 0}

    # Top Failing (sorted by num_fail desc, then index asc)
    # R-MED-FAIL (idx 2, fail 2), R-HIGH-FAIL (idx 0, fail 1)
    top = stats["top_failing_rules"]
    assert len(top) == 2
    assert top[0][0] == 2 # index
    assert top[0][1] == "R-MED-FAIL" # id
    assert top[0][2] == "medium" # severity
    assert top[0][3] == 2 # num_fail
    assert top[0][4] == "Medium Fail Rule" # title

    assert top[1][0] == 0 # index
    assert top[1][1] == "R-HIGH-FAIL" # id
    assert top[1][2] == "high" # severity
    assert top[1][3] == 1 # num_fail
    assert top[1][4] == "High Fail Rule" # title

    # All Results
    assert len(stats["all_results"]) == 4

def test_compute_stats_empty_input():
    """Test stats computation with empty input."""
    stats = compute_stats([])
    totals = stats["totals"]
    assert totals["total_rules"] == 0
    assert totals["rules_all_ok"] == 0
    assert totals["rules_with_fail"] == 0
    assert totals["pass_rate"] == 0.0
    assert totals["total_cmds"] == 0
    assert totals["total_ok"] == 0
    assert totals["total_fail"] == 0
    assert stats["by_severity"] == {}
    assert stats["top_failing_rules"] == []
    assert stats["all_results"] == []
