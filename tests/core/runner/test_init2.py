# tests/core/runner/test_init.py
import pytest
import time
import statistics # Needed for checking p95 calc if not mocked deeply
from concurrent.futures import Future, TimeoutError # Import TimeoutError
from unittest.mock import patch, MagicMock, call, ANY
from security_app.models import Rule, Settings, CmdResult
# FIX: Import _mk_denied from its location
from security_app.core.runner.scheduler import _mk_denied
from security_app.core.runner import (
    run_all_rules,
    _is_cpuish_cmd, # Keep tests for helpers if desired
    _classify_chunk,
    _count_timeouts,
    _workers_chunk,
    # Import AIMD constants for checking calculations
    AIMD_TIMEOUT_RATE, AIMD_P95_SPIKE, AIMD_BETA, AIMD_ADD,
    WAVE_SCALE_MIN, WAVE_SCALE_MAX
)
from security_app.core.logger import RunLogger
from security_app.core.runner.metrics import WaveMetricsSink

# --- Fixtures (Keep all existing fixtures) ---
@pytest.fixture
def sample_rules():
    """Provides a list of sample Rule objects for testing."""
    return [
        Rule(id="R1-IO", description="", check="$ io_cmd_1\n$ io_cmd_2", fix="", severity="low"),
        Rule(id="R2-CPU", description="", check="$ cpu_cmd_1", fix="", severity="high"),
        Rule(id="R3-MIX", description="", check="$ io_cmd_3\n$ cpu_cmd_2", fix="", severity="medium"),
        Rule(id="R4-DENY", description="", check="$ rm -rf /", fix="", severity="critical"), # Will be denied
    ]

@pytest.fixture
def default_settings():
    """Provides default Settings object."""
    # Use a mutable copy if tests modify settings
    return Settings(
        shell_timeout=10.0, retry_attempts=0, retry_delay_sec=0.0,
        retry_on_timeout=False, exec_cwd="/", clean_env=True
    )

@pytest.fixture
def mock_scheduler():
    with patch('security_app.core.runner.build_scheduled_tasks') as mock_build, \
         patch('security_app.core.runner.suggest_wave_size') as mock_suggest:
        yield mock_build, mock_suggest

@pytest.fixture
def mock_tuner():
    with patch('security_app.core.runner.auto_guess_workers') as mock_guess:
        yield mock_guess

@pytest.fixture
def mock_logger():
    with patch('security_app.core.runner.RunLogger', spec=RunLogger) as MockLogger:
        mock_instance = MockLogger.return_value
        mock_instance.run_dir = "/fake/logs/run_test"
        yield mock_instance

@pytest.fixture
def mock_sink():
    with patch('security_app.core.runner.WaveMetricsSink', spec=WaveMetricsSink) as MockSink:
        mock_instance = MockSink.return_value
        yield mock_instance

@pytest.fixture
def mock_executors():
    with patch('security_app.core.runner.ProcessPoolExecutor') as MockProcessPool, \
         patch('security_app.core.runner.ThreadPoolExecutor') as MockThreadPool, \
         patch('security_app.core.runner.as_completed') as mock_as_completed:
        mock_proc_executor = MockProcessPool.return_value.__enter__.return_value
        mock_thread_executor = MockThreadPool.return_value.__enter__.return_value
        mock_proc_executor.submit.side_effect = lambda fn, args: Future()
        mock_thread_executor.submit.side_effect = lambda fn, args: Future()
        yield mock_proc_executor, mock_thread_executor, mock_as_completed

@pytest.fixture
def mock_worker_chunk():
     # Mock the function itself, not just its import if it's called locally
     # The previous fixture might be targeting the wrong place if _workers_chunk
     # is called directly within __init__.py's namespace.
     # Let's try patching it within the runner's namespace.
    with patch('security_app.core.runner._workers_chunk') as mock_chunk:
        yield mock_chunk

@pytest.fixture
def mock_helpers():
    with patch('security_app.core.runner.os.makedirs') as mock_makedirs, \
         patch('security_app.core.runner._merge_and_log') as mock_merge, \
         patch('security_app.core.runner._bar') as mock_bar, \
         patch('builtins.print') as mock_print, \
         patch('time.time', side_effect=[1000.0, 1001.0, 1002.0, 1003.0, 1004.0]) as mock_time: # Provide multiple time values
        mock_bar.return_value = "[####......]"
        yield mock_makedirs, mock_merge, mock_bar, mock_print, mock_time

@pytest.fixture
def mock_classify():
     with patch('security_app.core.runner._classify_chunk') as mock_classify_fn:
         mock_classify_fn.side_effect = lambda chunk: "cpu" if any("cpu" in cmd for cmd in chunk) else "io"
         yield mock_classify_fn

# --- Test Cases ---

# Keep the basic flow test
def test_run_all_rules_basic_flow(
    sample_rules, default_settings, mock_scheduler, mock_tuner, mock_logger, mock_sink,
    mock_executors, mock_worker_chunk, mock_helpers, mock_classify):
    """Test the basic execution flow with mocked components."""
    # (Code from previous example, should pass now)
    mock_build, mock_suggest = mock_scheduler
    mock_guess = mock_tuner
    mock_proc_executor, mock_thread_executor, mock_as_completed = mock_executors
    mock_makedirs, mock_merge, mock_bar, mock_print, mock_time = mock_helpers
    rule1, rule2, rule3, rule4 = sample_rules
    tasks_list = [
        (0, rule1, ["io_cmd_1", "io_cmd_2"], 0.2), (1, rule2, ["cpu_cmd_1"], 1.5),
        (2, rule3, ["io_cmd_3"], 0.1), (2, rule3, ["cpu_cmd_2"], 1.2),
    ]
    tasks_sorted = sorted(tasks_list, key=lambda t: t[3], reverse=True)
    agg_data = {
        0: {"rule": rule1, "denied": [], "ran": []}, 1: {"rule": rule2, "denied": [], "ran": []},
        2: {"rule": rule3, "denied": [], "ran": []},
        3: {"rule": rule4, "denied": [_mk_denied("rm -rf /", "DENIED")], "ran": []},
    }
    pending_data = {0: 1, 1: 1, 2: 2, 3: 0}
    mock_build.return_value = (tasks_sorted, agg_data, pending_data)
    mock_suggest.return_value = 2 # Simulate wave size 2
    mock_guess.side_effect = lambda n, proc, sample: 2 if proc else 4 # Suggest 2 CPU, 4 IO
    futures_map = {}
    submitted_futures = []
    for task_idx, (idx, rule, chunk, est) in enumerate(tasks_sorted):
        f = Future()
        result_payload = (idx, [CmdResult(cmd=c, returncode=0, stdout="ok", stderr="", duration_sec=est / len(chunk), ok=True) for c in chunk])
        f.set_result(result_payload)
        futures_map[f] = ("cpu" if mock_classify(chunk) == "cpu" else "io", idx, len(chunk))
        submitted_futures.append(f)
    # Make as_completed yield futures wave by wave
    mock_as_completed.side_effect = [submitted_futures[0:2], submitted_futures[2:4]]

    results = run_all_rules(sample_rules, log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # (Assertions from previous example)
    mock_makedirs.assert_called_once_with("/fake/logs", exist_ok=True)
    mock_logger.assert_called_once_with(base_dir="/fake/logs")
    mock_sink.assert_called_once_with(run_dir="/fake/logs/run_test", total_cmds=ANY)
    mock_build.assert_called_once_with(sample_rules, logs_base_dir="/fake/logs")
    mock_merge.assert_any_call(3, rule4, agg_data[3]["denied"], [], mock_logger)
    assert mock_guess.call_count == 2
    assert mock_suggest.call_count >= 1
    assert mock_proc_executor.submit.call_count + mock_thread_executor.submit.call_count == len(tasks_sorted)
    mock_proc_executor.submit.assert_any_call(_workers_chunk, (1, rule2, ["cpu_cmd_1"], default_settings, ANY))
    mock_thread_executor.submit.assert_any_call(_workers_chunk, (0, rule1, ["io_cmd_1", "io_cmd_2"], default_settings, ANY))
    assert mock_as_completed.call_count == 2 # 2 waves
    assert mock_merge.call_count == 1 + len(tasks_sorted)
    assert mock_sink.add_wave.call_count == 2
    assert mock_print.call_count >= 2
    assert mock_bar.call_count >= 2
    assert len(results) == len(sample_rules)
    assert "rule_index" in results[0]
    assert isinstance(results[0]["rule"], Rule)
    mock_sink.finish.assert_called_once()

# --- NEW TESTS ---

def test_run_all_rules_worker_override(
    sample_rules, default_settings, mock_scheduler, mock_tuner, mock_logger, mock_sink,
    mock_executors, mock_helpers, mock_classify):
    """Test providing explicit --workers caps the guessed workers."""
    mock_build, mock_suggest = mock_scheduler
    mock_guess = mock_tuner
    mock_proc_executor, mock_thread_executor, mock_as_completed = mock_executors
    mock_makedirs, mock_merge, mock_bar, mock_print, mock_time = mock_helpers

    # Arrange: Simulate only one task, suggest high worker counts
    task = (0, sample_rules[0], ["io_cmd_1"], 0.1)
    mock_build.return_value = ([task], {0: {"rule": sample_rules[0], "denied":[], "ran":[]}}, {0: 1})
    mock_suggest.return_value = 1
    mock_guess.side_effect = lambda n, proc, sample: 8 # Suggest 8 workers
    # Simulate as_completed yielding one result
    f = Future()
    f.set_result((0, [CmdResult(cmd="io_cmd_1", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True)]))
    mock_as_completed.return_value = [f]

    # Act: Call with explicit workers=3
    run_all_rules(sample_rules, log_base_dir="/fake/logs", workers=3, settings=default_settings)

    # Assert: Check that guess was capped by explicit workers arg
    mock_guess.assert_called() # Called for CPU and IO
    # Check max_workers passed to Executors was capped at 3
    # Check ThreadPool call (since task is IO)
    mock_thread_executor_args = mock_executors[1].call_args # ThreadPoolExecutor constructor args
    assert mock_thread_executor_args is not None
    assert mock_thread_executor_args.kwargs.get('max_workers') == 3 # Capped IO guess
    # Check ProcessPool call (it might still be called even if no CPU tasks in wave)
    mock_proc_executor_args = mock_executors[0].call_args # ProcessPoolExecutor constructor args
    assert mock_proc_executor_args is not None
    assert mock_proc_executor_args.kwargs.get('max_workers') == 3 # Capped CPU guess


def test_run_all_rules_aimd_decrease(
    sample_rules, default_settings, mock_scheduler, mock_tuner, mock_logger, mock_sink,
    mock_executors, mock_helpers, mock_classify):
    """Test AIMD decreases caps on congestion (high timeout rate)."""
    mock_build, mock_suggest = mock_scheduler
    mock_guess = mock_tuner
    mock_proc_executor, mock_thread_executor, mock_as_completed = mock_executors
    mock_makedirs, mock_merge, mock_bar, mock_print, mock_time = mock_helpers

    # Arrange: 2 waves, 1 task each. First wave simulates high timeout.
    task1 = (0, sample_rules[0], ["io_cmd_1"], 0.1)
    task2 = (1, sample_rules[1], ["cpu_cmd_1"], 1.0) # Assume cpu_cmd_1 is CPU
    # Build returns both tasks initially
    mock_build.return_value = ([task1, task2], {0:{}, 1:{}}, {0:1, 1:1})
    mock_suggest.side_effect = [1, 1] # Wave size 1 for both waves
    mock_guess.side_effect = [2, 4] # Initial guess: 2 CPU, 4 IO

    # Simulate wave 1 (task1 - IO) results with high timeout
    f1 = Future()
    # Simulate result with timeout (returncode=None, stderr contains TIMEOUT)
    wave1_result_payload = (0, [CmdResult(cmd="io_cmd_1", returncode=None, stdout="", stderr="TIMEOUT", duration_sec=0.1, ok=False)])
    f1.set_result(wave1_result_payload)

    # Simulate wave 2 (task2 - CPU) results (normal)
    f2 = Future()
    wave2_result_payload = (1, [CmdResult(cmd="cpu_cmd_1", returncode=0, stdout="ok", stderr="", duration_sec=1.0, ok=True)])
    f2.set_result(wave2_result_payload)

    # as_completed yields futures one wave at a time
    mock_as_completed.side_effect = [[f1], [f2]]

    # Act
    run_all_rules(sample_rules[:2], log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # Assert AIMD decrease after wave 1
    # Check add_wave call for wave 1
    wave1_metrics_call = mock_sink.add_wave.call_args_list[0].kwargs
    assert wave1_metrics_call['wave_no'] == 1
    assert wave1_metrics_call['timeouts'] == 1
    assert wave1_metrics_call['timeout_rate'] == pytest.approx(1.0) # 1 timeout / 1 cmd

    # Check Executors call for wave 2 - should use reduced caps
    # Initial caps: cpu=2, io=4. After wave 1 timeout: cpu=max(1, 2*0.7)=1, io=max(1, 4*0.7)=2
    # Wave 2 has 1 CPU task. ProcessPool should be created with max_workers=1
    # Wave 2 has 0 IO tasks. ThreadPool created with max_workers=1 (default min)
    proc_pool_call_wave2 = mock_executors[0].call_args_list[1] # Second call to ProcessPoolExecutor
    thread_pool_call_wave2 = mock_executors[1].call_args_list[1] # Second call to ThreadPoolExecutor
    assert proc_pool_call_wave2.kwargs.get('max_workers') == 1 # Decreased from 2
    assert thread_pool_call_wave2.kwargs.get('max_workers') == 1 # Min workers as no IO tasks

    # Check wave_scale was also reduced
    wave2_print_call = next(c for c in mock_print.call_args_list if "[wave 2]" in c.args[0])
    assert f"ws×={AIMD_BETA:.2f}" in wave2_print_call.args[0] # Check printed wave scale


def test_run_all_rules_aimd_increase(
    sample_rules, default_settings, mock_scheduler, mock_tuner, mock_logger, mock_sink,
    mock_executors, mock_helpers, mock_classify):
    """Test AIMD increases caps on stable performance."""
    mock_build, mock_suggest = mock_scheduler
    mock_guess = mock_tuner
    mock_proc_executor, mock_thread_executor, mock_as_completed = mock_executors
    mock_makedirs, mock_merge, mock_bar, mock_print, mock_time = mock_helpers

    # Arrange: 2 waves, 1 task each. Both waves stable (no timeout, low p95).
    task1 = (0, sample_rules[0], ["io_cmd_1"], 0.1)
    task2 = (1, sample_rules[1], ["cpu_cmd_1"], 1.0)
    mock_build.return_value = ([task1, task2], {0:{}, 1:{}}, {0:1, 1:1})
    mock_suggest.side_effect = [1, 1]
    mock_guess.side_effect = [2, 4] # Initial guess: 2 CPU, 4 IO

    # Simulate wave 1 (task1 - IO) results stable
    f1 = Future()
    wave1_result_payload = (0, [CmdResult(cmd="io_cmd_1", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True)])
    f1.set_result(wave1_result_payload)

    # Simulate wave 2 (task2 - CPU) results stable
    f2 = Future()
    wave2_result_payload = (1, [CmdResult(cmd="cpu_cmd_1", returncode=0, stdout="ok", stderr="", duration_sec=1.0, ok=True)])
    f2.set_result(wave2_result_payload)

    mock_as_completed.side_effect = [[f1], [f2]]

    # Act
    run_all_rules(sample_rules[:2], log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # Assert AIMD increase after wave 1
    # Check add_wave call for wave 1
    wave1_metrics_call = mock_sink.add_wave.call_args_list[0].kwargs
    assert wave1_metrics_call['timeout_rate'] == 0.0
    assert wave1_metrics_call['p95'] == pytest.approx(0.1) # Assuming p95=duration for single item

    # Check Executors call for wave 2 - should use increased caps
    # Initial caps: cpu=2, io=4. After wave 1 stable: cpu=min(2, 2+1)=2, io=min(4, 4+1)=4 (no change as already at max initial guess)
    # Let's adjust initial guess to see increase: mock_guess.side_effect = [1, 3] -> cpu=min(1, 1+1)=1, io=min(3, 3+1)=3
    # Rerun with adjusted guess:
    mock_guess.side_effect = [1, 3] # Adjusted initial guess
    run_all_rules(sample_rules[:2], log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # Check again with adjusted initial guess
    proc_pool_call_wave2 = mock_executors[0].call_args_list[1]
    thread_pool_call_wave2 = mock_executors[1].call_args_list[1]
    # Check if max_workers increased (up to initial guess max)
    assert proc_pool_call_wave2.kwargs.get('max_workers') == 1 # Increased to 1 (max was 1)
    assert thread_pool_call_wave2.kwargs.get('max_workers') == 3 # Increased to 3 (max was 3)

    # Check wave_scale also increased
    wave2_print_call = next(c for c in mock_print.call_args_list if "[wave 2]" in c.args[0])
    assert f"ws×={1.0 + 0.10:.2f}" in wave2_print_call.args[0] # Check printed wave scale increased


def test_run_all_rules_dynamic_timeout_update(
    sample_rules, default_settings, mock_scheduler, mock_tuner, mock_logger, mock_sink,
    mock_executors, mock_helpers, mock_classify):
    """Test that settings.shell_timeout is updated based on wave p95."""
    mock_build, mock_suggest = mock_scheduler
    mock_guess = mock_tuner
    mock_proc_executor, mock_thread_executor, mock_as_completed = mock_executors
    mock_makedirs, mock_merge, mock_bar, mock_print, mock_time = mock_helpers

    # Arrange: 2 waves, check timeout used for wave 2 submission
    task1 = (0, sample_rules[0], ["io_cmd_1"], 0.1) # p95=0.1 -> next timeout = 5.0
    task2 = (1, sample_rules[1], ["cpu_cmd_1"], 3.0) # p95=3.0 -> next timeout = 10.0
    mock_build.return_value = ([task1, task2], {0:{}, 1:{}}, {0:1, 1:1})
    mock_suggest.side_effect = [1, 1]
    mock_guess.side_effect = [1, 1]

    # Simulate wave 1 results, p95=0.1
    f1 = Future()
    wave1_result_payload = (0, [CmdResult(cmd="io_cmd_1", returncode=0, stdout="ok", stderr="", duration_sec=0.1, ok=True)])
    f1.set_result(wave1_result_payload)

    # Simulate wave 2 results, p95=3.0
    f2 = Future()
    wave2_result_payload = (1, [CmdResult(cmd="cpu_cmd_1", returncode=0, stdout="ok", stderr="", duration_sec=3.0, ok=True)])
    f2.set_result(wave2_result_payload)

    mock_as_completed.side_effect = [[f1], [f2]]

    # Act
    run_all_rules(sample_rules[:2], log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # Assert: Check timeout used in wave 2 submission
    # _workers_chunk receives the updated settings object
    # Check the settings passed to the second submit call (task2 - CPU)
    submit_call_wave2 = mock_proc_executor.submit.call_args_list[0] # First (and only) call to process pool submit
    payload_wave2 = submit_call_wave2.args[1] # The payload tuple
    settings_wave2 = payload_wave2[3] # Settings object in the payload

    # Wave 1 had p95=0.1 -> timeout = max(5, 0.1*3+1) = 5.0
    assert settings_wave2.shell_timeout == pytest.approx(5.0)

    # Now simulate a third wave to check the next timeout update
    # Need to adjust mocks for 3 waves
    mock_suggest.side_effect = [1, 1, 1]
    task3 = (2, sample_rules[2], ["io_cmd_3"], 15.0) # p95=15.0 -> next timeout = 46.0
    mock_build.return_value = ([task1, task2, task3], {0:{}, 1:{}, 2:{}}, {0:1, 1:1, 2:1})
    f3 = Future()
    wave3_result_payload = (2, [CmdResult(cmd="io_cmd_3", returncode=0, stdout="ok", stderr="", duration_sec=15.0, ok=True)])
    f3.set_result(wave3_result_payload)
    mock_as_completed.side_effect = [[f1], [f2], [f3]]

    # Rerun with 3 waves
    run_all_rules(sample_rules[:3], log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # Check settings passed to the *third* submit call (task3 - IO)
    submit_call_wave3 = mock_thread_executor.submit.call_args_list[1] # Second call to thread pool submit (first was task1)
    payload_wave3 = submit_call_wave3.args[1]
    settings_wave3 = payload_wave3[3]

    # Wave 2 had p95=3.0 -> timeout = max(5, 3.0*3+1) = 10.0
    assert settings_wave3.shell_timeout == pytest.approx(10.0)


def test_run_all_rules_worker_error(
    sample_rules, default_settings, mock_scheduler, mock_tuner, mock_logger, mock_sink,
    mock_executors, mock_helpers, mock_classify):
    """Test handling of exceptions raised by the worker chunk function."""
    mock_build, mock_suggest = mock_scheduler
    mock_guess = mock_tuner
    mock_proc_executor, mock_thread_executor, mock_as_completed = mock_executors
    mock_makedirs, mock_merge, mock_bar, mock_print, mock_time = mock_helpers

    # Arrange: One task that will raise an error in the future
    task1 = (0, sample_rules[0], ["io_cmd_1"], 0.1)
    mock_build.return_value = ([task1], {0:{"rule": sample_rules[0], "denied":[], "ran":[]}}, {0:1})
    mock_suggest.return_value = 1
    mock_guess.side_effect = [1, 1]

    # Simulate future raising an exception
    f1 = Future()
    f1.set_exception(ValueError("Worker failed"))
    mock_as_completed.return_value = [f1]

    # Act
    results = run_all_rules(sample_rules[:1], log_base_dir="/fake/logs", workers=None, settings=default_settings)

    # Assert: _merge_and_log should be called with a synthetic error result
    mock_merge.assert_called_once()
    call_args = mock_merge.call_args[0]
    assert call_args[0] == 0 # idx
    assert call_args[1] == sample_rules[0] # rule
    assert call_args[2] == [] # denied list
    # Check the 'ran' list passed to merge
    ran_list = call_args[3]
    assert len(ran_list) == 1
    error_result = ran_list[0]
    assert isinstance(error_result, CmdResult)
    assert error_result.cmd == "(worker error)"
    assert error_result.returncode is None
    assert "ValueError: Worker failed" in error_result.stderr
    assert error_result.ok is False
    # Check logger was also passed
    assert call_args[4] is mock_logger

    # Check final result structure
    assert len(results) == 1
    assert results[0] == mock_merge.return_value # Should return the result from merge


# --- Test _workers_chunk ---
# Requires mocking the command_runner passed in

@patch('security_app.core.runner.default_command_runner') # Patch default if not passed
def test_workers_chunk(mock_run_fn):
    """Test the _workers_chunk function calls run_fn for each command."""
    rule = MagicMock(spec=Rule)
    cmds = ["cmd1", "cmd2", "cmd3"]
    settings = MagicMock(spec=Settings)
    # Simulate run_fn returning mock results
    mock_res1 = CmdResult("cmd1", 0, "o1", "", 0.1, True)
    mock_res2 = CmdResult("cmd2", 1, "", "e2", 0.2, False)
    mock_res3 = CmdResult("cmd3", 0, "o3", "", 0.1, True)
    mock_run_fn.side_effect = [mock_res1, mock_res2, mock_res3]

    payload = (5, rule, cmds, settings, mock_run_fn) # idx=5

    # Act
    idx_out, results_out = _workers_chunk(payload)

    # Assert
    assert idx_out == 5
    # Check run_fn was called for each command
    assert mock_run_fn.call_count == 3
    mock_run_fn.assert_has_calls([
        call("cmd1", settings),
        call("cmd2", settings),
        call("cmd3", settings),
    ])
    # Check returned results list
    assert results_out == [mock_res1, mock_res2, mock_res3]
