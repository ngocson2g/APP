# security_app/app/query.py
"""
Module cho subcommand query - Truy vấn log results với các filter khác nhau
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from datetime import datetime
from typing import Any

from security_app.config import DEFAULT_LOGS_DIR
from security_app.utils.text import _table

# Định dạng log đang dùng:
_ID_LINE     = re.compile(r"^ID\s*: (.+)$", re.M)
_TITLE_LINE  = re.compile(r"^Title\s*: (.*)$", re.M)
_SEV_LINE    = re.compile(r"^Severity\s*: (.*)$", re.M)
_RC_OK_LINE  = re.compile(r"^RC=(?P<rc>-?\d+|None)\s*\|\s*OK=(?P<ok>True|False)\b")
_CHECK_BLOCK = re.compile(r"---- Check ----\n(.*?)\n---- Command Results ----", re.S)

SEV_ORDER = {"critical": 5, "high": 4, "medium": 3, "low": 2, "unknown": 1, "": 0}

def _list_runs(base: str) -> list[dict[str, Any]]:
    if not os.path.isdir(base): return []
    items = []
    for name in os.listdir(base):
        p = os.path.join(base, name)
        if not os.path.isdir(p): continue
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            mtime = 0.0
        files = len(glob.glob(os.path.join(p, "rule-*.log")))
        items.append({"id": name, "mtime": mtime, "files": files, "path": p})
    # mới nhất trước
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def _parse_rule_log(fp: str) -> dict[str, Any]:
    with open(fp, encoding="utf-8", errors="ignore") as f:
        s = f.read()

    rid   = (_ID_LINE.search(s).group(1).strip()   if _ID_LINE.search(s)   else "")
    title = (_TITLE_LINE.search(s).group(1).strip()if _TITLE_LINE.search(s) else "")
    sev   = (_SEV_LINE.search(s).group(1).strip().lower() if _SEV_LINE.search(s) else "unknown")
    check = (_CHECK_BLOCK.search(s).group(1).strip() if _CHECK_BLOCK.search(s) else "")

    num_ok = num_fail = 0
    for line in s.splitlines():
        m = _RC_OK_LINE.match(line.strip())
        if not m: continue
        ok = (m.group("ok") == "True")
        if ok: num_ok += 1
        else:  num_fail += 1

    return {
        "id": rid or "",
        "title": title or "",
        "severity": sev or "unknown",
        "cmd_ok": num_ok,
        "cmd_fail": num_fail,
        "status": "ok" if num_fail == 0 else "fail",
        "check": check,
    }

def _pick_runs(runs: list[dict[str, Any]], last: int|None, since: float|None, until: float|None) -> list[dict[str, Any]]:
    rs = runs
    if since is not None: rs = [r for r in rs if r["mtime"] >= since]
    if until is not None: rs = [r for r in rs if r["mtime"] <= until]
    if last is not None:  rs = rs[: max(1, int(last))]
    return rs

def _parse_dt(s: str|None) -> float|None:
    if not s: return None
    # hỗ trợ ISO rút gọn: YYYY-MM-DD[ HH:MM:SS]
    try:
        if " " in s or "T" in s:
            s = s.replace("T", " ")
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
        return datetime.strptime(s, "%Y-%m-%d").timestamp()
    except Exception:
        # fallback: epoch/float
        try:
            return float(s)
        except Exception:
            return None

def _match_keywords(rec: dict[str, Any], keywords: list[str], scope: str) -> bool:
    if not keywords: return True
    scope = (scope or "any").lower()
    hay = []
    if scope in ("any","id"):    hay.append(rec["id"])
    if scope in ("any","title"): hay.append(rec["title"])
    if scope in ("any","check"): hay.append(rec.get("check",""))
    blob = " \n".join(str(x) for x in hay).lower()
    return all(k.lower() in blob for k in keywords)

def query(
    logs_dir: str,
    run_id: str|None,
    last: int|None,
    since: str|None,
    until: str|None,
    severities: list[str]|None,
    status: str|None,
    keywords: list[str]|None,
    scope: str,
    output_json: bool,
    limit: int|None,
) -> int:
    runs = _list_runs(logs_dir)
    if run_id:
        runs = [r for r in runs if r["id"] == run_id]
    runs = _pick_runs(
        runs,
        last=last,
        since=_parse_dt(since),
        until=_parse_dt(until),
    )
    if not runs:
        print("No runs matched.")
        return 0

    rows: list[dict[str, Any]] = []
    for r in runs:
        for fp in sorted(glob.glob(os.path.join(r["path"], "rule-*.log"))):
            rec = _parse_rule_log(fp)
            if severities:
                if (rec["severity"] or "unknown").lower() not in {s.lower() for s in severities}:
                    continue
            if status and rec["status"] != status.lower():
                continue
            if not _match_keywords(rec, keywords or [], scope):
                continue
            rows.append({
                "run": r["id"],
                "time": datetime.fromtimestamp(r["mtime"]).isoformat(sep=" ", timespec="seconds"),
                **rec
            })

    # sắp xếp: severity desc → cmd_fail desc → id
    rows.sort(key=lambda x: (-(SEV_ORDER.get(x["severity"],0)), -(x["cmd_fail"] or 0), str(x["id"])))

    if limit is not None:
        rows = rows[: max(1, int(limit))]

    if output_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    if not rows:
        print("No records matched filters.")
        return 0

    headers = ["#", "Run", "Time", "Rule ID", "Severity", "Status", "Cmd OK", "Cmd Fail", "Title"]
    table = []
    for i, r in enumerate(rows, start=1):
        table.append([
            i, r["run"], r["time"], r["id"] or "—",
            r["severity"], r["status"], r["cmd_ok"], r["cmd_fail"], r["title"] or "—"
        ])
    _table(table, headers=headers)
    print(f"\nMatched {len(rows)} rule(s) across {len({x['run'] for x in rows})} run(s).")
    return 0

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="security-app query", description="Query rule logs by time/severity/status/keywords.")
    p.add_argument("--logs-dir", default=DEFAULT_LOGS_DIR, help=f"Logs base directory (default: {DEFAULT_LOGS_DIR})")
    g = p.add_argument_group("Time window")
    g.add_argument("--run", help="Exact run id (e.g. 2025-09-01_18-37-45)")
    g.add_argument("--last", type=int, help="Pick last N runs (after time filters)")
    g.add_argument("--since", help=">= time (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')")
    g.add_argument("--until", help="<= time (YYYY-MM-DD or 'YYYY-MM-DD HH:MM:SS')")
    f = p.add_argument_group("Filters")
    f.add_argument("--severity", nargs="+", help="One or more of: low medium high critical unknown")
    f.add_argument("--status", choices=["ok","fail"], help="Rule-level status")
    f.add_argument("-q", "--query", nargs="+", help="Keywords to search")
    f.add_argument("--scope", choices=["any","id","title","check"], default="any", help="Keyword search scope (default: any)")
    o = p.add_argument_group("Output")
    o.add_argument("--json", action="store_true", help="Print JSON instead of table")
    o.add_argument("--limit", type=int, help="Limit number of rows shown")
    args = p.parse_args(argv)

    return query(
        logs_dir=args.logs_dir,
        run_id=args.run,
        last=args.last,
        since=args.since,
        until=args.until,
        severities=args.severity,
        status=args.status,
        keywords=args.query,
        scope=args.scope,
        output_json=args.json,
        limit=args.limit,
    )

if __name__ == "__main__":
    raise SystemExit(main())
