# security_app/core/runner/tuner.py
from __future__ import annotations

from collections.abc import Sequence
import os
import statistics


def auto_guess_workers(n_tasks: int, use_processes: bool, sample_durs: Sequence[float]) -> int:
    """
    Trả về số worker đề xuất dựa trên độ dài task (p50/p95) và loại pool.
    Ràng buộc: 1 <= workers <= min(512, n_tasks)
    """
    cpu = os.cpu_count() or 4
    n_tasks = max(0, int(n_tasks))
    cap = max(1, min(512, n_tasks))

    if not sample_durs:
        # Fallback bảo thủ
        return max(1, min((cpu if use_processes else 4*cpu), cap))

    durs = [max(0.0, float(d)) for d in sample_durs if d is not None]
    if not durs:
        return max(1, min((cpu if use_processes else 4*cpu), cap))

    p50 = statistics.median(durs)
    try:
        # p95 tương đối: quantiles n=20 ~ 5% step
        p95 = statistics.quantiles(durs, n=20)[18]
    except Exception:
        p95 = max(durs)

    if use_processes:
        # Lệnh dài/CPU-ish: ~CPU; lệnh ngắn: giảm để tránh overhead fork
        base = (os.cpu_count() or 4)
        workers = base if p50 >= 0.75 or p95 >= 1.5 else max(1, base // 2)
    else:
        # Threads: I/O/latency-bound thì oversubscribe vừa phải
        if p50 < 0.15:
            workers = 8 * (os.cpu_count() or 4)
        elif p50 < 0.5:
            workers = 4 * (os.cpu_count() or 4)
        else:
            workers = 2 * (os.cpu_count() or 4)

    return max(1, min(int(workers), cap))

