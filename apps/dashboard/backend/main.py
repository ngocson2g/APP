# apps/dashboard/backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Cho phép chạy kiểu package và kiểu "uvicorn main:app"
try:
    from .reader import list_runs, get_summary, list_rules  # chạy từ root: uvicorn apps.dashboard.backend.main:app
except ImportError:
    from reader import list_runs, get_summary, list_rules    # chạy trong thư mục backend: uvicorn main:app

app = FastAPI(title="security_app dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/runs")
def api_runs():
    return list_runs()

@app.get("/api/runs/{run_id}/summary")
def api_summary(run_id: str):
    try:
        return get_summary(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")

@app.get("/api/runs/{run_id}/rules")
def api_rules(run_id: str):
    try:
        return list_rules(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
