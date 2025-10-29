# #tests/core/runner/test_scheduler.py
# import pytest
# from unittest.mock import patch, MagicMock
# from security_app.models import Rule, CmdResult
# from security_app.core.runner.scheduler import (
#     build_scheduled_tasks,
#     suggest_wave_size,
#     _chunk_dynamic,
#     _mk_denied
# )

# # Sample Rules
# rule1 = Rule(id="R1", check="$ cmd1\n$ cmd2", severity="high")
# rule2 = Rule(id="R2", check="$ cmd3", severity="medium")
# rule_short_many = Rule(id="R3", check="\n".join([f"$ sleep 0.0{i}" for i in range(15)]), severity="low")
# rule_mixed = Rule(id="R4", check="$ long_cmd\n$ short1\n$ short2", severity="high")
# rule_denied = Rule(id="R5", check="$ rm -rf /\n$ ls", severity="critical")

# # --- Test Helpers ---

# def test_mk_denied():
#     """Test creating a denied CmdResult."""
#     reason = "DENIED by test"
#     cmd = "dangerous_cmd"
#     res = _mk_denied(cmd, reason)
#     assert isinstance(res, CmdResult)
#     assert res.cmd == cmd
#     assert res.stderr == reason
#     assert res.returncode is None
#     assert res.ok is False
#     assert res.duration_sec == 0.0

# @pytest.mark.parametrize("cmds, ests, expected_chunks", [
#     (["c1", "c2"], [0.5, 0.6], [["c1"], ["c2"]]), # Not enough commands for chunking
#     ([f"c{i}" for i in range(9)], [0.1] * 9, [[f"c{i}"] for i in range(9)]), # < 10 commands
#     ([f"c{i}" for i in range(15)], [0.1] * 15, [['c0','c1','c2','c3','c4'], ['c5','c6','c7','c8','c9'], ['c10','c11','c12','c13','c14']]), # >=10, all short, max_est < 0.1 -> chunk 5
#     ([f"c{i}" for i in range(12)], [0.1] * 10 + [0.2, 0.2], [['c0','c1','c2','c3'], ['c4','c5','c6','c7'], ['c8','c9','c10','c11']]), # >=10, >=60% short, max_est > 0.1 -> chunk 4
#     ([f"c{i}" for i in range(10)], [0.5] * 10, [[f"c{i}"] for i in range(10)]), # >=10, but not enough short ones
# ])
# def test_chunk_dynamic(cmds, ests, expected_chunks):
#     """Test dynamic chunking logic."""
#     assert _chunk_dynamic(cmds, ests) == expected_chunks

# @pytest.mark.parametrize("backlog, expected_size", [
#     (0, 8),      # No backlog -> min size
#     (10, 8),     # Small backlog -> min size
#     (32, 8),     # backlog // 4 = 8
#     (100, 25),   # backlog // 4 = 25
#     (500, 125),  # backlog // 4 = 125
#     (600, 128),  # backlog // 4 > 128 -> max size
#     (1000, 128), # Large backlog -> max size
# ])
# def test_suggest_wave_size(backlog, expected_size):
#     """Test wave size suggestion logic."""
#     assert suggest_wave_size(backlog) == expected_size

# # --- Test build_scheduled_tasks ---

# # Mock the estimator functions to avoid actual file reading/complex calculation
# @pytest.fixture
# def mock_estimators():
#     # Mock return values: hist_data, estimate_func
#     # Estimate func returns estimate based on command string length for simplicity
#     mock_hist = {"sleep": (0.05, 0.08, 10), "long_cmd": (1.5, 2.0, 5)}
#     def mock_estimate(cmd, hist):
#         if "sleep" in cmd: return 0.05
#         if "long_cmd" in cmd: return 1.5
#         if "short" in cmd: return 0.1
#         return len(cmd) * 0.1 # Simple estimate based on length
#     with patch('security_app.core.runner.scheduler._get_estimators', return_value=(lambda _: mock_hist, mock_estimate)):
#         yield

# def test_build_scheduled_tasks_simple(mock_estimators):
#     """Test basic scheduling, LPT sorting, and aggregation."""
#     rules = [rule1, rule2] # R1: cmd1 (0.4s), cmd2 (0.4s); R2: cmd3 (0.4s)
#     tasks, agg, pending = build_scheduled_tasks(rules, logs_base_dir="dummy")

#     # Check aggregation structure
#     assert 0 in agg and 1 in agg
#     assert agg[0]['rule'] == rule1
#     assert agg[1]['rule'] == rule2
#     assert agg[0]['denied'] == []
#     assert agg[1]['denied'] == []
#     assert 0 in pending and 1 in pending
#     assert pending[0] == 2 # Rule 1 has 2 commands -> 2 tasks (no chunking)
#     assert pending[1] == 1 # Rule 2 has 1 command -> 1 task

#     # Check tasks list (should be sorted by estimate descending)
#     # Estimates: cmd1=0.4, cmd2=0.4, cmd3=0.4 (all equal in this mock)
#     # Order might vary slightly if estimates are identical, but check content
#     assert len(tasks) == 3
#     assert tasks[0][3] == pytest.approx(0.4) # estimate
#     assert tasks[1][3] == pytest.approx(0.4)
#     assert tasks[2][3] == pytest.approx(0.4)
#     # Check that tasks belong to correct rules and contain correct commands
#     assert tasks[0][1] == rule1 and tasks[0][2] == ["cmd1"] # (idx, rule, chunk_cmds, est)
#     assert tasks[1][1] == rule1 and tasks[1][2] == ["cmd2"]
#     assert tasks[2][1] == rule2 and tasks[2][2] == ["cmd3"]

# def test_build_scheduled_tasks_with_chunking(mock_estimators):
#     """Test scheduling with dynamic chunking."""
#     rules = [rule_short_many] # 15 short commands (est 0.05s each)
#     tasks, agg, pending = build_scheduled_tasks(rules, logs_base_dir="dummy")

#     assert 0 in agg and agg[0]['rule'] == rule_short_many
#     assert 0 in pending
#     # 15 commands, est < 0.1s -> chunk size 5 -> 3 chunks/tasks
#     assert pending[0] == 3
#     assert len(tasks) == 3

#     # Check chunk content and estimate (0.05 * 5 = 0.25)
#     assert tasks[0][2] == [f"sleep 0.0{i}" for i in range(5)] # Chunk 1
#     assert tasks[0][3] == pytest.approx(0.25)
#     assert tasks[1][2] == [f"sleep 0.0{i}" for i in range(5, 10)] # Chunk 2
#     assert tasks[1][3] == pytest.approx(0.25)
#     assert tasks[2][2] == [f"sleep 0.0{i}" for i in range(10, 15)] # Chunk 3
#     assert tasks[2][3] == pytest.approx(0.25)

# def test_build_scheduled_tasks_with_denied(mock_estimators):
#     """Test handling of denied commands."""
#     rules = [rule_denied] # R5: rm -rf /, ls
#     tasks, agg, pending = build_scheduled_tasks(rules, logs_base_dir="dummy")

#     assert 0 in agg and agg[0]['rule'] == rule_denied
#     # Check denied list in aggregator
#     assert len(agg[0]['denied']) == 1
#     assert agg[0]['denied'][0].cmd == "rm -rf /"
#     assert "DENIED" in agg[0]['denied'][0].stderr

#     # Check pending tasks (only 'ls' should be scheduled)
#     assert 0 in pending and pending[0] == 1
#     assert len(tasks) == 1
#     assert tasks[0][1] == rule_denied
#     assert tasks[0][2] == ["ls"] # Only the allowed command
#     assert tasks[0][3] == pytest.approx(len("ls") * 0.1) # Estimate for 'ls'
