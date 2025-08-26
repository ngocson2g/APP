# apps/dashboard/backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from pathlib import Path
from datetime import datetime

from reader import list_runs, aggregate_run, get_run_path, detect_runs

LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs")).resolve()

app = FastAPI(title="security_app dashboard API", version="0.1.0")

# CORS (dev-friendly: allow localhost/any; tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunInfo(BaseModel):
    id: str
    title: str
    path: str
    mtime: float
    files: int

class Summary(BaseModel):
    total_rules: int
    all_ok: int
    with_failures: int
    pass_rate: float
    total_commands: int
    commands_ok: int
    commands_failed: int
    by_severity: Dict[str, Dict[str, int]]  # {sev: {"rules": x, "rules_ok": y, "cmd_ok": z, "cmd_fail": k}}
    top_failing_rules: List[Dict[str, Any]]

@app.get("/health")
def health():
    return {"status": "ok", "logs_dir": str(LOGS_DIR)}

@app.get("/api/runs", response_model=List[RunInfo])
def api_runs():
    if not LOGS_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Logs dir not found: {LOGS_DIR}")
    runs = list_runs(LOGS_DIR)
    return [RunInfo(**r) for r in runs]

@app.get("/api/runs/{run_id}/summary", response_model=Summary)
def api_summary(run_id: str):
    run_path = get_run_path(LOGS_DIR, run_id)
    if not run_path:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return Summary(**aggregate_run(run_path))

@app.get("/api/runs/{run_id}/rules")
def api_rules(run_id: str):
    run_path = get_run_path(LOGS_DIR, run_id)
    if not run_path:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    data = aggregate_run(run_path)
    return {"run_id": run_id, "rules": data.get("rules", [])}
