# apps/dashboard/backend/main.py

import os, json
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from io import BytesIO

# Cho phép chạy kiểu package và kiểu "uvicorn main:app"
try:
    from .reader import list_runs, get_summary, list_rules, get_timeseries, get_rule_detail
except ImportError:
    from reader import list_runs, get_summary, list_rules, get_timeseries, get_rule_detail

try:
    from .exporter import build_excel, build_pdf, save_copy_if_configured
except ImportError:
    from exporter import build_excel, build_pdf, save_copy_if_configured

# --- CORS config: đọc từ ENV ---
origins = os.getenv("ALLOWED_ORIGINS", "")
allow_origins = [o.strip() for o in origins.split(",") if o.strip()]

app = FastAPI(title="security_app dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["http://localhost:5173"],  # fallback an toàn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- API endpoints ----------------

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

@app.get("/api/runs/timeseries")
def api_runs_timeseries(limit: int = 20):
    return get_timeseries(limit=limit)

@app.get("/api/runs/{run_id}/rule/{index}")
def api_rule_detail(run_id: str, index: int):
    try:
        return get_rule_detail(run_id, index)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Rule not found")

# --- Export Excel ---
@app.get("/api/runs/{run_id}/export/excel")
def api_export_excel(run_id: str):
    try:
        summary = get_summary(run_id)
        rules = list_rules(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    data = build_excel(summary | {
        "by_severity": summary.get("by_severity"),
        "top_failing_rules": summary.get("top_failing_rules"),
        "denied_rules": summary.get("denied_rules", []),
    }, rules)
    save_copy_if_configured(data, run_id, "xlsx")
    filename = f"security-app_{run_id}.xlsx"
    return StreamingResponse(BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# --- Export PDF ---
@app.get("/api/runs/{run_id}/export/pdf")
def api_export_pdf(run_id: str):
    try:
        summary = get_summary(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    data = build_pdf(run_id, summary)
    save_copy_if_configured(data, run_id, "pdf")
    filename = f"security-app_{run_id}.pdf"
    return StreamingResponse(BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# --- Alias dùng ?run= cho FE ---
@app.get("/api/export/pdf")
def api_export_pdf_q(run: str = Query(..., min_length=1)):
    summary = get_summary(run)
    data = build_pdf(run, summary)
    save_copy_if_configured(data, run, "pdf")
    return StreamingResponse(BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="security-app_{run}.pdf"'}
    )

@app.get("/api/export/excel")
def api_export_excel_q(run: str = Query(..., min_length=1)):
    summary = get_summary(run)
    rules = list_rules(run)
    data = build_excel(summary | {
        "by_severity": summary.get("by_severity"),
        "top_failing_rules": summary.get("top_failing_rules"),
        "denied_rules": summary.get("denied_rules", []),
    }, rules)
    save_copy_if_configured(data, run, "xlsx")
    return StreamingResponse(BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="security-app_{run}.xlsx"'}
    )

# --- Capabilities ---
@app.get("/api/capabilities")
def api_capabilities():
    return JSONResponse({
        "export": {"pdf": True, "excel": True},
        "routes": ["/api/export/pdf", "/api/export/excel",
                   "/api/runs/{run_id}/export/pdf", "/api/runs/{run_id}/export/excel"]
    })
    
    
LOGS_DIR = os.environ.get("SECAPP_LOGS_DIR", "logs")

@app.get("/api/runs/{run_id}/waves")
def get_run_waves(run_id: str):
    fp = os.path.join(LOGS_DIR, run_id, "waves.json")
    if not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="waves not found")
    with open(fp, encoding="utf-8") as f:
        data = json.load(f)
    resp = JSONResponse(data)
    # NGĂN CACHE TRÌNH DUYỆT/PROXY
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp