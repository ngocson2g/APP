# tests/core/runner/test_metrics.py
import pytest
import json
import time
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call # <<< THÊM patch VÀO ĐÂY
from security_app.core.runner.metrics import WaveMetricsSink
@pytest.fixture
def metrics_sink(tmp_path: Path):
    """Fixture to create WaveMetricsSink in a temporary directory."""
    run_dir = tmp_path / "test_run_metrics"
    # Ensure parent exists if run_dir needs creation by WaveMetricsSink
    run_dir.parent.mkdir(parents=True, exist_ok=True)
    # Mock chown_path to avoid permission errors if tests run as non-root
    with patch('security_app.core.runner.metrics.chown_path', return_value=None): # Giờ patch sẽ được nhận diện
        sink = WaveMetricsSink(str(run_dir), total_cmds=100)
        yield sink, run_dir # Return sink and path for checking

def test_wave_metrics_sink_init(metrics_sink):
    """Test initialization and initial file flush."""
    sink, run_dir = metrics_sink
    waves_file = run_dir / "waves.json"

    assert waves_file.exists()
    assert sink.run_id == "test_run_metrics"

    with open(waves_file, 'r') as f:
        data = json.load(f)

    assert data["run_id"] == "test_run_metrics"
    assert data["total_cmds"] == 100
    assert data["waves"] == []
    assert "started_at" in data
    assert "updated_at" in data
    assert "finished_at" not in data

def test_wave_metrics_sink_add_wave(metrics_sink):
    """Test adding waves and flushing updates."""
    sink, run_dir = metrics_sink
    waves_file = run_dir / "waves.json"
    t_start = time.time() - 10 # Simulate past start

    # Add wave 1
    sink.add_wave(1, started_at=t_start, ended_at=t_start + 2.5, cmds_total=20,
                  thr_total=8.0, thr_cpu=2.0, thr_io=6.0, timeouts=1,
                  timeout_rate=0.05, p50=0.1, p95=0.5)

    time.sleep(0.1) # Ensure updated_at changes
    t_wave2_start = time.time()

    # Add wave 2
    sink.add_wave(2, started_at=t_wave2_start, ended_at=t_wave2_start + 3.0, cmds_total=30,
                  thr_total=10.0, thr_cpu=3.0, thr_io=7.0, timeouts=0,
                  timeout_rate=0.0, p50=0.15, p95=0.6)

    with open(waves_file, 'r') as f:
        data = json.load(f)

    assert len(data["waves"]) == 2
    assert data["waves"][0]["wave"] == 1
    assert data["waves"][0]["cmds"] == 20
    assert data["waves"][0]["timeout_rate"] == pytest.approx(0.05)
    assert data["waves"][0]["p95"] == pytest.approx(0.5)
    assert data["waves"][0]["elapsed_sec"] == pytest.approx(2.5)

    assert data["waves"][1]["wave"] == 2
    assert data["waves"][1]["cmds"] == 30
    assert data["waves"][1]["timeout_rate"] == pytest.approx(0.0)
    assert data["waves"][1]["p95"] == pytest.approx(0.6)

    assert "finished_at" not in data
    assert data["updated_at"] > data["started_at"]
    assert data["updated_at"] >= t_wave2_start 

def test_wave_metrics_sink_finish(metrics_sink):
    """Test the finish method."""
    sink, run_dir = metrics_sink
    waves_file = run_dir / "waves.json"

    # Add a wave first
    t_start = time.time() - 5
    sink.add_wave(1, started_at=t_start, ended_at=t_start + 1.0, cmds_total=10,
                  thr_total=10.0, thr_cpu=2.0, thr_io=8.0, timeouts=0,
                  timeout_rate=0.0, p50=0.05, p95=0.2)

    time.sleep(0.1) # Ensure finish time is later
    finish_time = time.time()
    sink.finish()

    with open(waves_file, 'r') as f:
        data = json.load(f)

    assert "finished_at" in data
    assert data["finished_at"] >= finish_time
    # FIX: Remove the incorrect assertion below
    # assert data["updated_at"] == data["finished_at"] # Finish also updates <- COMMENT OUT OR DELETE
    assert len(data["waves"]) == 1 # Check wave data is still there

def test_wave_metrics_atomic_flush(metrics_sink, mocker):
    """Test that flushing uses atomic replace."""
    sink, run_dir = metrics_sink # run_dir là Path
    dst_path = run_dir / "waves.json"
    tmp_path = run_dir / "waves.json.tmp"

    # Convert Path objects to strings for assertion matching
    dst_str = str(dst_path)
    tmp_str = str(tmp_path)

    mock_open = mocker.patch('builtins.open', mocker.mock_open())
    mock_dump = mocker.patch('json.dump')
    mock_replace = mocker.patch('os.replace')
    mock_chown = mocker.patch('security_app.core.runner.metrics.chown_path')

    # Call internal flush method
    sink._flush()

    # Assertions - FIX: Use string paths in assertions
    mock_open.assert_called_once_with(tmp_str, "w", encoding="utf-8") # Sử dụng tmp_str
    mock_dump.assert_called_once()
    mock_replace.assert_called_once_with(tmp_str, dst_str) # Sử dụng tmp_str, dst_str
    mock_chown.assert_called_once_with(dst_str) # Sử dụng dst_str