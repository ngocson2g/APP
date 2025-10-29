# tests/maintenance/test_cleanup.py
import pytest
import os
import shutil
import tarfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, call # Import call for checking mock calls
from security_app.maintenance.cleanup import (
    _human,
    _is_run_dir,
    _sorted_by_mtime_desc,
    _folder_size,
    prune_runs,
    prune_tmp,
    prune_reports,
    run_cleanup
)

# --- Test _human (Keep existing test) ---
@pytest.mark.parametrize("bytes_in, expected_str", [
    (100, "100.0 B"), (1024, "1.0 KB"), (1536, "1.5 KB"),
    (1024 * 1024, "1.0 MB"), (1024 * 1024 * 5.2, "5.2 MB"),
    (1024**3 * 2, "2.0 GB"), (1024**4 * 1.1, "1.1 TB"),
    (0, "0.0 B"), (-100, "-100.0 B"),
])
def test_human_readable_size(bytes_in, expected_str):
    assert _human(bytes_in) == expected_str

# --- Test Helper Functions ---

def test_is_run_dir(tmp_path: Path):
    """Tests the directory check helper."""
    dir_path = tmp_path / "a_dir"
    file_path = tmp_path / "a_file.txt"
    non_existent = tmp_path / "non_existent"

    dir_path.mkdir()
    file_path.touch()

    assert _is_run_dir(dir_path) is True
    assert _is_run_dir(file_path) is False
    assert _is_run_dir(non_existent) is False # Should handle FileNotFoundError

def test_sorted_by_mtime_desc(tmp_path: Path):
    """Tests sorting paths by modification time descending."""
    p1 = tmp_path / "file1"
    p2 = tmp_path / "file2"
    p3 = tmp_path / "file3"
    non_existent = tmp_path / "non_existent" # Test handling missing file

    now = time.time()
    p1.touch()
    time.sleep(0.01) # Ensure time difference
    p3.touch()
    time.sleep(0.01)
    p2.touch()

    # Manually set mtimes for clarity if needed
    os.utime(p1, (now - 20, now - 20)) # Oldest
    os.utime(p3, (now - 10, now - 10)) # Middle
    os.utime(p2, (now, now))           # Newest

    paths = [p1, p2, p3, non_existent]
    sorted_paths = _sorted_by_mtime_desc(paths)

    # Expected order: p2 (newest), p3, p1 (oldest), non_existent (mtime 0)
    # Check if non_existent is last (mtime 0)
    assert sorted_paths == [p2, p3, p1, non_existent]

def test_folder_size(tmp_path: Path):
    """Tests folder size calculation."""
    dir1 = tmp_path / "dir1"
    dir1.mkdir()
    file1 = dir1 / "file1.bin"
    file2 = dir1 / "file2.txt"
    subdir = dir1 / "subdir"
    subdir.mkdir()
    file3 = subdir / "file3.dat"

    # Write known sizes
    file1.write_bytes(b'a' * 1024) # 1 KB
    file2.write_text("hello" * 200) # 1000 bytes
    file3.write_bytes(b'c' * 512)   # 0.5 KB

    expected_size = 1024 + 1000 + 512
    assert _folder_size(dir1) == expected_size

    # Test on empty dir
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert _folder_size(empty_dir) == 0

    # Test on non-existent dir (should not error, return 0)
    assert _folder_size(tmp_path / "no_such_dir") == 0

# --- Test Pruning Functions ---

@pytest.fixture
def setup_tmp_dirs(tmp_path: Path):
    """Creates a structure of temp files/dirs for prune_tmp."""
    now = time.time()
    prefix = "security_app_"
    # Files/Dirs to keep (newer than 12 hours)
    (tmp_path / f"{prefix}recent_file.log").touch()
    (tmp_path / f"{prefix}recent_dir").mkdir()
    (tmp_path / f"{prefix}recent_dir" / "inner.txt").touch()

    # Files/Dirs to prune (older than 12 hours)
    old_time = now - timedelta(hours=13).total_seconds()
    old_file = tmp_path / f"{prefix}old_file.tmp"
    old_dir = tmp_path / f"{prefix}old_dir"
    old_file.touch()
    old_dir.mkdir()
    (old_dir / "old_inner.txt").touch()
    os.utime(old_file, (old_time, old_time))
    os.utime(old_dir, (old_time, old_time)) # Set dir time too
    os.utime(old_dir / "old_inner.txt", (old_time, old_time))

    # File with different prefix
    (tmp_path / "other_prefix.log").touch()

    return tmp_path, prefix, old_file, old_dir

def test_prune_tmp_dry_run(setup_tmp_dirs):
    """Test prune_tmp in dry-run mode."""
    tmp_path, prefix, old_file, old_dir = setup_tmp_dirs
    report = prune_tmp(tmp_dir=tmp_path, prefix=prefix, older_than_hours=12, dry_run=True)

    assert len(report["tmp_removed"]) == 2
    assert f"DRY-RUN {old_file}" in report["tmp_removed"]
    assert f"DRY-RUN {old_dir}" in report["tmp_removed"]
    # Check that files/dirs were NOT actually deleted
    assert old_file.exists()
    assert old_dir.exists()
    assert (tmp_path / f"{prefix}recent_file.log").exists()
    assert (tmp_path / "other_prefix.log").exists()

def test_prune_tmp_actual_run(setup_tmp_dirs):
    """Test prune_tmp actually deleting old items."""
    tmp_path, prefix, old_file, old_dir = setup_tmp_dirs
    report = prune_tmp(tmp_dir=tmp_path, prefix=prefix, older_than_hours=12, dry_run=False)

    assert len(report["tmp_removed"]) == 2
    assert str(old_file) in report["tmp_removed"]
    assert str(old_dir) in report["tmp_removed"]
    # Check that files/dirs WERE deleted
    assert not old_file.exists()
    assert not old_dir.exists()
    # Check others remain
    assert (tmp_path / f"{prefix}recent_file.log").exists()
    assert (tmp_path / "other_prefix.log").exists()

@pytest.fixture
def setup_run_dirs(tmp_path: Path):
    """Creates a structure of run dirs for prune_runs."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    base_time = time.time()
    run_times = {
        "run_5_oldest": base_time - timedelta(days=5).total_seconds(),
        "run_4_old": base_time - timedelta(days=4).total_seconds(),
        "run_3_compress": base_time - timedelta(days=3).total_seconds(),
        "run_2_keep": base_time - timedelta(days=2).total_seconds(),
        "run_1_keep": base_time - timedelta(days=1).total_seconds(),
        "run_0_keep": base_time, # Newest
    }
    for name, mtime in run_times.items():
        p = logs_dir / name
        p.mkdir()
        (p / "rule-001.log").touch()
        os.utime(p, (mtime, mtime))
    # Add a compressed file that should be ignored by compression logic
    (logs_dir / "run_6_already_compressed.tar.gz").touch()
    os.utime(logs_dir / "run_6_already_compressed.tar.gz", (base_time - timedelta(days=6).total_seconds(),)*2)

    return logs_dir

def test_prune_runs_keep_latest(setup_run_dirs):
    """Test prune_runs based on keep_latest count."""
    logs_dir = setup_run_dirs
    report = prune_runs(logs_dir, keep_latest=3, dry_run=True) # Keep 3 newest

    assert len(report["deleted"]) == 3 # run_3_compress, run_4_old, run_5_oldest
    assert any("run_3_compress" in item for item in report["deleted"])
    assert any("run_4_old" in item for item in report["deleted"])
    assert any("run_5_oldest" in item for item in report["deleted"])
    assert len(report["kept"]) == 3
    assert str(logs_dir / "run_0_keep") in report["kept"]
    assert str(logs_dir / "run_1_keep") in report["kept"]
    assert str(logs_dir / "run_2_keep") in report["kept"]
    assert report["compressed"] == [] # No compression triggered

def test_prune_runs_older_than(setup_run_dirs):
    """Test prune_runs based on age."""
    logs_dir = setup_run_dirs
    report = prune_runs(logs_dir, keep_latest=10, older_than_days=3.5, dry_run=True) # Delete older than 3.5 days

    assert len(report["deleted"]) == 2 # run_4_old, run_5_oldest
    assert any("run_4_old" in item for item in report["deleted"])
    assert any("run_5_oldest" in item for item in report["deleted"])
    assert len(report["kept"]) == 6 # All originally created dirs
    assert report["compressed"] == []

# Mock tarfile for compression tests
@patch('tarfile.open')
def test_prune_runs_compress(mock_tar_open, setup_run_dirs):
    """Test prune_runs compression logic."""
    logs_dir = setup_run_dirs
    # Mock the tarfile context manager
    mock_tf = MagicMock()
    mock_tar_open.return_value.__enter__.return_value = mock_tf

    report = prune_runs(logs_dir, keep_latest=10, compress_older_days=2.5, dry_run=False) # Compress older than 2.5 days

    assert len(report["deleted"]) == 0 # No deletion triggered
    # Should compress run_3, run_4, run_5
    assert len(report["compressed"]) == 3
    assert any("run_3_compress -> run_3_compress.tar.gz" in item for item in report["compressed"])
    assert any("run_4_old -> run_4_old.tar.gz" in item for item in report["compressed"])
    assert any("run_5_oldest -> run_5_oldest.tar.gz" in item for item in report["compressed"])

    # Check tarfile.open calls
    assert mock_tar_open.call_count == 3
    expected_arc_paths = [
        str(logs_dir / "run_3_compress.tar.gz"),
        str(logs_dir / "run_4_old.tar.gz"),
        str(logs_dir / "run_5_oldest.tar.gz"),
    ]
    # Check add calls on the mock tarfile instance
    assert mock_tf.add.call_count == 3
    expected_add_calls = [
        call(logs_dir / "run_3_compress", arcname="run_3_compress", recursive=True),
        call(logs_dir / "run_4_old", arcname="run_4_old", recursive=True),
        call(logs_dir / "run_5_oldest", arcname="run_5_oldest", recursive=True),
    ]
    mock_tf.add.assert_has_calls(expected_add_calls, any_order=True)

@pytest.fixture
def setup_report_dirs(tmp_path: Path):
    """Creates a structure of report dirs for prune_reports."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    base_time = time.time()
    report_times = {
        "rep_3_old": base_time - timedelta(days=40).total_seconds(),
        "rep_2_keep": base_time - timedelta(days=20).total_seconds(),
        "rep_1_keep": base_time - timedelta(days=10).total_seconds(),
        "rep_0_keep": base_time, # Newest
    }
    for name, mtime in report_times.items():
        p = report_dir / name
        p.mkdir()
        (p / "report.pdf").touch()
        os.utime(p, (mtime, mtime))
    # Create a potentially broken symlink
    latest_link = report_dir / "latest"
    latest_link.symlink_to("rep_old_nonexistent")
    return report_dir

def test_prune_reports_delete_and_fix_link(setup_report_dirs):
    """Test deleting old reports and fixing the 'latest' symlink."""
    report_dir = setup_report_dirs
    report = prune_reports(report_dir, keep_days=25, dry_run=False) # Keep reports newer than 25 days

    assert len(report["reports_deleted"]) == 1 # rep_3_old
    assert "rep_3_old" in report["reports_deleted"]
    assert not (report_dir / "rep_3_old").exists()
    assert (report_dir / "rep_2_keep").exists()
    assert (report_dir / "rep_1_keep").exists()
    assert (report_dir / "rep_0_keep").exists()

    # Check symlink was updated to the newest remaining directory
    latest_link = report_dir / "latest"
    assert latest_link.is_symlink()
    assert latest_link.readlink().name == "rep_0_keep"
    assert report["latest"] == "rep_0_keep"

def test_prune_reports_dry_run(setup_report_dirs):
    """Test prune_reports in dry-run mode."""
    report_dir = setup_report_dirs
    report = prune_reports(report_dir, keep_days=25, dry_run=True)

    assert len(report["reports_deleted"]) == 1
    assert "DRY-RUN rep_3_old" in report["reports_deleted"]
    # Check dir still exists
    assert (report_dir / "rep_3_old").exists()
    # Check link was not updated (though report['latest'] might show what it *would* be)
    latest_link = report_dir / "latest"
    assert latest_link.readlink().name == "rep_old_nonexistent"


# --- Test run_cleanup Orchestrator ---

@patch('security_app.maintenance.cleanup.prune_runs')
@patch('security_app.maintenance.cleanup.prune_reports')
@patch('security_app.maintenance.cleanup.prune_tmp')
def test_run_cleanup(mock_prune_tmp, mock_prune_reports, mock_prune_runs):
    """Test that run_cleanup calls the individual prune functions correctly."""
    logs_path = Path("/path/to/logs")
    reports_path = Path("/path/to/reports")

    # Configure mocks to return simple dicts
    mock_prune_runs.return_value = {"runs_report": True}
    mock_prune_reports.return_value = {"reports_report": True}
    mock_prune_tmp.return_value = {"tmp_report": True}

    result = run_cleanup(
        logs_dir=logs_path,
        report_dir=reports_path,
        keep_runs=20,
        runs_older_than_days=60,
        compress_runs_older_than_days=90,
        keep_reports_days=45,
        tmp_prefix="test_",
        tmp_older_than_hours=6,
        dry_run=False
    )

    # Check calls
    mock_prune_runs.assert_called_once_with(
        logs_dir=logs_path, keep_latest=20, older_than_days=60,
        compress_older_days=90, dry_run=False
    )
    mock_prune_reports.assert_called_once_with(
        report_root=reports_path, keep_days=45, dry_run=False
    )
    mock_prune_tmp.assert_called_once_with(
        prefix="test_", older_than_hours=6, dry_run=False
        # Note: tmp_dir uses default Path('/tmp') here, check if needed
    )

    # Check result structure
    assert result == {
        "runs": {"runs_report": True},
        "reports": {"reports_report": True},
        "tmp": {"tmp_report": True},
    }

@patch('security_app.maintenance.cleanup.prune_runs')
@patch('security_app.maintenance.cleanup.prune_reports') # Keep this mock
@patch('security_app.maintenance.cleanup.prune_tmp')
def test_run_cleanup_no_report_dir(mock_prune_tmp, mock_prune_reports, mock_prune_runs):
    """Test run_cleanup when report_dir is None."""
    logs_path = Path("/path/to/logs")
    run_cleanup(logs_dir=logs_path, report_dir=None, dry_run=True)

    mock_prune_runs.assert_called_once()
    mock_prune_tmp.assert_called_once()
    mock_prune_reports.assert_not_called() # Should not be called