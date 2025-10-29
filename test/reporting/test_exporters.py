# tests/reporting/test_exporters.py
import pytest
import json
import csv
from io import StringIO
from pathlib import Path
from unittest.mock import patch, mock_open

from security_app.reporting.exporters import (
    _summary_from_stats,
    _by_sev_from_stats,
    _top_from_stats,
    build_stats_json,
    dump_stats_json,
    write_stats_csv_bundle,
    _write_csv,
)
from security_app.models import Rule # Needed for stats structure

# --- Sample Stats Data (simplified output from compute_stats) ---

@pytest.fixture
def sample_stats_data():
    """Simplified stats structure matching output of compute_stats."""
    return {
        "totals": {
            "total_rules": 4, "rules_all_ok": 2, "rules_with_fail": 2,
            "pass_rate": 50.0, "total_cmds": 6, "total_ok": 3, "total_fail": 3,
        },
        "by_severity": {
            "high": {"rules": 1, "rules_fail": 1, "cmds": 2, "ok": 1, "fail": 1},
            "medium": {"rules": 2, "rules_fail": 1, "cmds": 3, "ok": 1, "fail": 2},
            "unknown": {"rules": 1, "rules_fail": 0, "cmds": 1, "ok": 1, "fail": 0},
        },
        "top_failing_rules": [
            (2, "R-MED-FAIL", "medium", 2, "Medium Fail Rule"),
            (0, "R-HIGH-FAIL", "high", 1, "High Fail Rule"),
        ],
        "all_results": [
            {"rule_index": 0, "rule": Rule(id="R-HIGH-FAIL", severity="high", title="High Fail Rule", check="",fix="",description=""), "num_ok": 1, "num_fail": 1},
            {"rule_index": 1, "rule": Rule(id="R-MED-OK", severity="medium", title="Medium OK Rule", check="",fix="",description=""), "num_ok": 1, "num_fail": 0},
            {"rule_index": 2, "rule": Rule(id="R-MED-FAIL", severity="medium", title="Medium Fail Rule", check="",fix="",description=""), "num_ok": 0, "num_fail": 2},
            {"rule_index": 3, "rule": Rule(id="R-UNK-OK", severity="unknown", title="Unknown OK Rule", check="",fix="",description=""), "num_ok": 1, "num_fail": 0},
        ]
    }

# --- Test Helper Functions ---

def test_summary_from_stats(sample_stats_data):
    summary = _summary_from_stats(sample_stats_data)
    assert summary["total_rules"] == 4
    assert summary["pass_rate"] == 50.0
    assert summary["commands_failed"] == 3

def test_by_sev_from_stats(sample_stats_data):
    by_sev = _by_sev_from_stats(sample_stats_data)
    assert "high" in by_sev and "medium" in by_sev and "unknown" in by_sev
    assert by_sev["high"]["rules"] == 1
    assert by_sev["high"]["rules_ok"] == 0 # 1 rule - 1 fail rule
    assert by_sev["high"]["cmd_ok"] == 1
    assert by_sev["high"]["cmd_fail"] == 1
    assert by_sev["medium"]["rules"] == 2
    assert by_sev["medium"]["rules_ok"] == 1 # 2 rules - 1 fail rule
    assert by_sev["medium"]["cmd_ok"] == 1
    assert by_sev["medium"]["cmd_fail"] == 2
    assert by_sev["unknown"]["rules"] == 1
    assert by_sev["unknown"]["rules_ok"] == 1 # 1 rule - 0 fail rules
    assert by_sev["unknown"]["cmd_ok"] == 1
    assert by_sev["unknown"]["cmd_fail"] == 0

def test_top_from_stats(sample_stats_data):
    top = _top_from_stats(sample_stats_data)
    assert len(top) == 2
    assert top[0]["id"] == "R-MED-FAIL"
    assert top[0]["severity"] == "medium"
    assert top[0]["cmd_fail"] == 2
    assert top[0]["status"] == "fail"
    assert top[1]["id"] == "R-HIGH-FAIL"
    assert top[1]["severity"] == "high"
    assert top[1]["cmd_fail"] == 1
    assert top[1]["status"] == "fail"

# --- Test Main Export Functions ---

def test_build_stats_json(sample_stats_data):
    """Test the structure of the combined JSON object."""
    data = build_stats_json(sample_stats_data)
    assert "summary" in data
    assert "by_severity" in data
    assert "top_failing_rules" in data
    assert "rules" in data
    assert len(data["rules"]) == 4
    assert data["rules"][0]["id"] == "R-HIGH-FAIL"
    assert data["rules"][0]["status"] == "fail"
    assert data["rules"][1]["id"] == "R-MED-OK"
    assert data["rules"][1]["status"] == "ok"

@patch("builtins.open", new_callable=mock_open)
@patch("os.makedirs")
def test_dump_stats_json_to_file(mock_makedirs, mock_file_open, sample_stats_data):
    """Test dumping JSON stats to a file."""
    filepath = "/fake/path/report.json"
    dump_stats_json(sample_stats_data, filepath)

    mock_makedirs.assert_called_once_with("/fake/path", exist_ok=True)
    mock_file_open.assert_called_once_with(filepath, "w", encoding="utf-8")
    # Get the handle mock used by 'open'
    handle = mock_file_open()
    # Check if write was called (content check is more complex, just check call)
    handle.write.assert_called()
    # Optionally check the written content roughly
    # written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    # import json
    # assert json.loads(written_content)["summary"]["total_rules"] == 4

@patch("sys.stdout", new_callable=StringIO)
def test_dump_stats_json_to_stdout(mock_stdout, sample_stats_data):
    """Test dumping JSON stats to stdout."""
    dump_stats_json(sample_stats_data, "-") # "-" indicates stdout
    output = mock_stdout.getvalue()
    assert '"total_rules": 4' in output # Check some key content
    assert '"id": "R-HIGH-FAIL"' in output

@patch("builtins.open", new_callable=mock_open)
@patch("os.makedirs")
@patch("csv.writer")
def test_write_csv(mock_csv_writer, mock_makedirs, mock_file_open):
    """Test the internal _write_csv function."""
    filepath = "/fake/path/data.csv"
    headers = ["col1", "col2"]
    rows = [["a", 1], ["b", 2]]

    # Mock the writer object returned by csv.writer
    mock_writer_instance = MagicMock()
    mock_csv_writer.return_value = mock_writer_instance

    _write_csv(filepath, headers, rows)

    mock_makedirs.assert_called_once_with("/fake/path", exist_ok=True)
    mock_file_open.assert_called_once_with(filepath, "w", encoding="utf-8", newline="")
    mock_csv_writer.assert_called_once() # Check if csv.writer was called
    # Check if writeheader and writerows were called on the writer instance
    mock_writer_instance.writerow.assert_called_once_with(headers)
    mock_writer_instance.writerow.assert_called_with(headers) # Check header row
    assert mock_writer_instance.writerow.call_count == 1 + len(rows) # Headers + data rows


@patch("security_app.reporting.exporters._write_csv")
@patch("os.makedirs")
def test_write_stats_csv_bundle(mock_makedirs, mock_write_csv, sample_stats_data):
    """Test that writing the CSV bundle calls _write_csv for each file."""
    out_dir = "/fake/out"
    write_stats_csv_bundle(sample_stats_data, out_dir)

    mock_makedirs.assert_called_once_with(out_dir, exist_ok=True)

    # Check that _write_csv was called 4 times (summary, by_sev, top, rules)
    assert mock_write_csv.call_count == 4

    # Optionally, check the arguments for one of the calls
    # Example: Check the call for summary.csv
    summary_call = next(call for call in mock_write_csv.call_args_list if "summary.csv" in call.args[0])
    assert summary_call.args[0] == os.path.join(out_dir, "summary.csv") # Path
    assert summary_call.args[1] == ["key", "value"] # Headers
    assert ["total_rules", 4] in summary_call.args[2] # Check some row data
