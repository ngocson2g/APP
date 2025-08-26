# apps/dashboard/backend/reader.py
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

LOG_PATTERNS = [
    re.compile(r"\.log$", re.IGNORECASE),
]

ID_PATS = [
    re.compile(r"^\s*(?:Rule\s*ID|Rule|ID)\s*[:#]\s*(.+)$", re.IGNORECASE | re.MULTILINE),
]
SEV_PATS = [
    re.compile(r"^\s*Severity\s*:\s*([A-Za-z]+)\s*$", re.IGNORECASE | re.MULTILINE),
]
TITLE_PATS = [
    re.compile(r"^\s*(?:Title|Name)\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE),
]

OK_PAT = re.compile(r"\b(OK|SUCCESS|PASSED)\b", re.IGNORECASE)
FAIL_PAT = re.compile(r"\b(FAIL|FAILED|ERROR)\b", re.IGNORECASE)

def _is_log_file(p: Path) -> bool:
    if not p.is_file():
        return False
    s = str(p.name)
    return any(pat.search(s) for pat in LOG_PATTERNS)

def _list_log_files(run_path: Path) -> List[Path]:
    files = [p for p in run_path.iterdir() if _is_log_file(p)]
    # also check nested "per-rule" folder if present
    per_rule = run_path / "rules"
    if per_rule.exists() and per_rule.is_dir():
        files += [p for p in per_rule.iterdir() if _is_log_file(p)]
    return files

def detect_runs(logs_dir: Path) -> List[Path]:
    # If there are subdirs with .log files, treat each as a run
    subdirs = [p for p in logs_dir.iterdir() if p.is_dir()]
    run_dirs = []
    for d in subdirs:
        if _list_log_files(d):
            run_dirs.append(d)
    if run_dirs:
        return run_dirs
    # fallback: treat logs_dir itself as a single run
    if _list_log_files(logs_dir):
        return [logs_dir]
    return []

def list_runs(logs_dir: Path) -> List[Dict[str, Any]]:
    runs = []
    for run_path in detect_runs(logs_dir):
        if run_path == logs_dir and run_path.name != "logs":
            run_id = run_path.name
        elif run_path == logs_dir:
            run_id = "_root"
        else:
            run_id = run_path.name
        files = _list_log_files(run_path)
        mtime = max((f.stat().st_mtime for f in files), default=run_path.stat().st_mtime)
        runs.append({
            "id": run_id,
            "title": f"Run {run_id}",
            "path": str(run_path.resolve()),
            "mtime": mtime,
            "files": len(files),
        })
    runs.sort(key=lambda r: r["mtime"], reverse=True)
    return runs

def get_run_path(logs_dir: Path, run_id: str) -> Path | None:
    if run_id == "_root":
        path = logs_dir
    else:
        path = logs_dir / run_id
        if not path.exists():
            # also allow absolute path (dangerous; reject) — safer to only allow direct subdir or logs root
            return None
    if not path.exists() or not path.is_dir():
        return None
    return path

def _extract_first(pats: List[re.Pattern], text: str) -> str:
    for pat in pats:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return ""

def _fallback_from_filename(fp: Path) -> Dict[str, str]:
    # Try to glean id/severity from filename, e.g., "rule-001_id-CIS-1.1.1_high.log"
    name = fp.stem
    rid = ""
    sev = ""
    m = re.search(r"(CIS|NIST|STIG)[-_]?\w*[-_]*(\d[\w\.\-]*)", name, re.IGNORECASE)
    if m:
        rid = f"{m.group(1).upper()}-{m.group(2)}"
    m2 = re.search(r"(low|medium|high|critical)", name, re.IGNORECASE)
    if m2:
        sev = m2.group(1).lower()
    return {"id": rid, "severity": sev}

def parse_rule_log(fp: Path) -> Dict[str, Any]:
    try:
        text = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        text = ""
    rid = _extract_first(ID_PATS, text) or _fallback_from_filename(fp)["id"] or fp.stem
    title = _extract_first(TITLE_PATS, text)
    sev = (_extract_first(SEV_PATS, text) or _fallback_from_filename(fp)["severity"] or "unknown").lower()

    # Heuristics for counting command OK/FAIL lines
    cmd_ok = len(OK_PAT.findall(text))
    cmd_fail = len(FAIL_PAT.findall(text))
    status = "ok" if cmd_fail == 0 and cmd_ok > 0 else ("unknown" if (cmd_ok==0 and cmd_fail==0) else "fail")

    return {
        "id": rid,
        "title": title,
        "severity": sev,
        "cmd_ok": cmd_ok,
        "cmd_fail": cmd_fail,
        "status": status,
        "file": str(fp),
    }

def aggregate_run(run_path: Path) -> Dict[str, Any]:
    files = _list_log_files(run_path)
    rules = [parse_rule_log(fp) for fp in files]

    total_rules = len(rules)
    all_ok = sum(1 for r in rules if r["status"] == "ok")
    with_failures = sum(1 for r in rules if r["status"] == "fail")
    total_commands = sum(r["cmd_ok"] + r["cmd_fail"] for r in rules)
    commands_ok = sum(r["cmd_ok"] for r in rules)
    commands_failed = sum(r["cmd_fail"] for r in rules)
    pass_rate = (all_ok / total_rules * 100.0) if total_rules else 0.0

    # By severity
    by_sev: Dict[str, Dict[str, int]] = {}
    def acc(sev: str) -> Dict[str, int]:
        if sev not in by_sev:
            by_sev[sev] = {"rules": 0, "rules_ok": 0, "cmd_ok": 0, "cmd_fail": 0}
        return by_sev[sev]

    for r in rules:
        s = acc(r["severity"] or "unknown")
        s["rules"] += 1
        if r["status"] == "ok":
            s["rules_ok"] += 1
        s["cmd_ok"] += r["cmd_ok"]
        s["cmd_fail"] += r["cmd_fail"]

    # Top failing rules (by cmd_fail, then by presence of fail status)
    top_failing = sorted(rules, key=lambda x: (x["cmd_fail"], x["status"]=="fail"), reverse=True)[:10]

    return {
        "total_rules": total_rules,
        "all_ok": all_ok,
        "with_failures": with_failures,
        "pass_rate": round(pass_rate, 2),
        "total_commands": total_commands,
        "commands_ok": commands_ok,
        "commands_failed": commands_failed,
        "by_severity": by_sev,
        "top_failing_rules": top_failing,
        "rules": rules,
    }
