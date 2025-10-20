# security_app/core/runner/metrics.py
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict
from security_app.runtime.ownership import chown_path

class WaveMetricsSink:
    """
    Trách nhiệm duy nhất: quản lý và flush metrics theo wave ra waves.json
    Định dạng giữ nguyên để FE /api/runs/{run_id}/waves dùng lại được.
    """
    def __init__(self, run_dir: str, total_cmds: int):
        self.run_dir = os.path.abspath(run_dir)
        self.run_id = os.path.basename(self.run_dir)
        os.makedirs(self.run_dir, exist_ok=True)
        now = time.time()
        self._metrics: Dict[str, Any] = {
            "run_id": self.run_id,
            "started_at": now,
            "total_cmds": int(total_cmds),
            "waves": [],
            "updated_at": now,
        }
        self._flush()

    def add_wave(self, wave_no: int, *,
                 started_at: float, ended_at: float,
                 cmds_total: int, thr_total: float, thr_cpu: float, thr_io: float,
                 timeouts: int, timeout_rate: float, p50: float, p95: float) -> None:
        self._metrics["waves"].append({
            "wave": int(wave_no),
            "started_at": float(started_at),
            "ended_at": float(ended_at),
            "elapsed_sec": round(float(ended_at - started_at), 6),
            "cmds": int(cmds_total),
            "thr_total": round(float(thr_total), 6),
            "thr_cpu": round(float(thr_cpu), 6),
            "thr_io": round(float(thr_io), 6),
            "timeouts": int(timeouts),
            "timeout_rate": round(float(timeout_rate), 6),
            "p50": round(float(p50), 6),
            "p95": round(float(p95), 6),
        })
        self._metrics["updated_at"] = time.time()
        self._flush()

    def finish(self) -> None:
        self._metrics["finished_at"] = time.time()
        self._flush()

    # ---------- private ----------
    def _flush(self) -> None:
        tmp = os.path.join(self.run_dir, "waves.json.tmp")
        dst = os.path.join(self.run_dir, "waves.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._metrics, f, ensure_ascii=False, indent=2)
        os.replace(tmp, dst)
        chown_path(dst)