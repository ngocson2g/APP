# tests/core/test_estimator.py
import pytest
import statistics
from unittest.mock import patch, MagicMock, mock_open, call
from security_app.models import Rule
from security_app.core.estimator import (
    _base_cost,
    _shape_multipliers,
    _first_token,
    _read_history,
    _estimate_cmd_seconds,
    _list_allowed_cmds,
    _simulate_makespan,
    estimate_plan,
    PAT_COST # Import to check against
)

# --- Test Helpers ---

def test_first_token():
    assert _first_token(" ls -l / ") == "ls"
    assert _first_token("grep ") == "grep"
    assert _first_token("") == ""
    assert _first_token(None) == "" # Should handle None input gracefully

def test_base_cost():
    """Test heuristic base cost calculation."""
    assert _base_cost("apt install package") == 5.0 # Matches apt install pattern
    assert _base_cost("dpkg -l | grep ssh") == 0.8 # Matches dpkg -l
    assert _base_cost("find /home -name '*.py'") == 1.2 # Matches find
    assert _base_cost("cat /etc/passwd") == 0.05 # Matches cat
    assert _base_cost("ls -R /") == _base_cost("ls /") # Longer command -> slightly higher fallback base
    assert _base_cost("unknown command") == pytest.approx(0.05 + 0.01 * 0) # 2 tokens
    assert _base_cost("unknown command with more tokens") == pytest.approx(0.05 + 0.01 * 3) # 5 tokens

def test_shape_multipliers():
    """Test calculation of shape multipliers."""
    assert _shape_multipliers("ls -l") == 1.0 # No special shapes
    assert _shape_multipliers("grep -R pattern /") > 1.0 # Recursive and root scan
    assert _shape_multipliers("cat file | sort | uniq") > 1.0 # Pipes increase multiplier
    assert _shape_multipliers("find /var/log -name '*.gz'") > 1.0 # Sensitive path multiplier
    assert _shape_multipliers("ls *.txt") > 1.0 # Glob multiplier

# Mock file system for _read_history
@patch('glob.glob')
@patch('os.path.isdir', return_value=True)
@patch('builtins.open', new_callable=mock_open)
def test_read_history(mock_file_open, mock_isdir, mock_glob):
    """Test reading command durations from mock log files."""
    # Mock glob to return run dirs and log files
    mock_glob.side_effect = lambda pattern: {
        'logs/*': ['logs/run1', 'logs/run2'],
        'logs/run1/rule-*.log': ['logs/run1/rule-001_A.log', 'logs/run1/rule-002_B.log'],
        'logs/run2/rule-*.log': ['logs/run2/rule-001_A.log'],
    }[pattern]

    # Mock file content
    log1_content = """
$ ls -l
RC=0 | OK=True | 0.100s
$ grep error /var/log/syslog
RC=1 | OK=False | 0.500s
"""
    log2_content = """
$ cat file
RC=0 | OK=True | 0.020s
"""
    log3_content = """
$ ls -R /home
RC=0 | OK=True | 1.200s
$ ls -l /tmp # Another ls command
RC=0 | OK=True | 0.150s
"""
    # Configure mock_open to return different content based on path
    mock_file_open.side_effect = lambda path, *args, **kwargs: {
        'logs/run1/rule-001_A.log': mock_open(read_data=log1_content).return_value,
        'logs/run1/rule-002_B.log': mock_open(read_data=log2_content).return_value,
        'logs/run2/rule-001_A.log': mock_open(read_data=log3_content).return_value,
    }.get(path, mock_open(read_data="").return_value) # Default empty

    history = _read_history("logs", max_files=10) # Set max_files low enough

    assert "ls" in history
    assert "grep" in history
    assert "cat" in history
    # ls durations: 0.1, 1.2, 0.15
    ls_mean, ls_p95, ls_n = history["ls"]
    assert ls_n == 3
    assert ls_mean == pytest.approx( (0.1 + 1.2 + 0.15) / 3 )
    assert ls_p95 == pytest.approx(statistics.quantiles([0.1, 1.2, 0.15], n=20)[18]) # P95 of [0.1, 0.15, 1.2]

    # grep: 0.5
    grep_mean, grep_p95, grep_n = history["grep"]
    assert grep_n == 1
    assert grep_mean == 0.5
    assert grep_p95 == 0.5 # p95 is max for n=1

    # cat: 0.02
    cat_mean, cat_p95, cat_n = history["cat"]
    assert cat_n == 1
    assert cat_mean == 0.02
    assert cat_p95 == 0.02

def test_estimate_cmd_seconds():
    """Test blending heuristic cost with history."""
    hist_data = {"ls": (0.12, 0.18, 10), "grep": (0.6, 0.9, 3)} # grep has few samples (<5)
    base_cost_ls = _base_cost("ls -l /") * _shape_multipliers("ls -l /")
    base_cost_grep = _base_cost("grep error log") * _shape_multipliers("grep error log")

    # ls uses history (n=10 >= 5)
    est_ls = _estimate_cmd_seconds("ls -l /", hist_data)
    assert est_ls == pytest.approx(0.5 * base_cost_ls + 0.5 * 0.12)

    # grep does not use history (n=3 < 5)
    est_grep = _estimate_cmd_seconds("grep error log", hist_data)
    assert est_grep == pytest.approx(base_cost_grep)

    # Unknown command uses heuristic only
    est_unknown = _estimate_cmd_seconds("unknown cmd", hist_data)
    assert est_unknown == pytest.approx(_base_cost("unknown cmd") * _shape_multipliers("unknown cmd"))

@patch('security_app.core.estimator.deny_reason')
def test_list_allowed_cmds(mock_deny_reason):
    """Test separating allowed and denied commands."""
    mock_deny_reason.side_effect = lambda cmd: "DENIED" if "rm" in cmd else None
    rules = [
        Rule(id="R1", description="", check="$ ls -l\n$ rm -rf /tmp/test", fix="", severity="high"),
        Rule(id="R2", description="Desc for R2", check="$ pwd", fix="Fix for R2", severity="low"),
        Rule(id="R3", description="", check="$ rm file", fix="", severity="medium"), # Denied
    ]
    allowed, denied_count = _list_allowed_cmds(rules)
    assert allowed == ["ls -l", "pwd"]
    assert denied_count == 2

def test_simulate_makespan():
    """Test the LPT makespan simulation."""
    durations = [5.0, 4.0, 3.0, 2.0, 1.0] # Total 15s
    overhead = 0.1 # 10% overhead

    # 1 worker: Makespan = sum + overhead
    assert _simulate_makespan(durations, 1, overhead) == pytest.approx(15.0 * 1.1)

    # 2 workers: LPT -> [5], [4,1], [3,2] -> Bins [5], [5], [5] -> Max bin = 5. Makespan = 5 * 1.1
    # Actual LPT: B1=[], B2=[]
    # 5.0 -> B1=[5.0]
    # 4.0 -> B2=[4.0]
    # 3.0 -> B2=[4.0, 3.0] -> Load 7.0 (Mistake here, LPT assigns to *least* loaded)
    # LPT Correct: B1=[], B2=[]
    # 5.0 -> B1=[5.0] (Load 5.0)
    # 4.0 -> B2=[4.0] (Load 4.0)
    # 3.0 -> B2=[4.0, 3.0] (Load 7.0) -> Still wrong. Assign 3.0 to B2. Load 4.0 < 5.0
    # LPT Corrected Again:
    # Tasks: [5, 4, 3, 2, 1]
    # Bins: [0, 0]
    # Add 5 -> [5, 0]
    # Add 4 -> [5, 4]
    # Add 3 -> [5, 4+3=7] -> Assign to B1. [5+3=8, 4]
    # Add 2 -> Assign to B2. [8, 4+2=6]
    # Add 1 -> Assign to B2. [8, 6+1=7]
    # Max bin = 8. Makespan = 8 * 1.1 = 8.8
    assert _simulate_makespan(durations, 2, overhead) == pytest.approx(8.0 * 1.1)


    # 3 workers: LPT -> Bins [0,0,0]
    # Add 5 -> [5, 0, 0]
    # Add 4 -> [5, 4, 0]
    # Add 3 -> [5, 4, 3]
    # Add 2 -> [5, 4, 3+2=5] -> Assign to B3
    # Add 1 -> [5, 4+1=5, 5] -> Assign to B2
    # Max bin = 5. Makespan = 5 * 1.1 = 5.5
    assert _simulate_makespan(durations, 3, overhead) == pytest.approx(5.0 * 1.1)

    assert _simulate_makespan([], 2, overhead) == 0.0 # Empty input

# Mock dependencies for estimate_plan
@patch('security_app.core.estimator._list_allowed_cmds')
@patch('security_app.core.estimator._read_history')
@patch('security_app.core.estimator._estimate_cmd_seconds')
@patch('security_app.core.estimator.auto_guess_workers')
@patch('security_app.core.estimator._simulate_makespan')
def test_estimate_plan(mock_simulate, mock_guess_workers, mock_estimate_cmd, mock_read_hist, mock_list_allowed):
    """Test the main estimate_plan function orchestrating helpers."""
    rules = [MagicMock(spec=Rule)] * 10 # 10 dummy rules
    mock_list_allowed.return_value = (["cmd"] * 50, 5) # 50 allowed, 5 denied
    mock_read_hist.return_value = {"cmd": (0.2, 0.3, 10)}
    # Let estimate_cmd_seconds return 0.2 for all 50 commands
    mock_estimate_cmd.return_value = 0.2
    mock_guess_workers.return_value = 4 # Suggest 4 workers
    mock_simulate.return_value = 3.0 # Simulate makespan returns 3.0s

    result = estimate_plan(rules, logs_base_dir="logs", workers=None, use_processes=False)

    mock_list_allowed.assert_called_once_with(rules)
    mock_read_hist.assert_called_once_with("logs")
    assert mock_estimate_cmd.call_count == 50 # Called for each allowed cmd
    # Check auto_guess_workers was called correctly (IO pool type)
    mock_guess_workers.assert_called_once_with(50, False, [0.2] * 50) # Assuming sample is just the estimates
    # Check _simulate_makespan called with estimated durations and suggested workers
    mock_simulate.assert_called_once_with([0.2] * 50, 4, overhead=0.08) # Overhead for threads

    # Check result dictionary structure and values
    assert result["n_rules"] == 10
    assert result["n_cmds"] == 50
    assert result["n_denied"] == 5
    assert result["workers_suggested"] == 4
    assert result["use_processes"] is False
    assert result["p50_cmd"] == pytest.approx(0.2)
    assert result["p95_cmd"] == pytest.approx(0.2) # p95 of constant list is the constant
    assert result["cpu_seconds_sum"] == pytest.approx(50 * 0.2)
    assert result["wall_seconds"] == pytest.approx(3.0)
    assert "S (" in result["complexity"] # wall < 60s
