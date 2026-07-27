# tests/core/runner/test_tuner.py
import pytest
import os
from security_app.core.runner.tuner import auto_guess_workers

# Mock os.cpu_count() if needed, otherwise uses the actual count
CPU_COUNT = os.cpu_count() or 4

@pytest.mark.parametrize("n_tasks, use_processes, sample_durs, expected_workers", [
    # --- Process Pool (use_processes=True) ---
    (100, True, [1.0, 1.2, 0.9, 1.5], CPU_COUNT), # Long tasks -> use all cores
    (100, True, [0.1, 0.2, 0.15, 0.3], max(1, CPU_COUNT // 2)), # Short tasks -> use half cores
    (100, True, [], CPU_COUNT), # No sample -> assume CPU bound, use all cores (fallback)
    (3, True, [1.0, 1.2, 1.5], 3), # Less tasks than cores -> limit to n_tasks
    (5, True, [0.1, 0.2, 0.15], min(max(1, CPU_COUNT // 2), 5)), # Short tasks, limited by n_tasks

    # --- Thread Pool (use_processes=False) ---
    (100, False, [0.1, 0.05, 0.12, 0.08], 8 * CPU_COUNT), # Very short (I/O bound) -> 8x oversubscribe
    (100, False, [0.3, 0.4, 0.25, 0.45], 4 * CPU_COUNT), # Medium (I/O bound) -> 4x oversubscribe
    (100, False, [0.6, 0.8, 1.0, 0.7], 2 * CPU_COUNT), # Longer (less I/O bound?) -> 2x oversubscribe
    (100, False, [], 4 * CPU_COUNT), # No sample -> assume medium I/O bound (fallback)
    (10, False, [0.1, 0.05], min(10, 8 * CPU_COUNT)), # Very short, limited by n_tasks
    (600, False, [0.1, 0.05], min(512, 8 * CPU_COUNT)), # Very short, limited by cap (512)

    # --- Edge Cases ---
    (0, True, [1.0], 1), # No tasks -> 1 worker
    (100, True, [None, 0.1, -0.5], max(1, CPU_COUNT // 2)), # Handle None/negative durs
])
def test_auto_guess_workers(n_tasks, use_processes, sample_durs, expected_workers):
    """Tests worker guessing logic based on task type and duration samples."""
    # Ensure expected_workers doesn't exceed the 512 cap
    capped_expected = max(1, min(expected_workers, 512, n_tasks if n_tasks > 0 else 1))
    assert auto_guess_workers(n_tasks, use_processes, sample_durs) == capped_expected
