# tests/app/test_run.py
import pytest
from unittest.mock import patch, MagicMock
import os
from security_app.models import Rule, Settings
from security_app.app.run import run_once, _autotimeout_from_est

# --- Test _autotimeout_from_est (Keep existing test) ---
@pytest.mark.parametrize("p95, expected_timeout", [
    (0.5, 5.0), (1.0, 5.0), (2.0, 7.0), (10.0, 31.0),
    (20.0, 60.0), (30.0, 60.0), (None, None), (0, None), (-1.0, None),
])
def test_autotimeout_from_est(p95, expected_timeout):
    assert _autotimeout_from_est(p95) == expected_timeout

# --- Mocks for run_once dependencies ---
# Use fixtures for commonly mocked objects across multiple tests
@pytest.fixture
def mock_deps():
    with patch('security_app.app.run.ensure_root') as m_ensure, \
         patch('security_app.app.run.os.path.exists', return_value=True) as m_exists, \
         patch('security_app.app.run.parse_file') as m_parse, \
         patch('security_app.app.run.estimate_plan') as m_estimate, \
         patch('security_app.app.run.print_estimate') as m_print_est, \
         patch('security_app.app.run.run_all_rules') as m_run_all, \
         patch('security_app.app.run.compute_stats') as m_compute, \
         patch('security_app.app.run.print_report') as m_print_rep, \
         patch('security_app.app.run.dump_stats_json') as m_dump_json, \
         patch('security_app.app.run.write_stats_csv_bundle') as m_write_csv, \
         patch('security_app.settings.require_sudo_by_default', return_value=False) as m_req_sudo: # Assume no sudo needed by default for tests
        yield {
            "ensure": m_ensure, "exists": m_exists, "parse": m_parse, "estimate": m_estimate,
            "print_est": m_print_est, "run_all": m_run_all, "compute": m_compute,
            "print_rep": m_print_rep, "dump_json": m_dump_json, "write_csv": m_write_csv,
            "req_sudo": m_req_sudo
        }

# --- Test Cases for run_once ---

def test_run_once_basic_flow(mock_deps):
    """Kiểm tra luồng chạy cơ bản của run_once."""
    # Arrange
    mock_rules = [Rule(id="R1", description="", check="$ cmd1", fix="", severity="high")]
    mock_deps["parse"].return_value = mock_rules
    mock_est_result = {"p95_cmd": 2.0, "workers_suggested": "4", "wall_seconds": 10.0} # workers as string
    mock_deps["estimate"].return_value = mock_est_result
    mock_run_results = [{"rule_index": 0, "rule": mock_rules[0], "num_ok": 1, "num_fail": 0}]
    mock_deps["run_all"].return_value = mock_run_results
    mock_stats_result = {"totals": {"pass_rate": 100.0}, "all_results": mock_run_results}
    mock_deps["compute"].return_value = mock_stats_result

    # Act
    result = run_once("input.csv", workers=4, json_out="report.json", csv_out_dir="csv_out")

    # Assert
    mock_deps["req_sudo"].assert_called_once() # Sudo check called
    mock_deps["ensure"].assert_not_called() # ensure_root not called as require_sudo mock returns False
    mock_deps["exists"].assert_called_once_with("input.csv")
    mock_deps["parse"].assert_called_once_with("input.csv")
    mock_deps["estimate"].assert_called_once_with(mock_rules, logs_base_dir="logs", workers=4, use_processes=False, per_command=True)
    mock_deps["print_est"].assert_not_called()
    mock_deps["run_all"].assert_called_once()
    call_args_run_all = mock_deps["run_all"].call_args.kwargs
    assert call_args_run_all['workers'] == 4
    assert call_args_run_all['settings'].shell_timeout == 7.0 # Auto timeout from p95=2.0
    mock_deps["compute"].assert_called_once_with(mock_run_results)
    mock_deps["print_rep"].assert_called_once_with(mock_stats_result, limit_top=ANY)
    mock_deps["dump_json"].assert_called_once_with(mock_stats_result, "report.json")
    mock_deps["write_csv"].assert_called_once_with(mock_stats_result, out_dir="csv_out")
    assert result["estimate"] == mock_est_result
    assert result["stats"] == mock_stats_result

def test_run_once_estimate_flag(mock_deps):
    """Test behavior with --estimate flag."""
    mock_rules = [Rule(id="R1", description="", check="$ cmd1", fix="", severity="high")]
    mock_deps["parse"].return_value = mock_rules
    mock_est_result = {"p95_cmd": 1.0, "workers_suggested": "2"}
    mock_deps["estimate"].return_value = mock_est_result
    # Mock subsequent calls as they should still run
    mock_deps["run_all"].return_value = []
    mock_deps["compute"].return_value = {"totals": {}}

    result = run_once("input.xml", estimate=True) # estimate=True

    mock_deps["estimate"].assert_called_once()
    mock_deps["print_est"].assert_called_once_with(mock_est_result) # Should print estimate
    mock_deps["run_all"].assert_called_once() # Should still call run_all
    mock_deps["compute"].assert_called_once()
    mock_deps["print_rep"].assert_called_once() # Should still print final report

def test_run_once_plan_only_flag(mock_deps):
    """Test behavior with --plan-only flag."""
    mock_rules = [Rule(id="R1", description="", check="$ cmd1", fix="", severity="high")]
    mock_deps["parse"].return_value = mock_rules
    mock_est_result = {"p95_cmd": 1.0, "workers_suggested": "2"}
    mock_deps["estimate"].return_value = mock_est_result

    result = run_once("input.xml", plan_only=True) # plan_only=True

    mock_deps["estimate"].assert_called_once()
    mock_deps["print_est"].assert_called_once_with(mock_est_result) # Should print estimate
    mock_deps["run_all"].assert_not_called() # Should NOT call run_all
    mock_deps["compute"].assert_not_called()
    mock_deps["print_rep"].assert_not_called()
    assert result["estimate"] == mock_est_result
    assert result["stats"] is None

def test_run_once_input_not_found(mock_deps):
    """Test error handling when input file doesn't exist."""
    mock_deps["exists"].return_value = False # Simulate file not found
    with pytest.raises(FileNotFoundError, match="Input not found: nonexistent.csv"):
        run_once("nonexistent.csv")
    mock_deps["parse"].assert_not_called() # Should exit before parsing

def test_run_once_uses_suggested_workers(mock_deps):
    """Test that suggested workers are used if --workers is not provided."""
    mock_rules = [Rule(id="R1", description="", check="$ cmd1", fix="", severity="high")]
    mock_deps["parse"].return_value = mock_rules
    # Estimate suggests 3 workers (as string, simulating potential type issue)
    mock_est_result = {"p95_cmd": 1.0, "workers_suggested": "3"}
    mock_deps["estimate"].return_value = mock_est_result
    mock_deps["run_all"].return_value = [] # Prevent further execution

    run_once("input.csv", workers=None) # workers=None

    mock_deps["estimate"].assert_called_once()
    mock_deps["run_all"].assert_called_once()
    # Check that run_all was called with the integer version of suggested workers
    call_args_run_all = mock_deps["run_all"].call_args.kwargs
    assert call_args_run_all['workers'] == 3
