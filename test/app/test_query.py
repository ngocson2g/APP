# tests/app/test_query.py
import pytest
import json
from io import StringIO
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call, mock_open

# Import functions/constants to test/use
from security_app.app.query import query, main as query_main, _parse_dt, _pick_runs, _match_keywords, SEV_ORDER

# --- Test Helpers (Copied/adapted from previous tests if needed) ---
@pytest.mark.parametrize("input_str, expected_ts", [
    ("2025-10-29", datetime(2025, 10, 29, 0, 0, 0).timestamp()),
    ("2025-10-29 14:30:00", datetime(2025, 10, 29, 14, 30, 0).timestamp()),
    ("2025-10-29T08:00:00", datetime(2025, 10, 29, 8, 0, 0).timestamp()),
    (str(datetime(2025, 1, 1).timestamp()), datetime(2025, 1, 1).timestamp()),
    ("invalid-date", None), ("", None), (None, None),
])
def test_parse_dt(input_str, expected_ts):
    assert _parse_dt(input_str) == expected_ts

def test_pick_runs():
    runs = [
        {"id": "run1", "mtime": datetime(2025, 10, 29, 10, 0).timestamp()}, # newest
        {"id": "run2", "mtime": datetime(2025, 10, 29, 9, 0).timestamp()},
        {"id": "run3", "mtime": datetime(2025, 10, 28, 12, 0).timestamp()},
        {"id": "run4", "mtime": datetime(2025, 10, 27, 8, 0).timestamp()}, # oldest
    ]
    since = datetime(2025, 10, 28, 0, 0).timestamp()
    until = datetime(2025, 10, 29, 9, 30).timestamp()
    assert _pick_runs(runs, last=None, since=None, until=None) == runs
    assert _pick_runs(runs, last=2, since=None, until=None) == [runs[0], runs[1]]
    assert _pick_runs(runs, last=None, since=since, until=None) == [runs[0], runs[1], runs[2]]
    assert _pick_runs(runs, last=None, since=None, until=until) == [runs[1], runs[2], runs[3]]
    assert _pick_runs(runs, last=None, since=since, until=until) == [runs[1], runs[2]]
    assert _pick_runs(runs, last=1, since=since, until=None) == [runs[0]]

def test_match_keywords():
    rec = {"id": "RULE_123", "title": "Check SSH config", "severity": "high", "check": "$ grep PermitRoot /etc/ssh/sshd_config"}
    assert _match_keywords(rec, ["ssh"], "any") is True
    assert _match_keywords(rec, ["ssh"], "title") is True
    assert _match_keywords(rec, ["ssh"], "check") is True
    assert _match_keywords(rec, ["ssh"], "id") is False
    assert _match_keywords(rec, ["permitroot"], "any") is True
    assert _match_keywords(rec, ["permitroot"], "check") is True
    assert _match_keywords(rec, ["permitroot"], "title") is False
    assert _match_keywords(rec, ["ssh", "config"], "any") is True
    assert _match_keywords(rec, ["ssh", "nomatch"], "any") is False
    assert _match_keywords(rec, [], "any") is True
    assert _match_keywords(rec, None, "any") is True

# --- Mock Data for Main Query Function ---
MOCK_RUNS_LIST = [
    {"id": "run_new", "mtime": datetime(2025, 10, 30, 10, 0).timestamp(), "files": 2, "path": "/logs/run_new"},
    {"id": "run_old", "mtime": datetime(2025, 10, 28, 12, 0).timestamp(), "files": 1, "path": "/logs/run_old"},
]

MOCK_RULE_LOGS = {
    "/logs/run_new/rule-001_high_pass.log": {
        "id": "R-HIGH-PASS", "title": "High Pass", "severity": "high",
        "cmd_ok": 1, "cmd_fail": 0, "status": "ok", "check": "$ cmd1"
    },
    "/logs/run_new/rule-002_med_fail.log": {
        "id": "R-MED-FAIL", "title": "Medium Fail SSH", "severity": "medium",
        "cmd_ok": 0, "cmd_fail": 1, "status": "fail", "check": "$ cmd_ssh_fail"
    },
    "/logs/run_old/rule-001_high_fail.log": {
        "id": "R-HIGH-FAIL", "title": "High Fail Old", "severity": "high",
        "cmd_ok": 1, "cmd_fail": 2, "status": "fail", "check": "$ cmd_old_fail"
    },
}

# --- Test Main Query Function ---

@patch('security_app.app.query._list_runs', return_value=MOCK_RUNS_LIST)
@patch('security_app.app.query.glob.glob')
@patch('security_app.app.query._parse_rule_log')
@patch('security_app.app.query._table') # Mock table output
@patch('builtins.print') # Mock print for JSON output and messages
def test_query_table_output_all(mock_print, mock_table, mock_parse_log, mock_glob, mock_list_runs):
    """Test query with no filters, outputting a table."""
    # Arrange: Configure mocks
    def glob_side_effect(pattern):
        if "run_new" in pattern: return ["/logs/run_new/rule-001_high_pass.log", "/logs/run_new/rule-002_med_fail.log"]
        if "run_old" in pattern: return ["/logs/run_old/rule-001_high_fail.log"]
        return []
    mock_glob.side_effect = glob_side_effect
    mock_parse_log.side_effect = lambda fp: MOCK_RULE_LOGS.get(fp, {})

    # Act
    exit_code = query(
        logs_dir="/logs", run_id=None, last=None, since=None, until=None,
        severities=None, status=None, keywords=None, scope="any",
        output_json=False, limit=None
    )

    # Assert
    assert exit_code == 0
    mock_list_runs.assert_called_once_with("/logs")
    assert mock_glob.call_count == len(MOCK_RUNS_LIST) # Called once per run
    assert mock_parse_log.call_count == len(MOCK_RULE_LOGS) # Called once per log file found
    mock_table.assert_called_once() # Table printer was called

    # Check the data passed to the table (sorted: high_fail_old, high_pass, med_fail)
    call_args_table = mock_table.call_args[0]
    headers = call_args_table[1]['headers']
    rows = call_args_table[0]
    assert headers[3] == "Rule ID" # Basic header check
    assert len(rows) == 3
    # Check sorting (Severity Desc -> Cmd Fail Desc -> ID)
    assert rows[0][3] == "R-HIGH-FAIL" # High, 2 fails
    assert rows[1][3] == "R-HIGH-PASS" # High, 0 fails
    assert rows[2][3] == "R-MED-FAIL"  # Medium, 1 fail
    # Check a specific row content
    assert rows[0] == [1, 'run_old', ANY, 'R-HIGH-FAIL', 'high', 'fail', 1, 2, 'High Fail Old']

    # Check summary print message
    assert call('\nMatched 3 rule(s) across 2 run(s).') in mock_print.call_args_list

@patch('security_app.app.query._list_runs', return_value=MOCK_RUNS_LIST)
@patch('security_app.app.query.glob.glob')
@patch('security_app.app.query._parse_rule_log')
@patch('builtins.print') # Mock print for JSON output
def test_query_json_output_filtered(mock_print, mock_parse_log, mock_glob, mock_list_runs):
    """Test query with filters and JSON output."""
    # Arrange: Configure mocks same as above
    def glob_side_effect(pattern):
        if "run_new" in pattern: return ["/logs/run_new/rule-001_high_pass.log", "/logs/run_new/rule-002_med_fail.log"]
        if "run_old" in pattern: return ["/logs/run_old/rule-001_high_fail.log"]
        return []
    mock_glob.side_effect = glob_side_effect
    mock_parse_log.side_effect = lambda fp: MOCK_RULE_LOGS.get(fp, {})

    # Act: Query with filters (medium severity, status fail, keyword ssh)
    exit_code = query(
        logs_dir="/logs", run_id=None, last=None, since=None, until=None,
        severities=["medium"],
        status="fail",
        keywords=["ssh"],
        scope="title", # Search only in title
        output_json=True, # JSON output
        limit=None
    )

    # Assert
    assert exit_code == 0
    mock_list_runs.assert_called_once_with("/logs")
    assert mock_glob.call_count == len(MOCK_RUNS_LIST)
    # Parse log might be called fewer times if glob returns fewer files due to filters (depends on implementation, current impl filters after parsing)
    assert mock_parse_log.call_count == len(MOCK_RULE_LOGS)

    # Check print was called once (for the JSON dump)
    mock_print.assert_called_once()
    # Parse the JSON output and check content
    json_output_str = mock_print.call_args[0][0]
    try:
        json_data = json.loads(json_output_str)
    except json.JSONDecodeError:
        pytest.fail(f"Output was not valid JSON: {json_output_str}")

    # Only R-MED-FAIL from run_new should match all filters
    assert isinstance(json_data, list)
    assert len(json_data) == 1
    assert json_data[0]["run"] == "run_new"
    assert json_data[0]["id"] == "R-MED-FAIL"
    assert json_data[0]["severity"] == "medium"
    assert json_data[0]["status"] == "fail"
    assert json_data[0]["title"] == "Medium Fail SSH"

@patch('security_app.app.query._list_runs', return_value=MOCK_RUNS_LIST)
@patch('security_app.app.query.glob.glob')
@patch('security_app.app.query._parse_rule_log')
@patch('builtins.print')
def test_query_no_records_match(mock_print, mock_parse_log, mock_glob, mock_list_runs):
    """Test query when no records match the filters."""
    # Arrange Mocks
    def glob_side_effect(pattern):
        if "run_new" in pattern: return ["/logs/run_new/rule-001_high_pass.log", "/logs/run_new/rule-002_med_fail.log"]
        if "run_old" in pattern: return ["/logs/run_old/rule-001_high_fail.log"]
        return []
    mock_glob.side_effect = glob_side_effect
    mock_parse_log.side_effect = lambda fp: MOCK_RULE_LOGS.get(fp, {})

    # Act: Query with filters that won't match anything
    exit_code = query(
        logs_dir="/logs", run_id=None, last=None, since=None, until=None,
        severities=["critical"], # No critical rules in mock data
        output_json=False, limit=None
    )

    # Assert
    assert exit_code == 0
    # Check that the "No records matched" message was printed
    mock_print.assert_called_once_with("No records matched filters.")

@patch('security_app.app.query._list_runs', return_value=[]) # Simulate no runs found
@patch('builtins.print')
def test_query_no_runs_found(mock_print, mock_list_runs):
    """Test query when no runs are found in the logs directory."""
    # Act
    exit_code = query(logs_dir="/empty_logs", run_id=None, last=None, since=None, until=None,
                      severities=None, status=None, keywords=None, scope="any",
                      output_json=False, limit=None)
    # Assert
    assert exit_code == 0
    mock_list_runs.assert_called_once_with("/empty_logs")
    mock_print.assert_called_once_with("No runs matched.")

# --- Test query_main (argument parsing and calling query) ---

@patch('security_app.app.query.query') # Mock the core query function
@patch('argparse.ArgumentParser.parse_args')
def test_query_main(mock_parse_args, mock_query):
    """Test the main entrypoint function for argument parsing."""
    # Arrange: Simulate parsed arguments
    mock_args_obj = MagicMock()
    mock_args_obj.logs_dir = "test_dir"
    mock_args_obj.run = "specific_run"
    mock_args_obj.last = 5
    mock_args_obj.since = "2025-01-01"
    mock_args_obj.until = None
    mock_args_obj.severity = ["high", "critical"]
    mock_args_obj.status = "fail"
    mock_args_obj.query = ["keyword1", "keyword2"]
    mock_args_obj.scope = "check"
    mock_args_obj.json = True
    mock_args_obj.limit = 100
    mock_parse_args.return_value = mock_args_obj
    mock_query.return_value = 0 # Simulate successful query call

    # Act
    exit_code = query_main(["--run", "specific_run", "--last", "5", "--json", "--limit", "100"]) # Example argv

    # Assert
    mock_parse_args.assert_called_once() # Check parser was called
    # Check that the core query function was called with the correct arguments from parsed args
    mock_query.assert_called_once_with(
        logs_dir="test_dir",
        run_id="specific_run",
        last=5,
        since="2025-01-01",
        until=None,
        severities=["high", "critical"],
        status="fail",
        keywords=["keyword1", "keyword2"],
        scope="check",
        output_json=True,
        limit=100,
    )
    assert exit_code == 0
