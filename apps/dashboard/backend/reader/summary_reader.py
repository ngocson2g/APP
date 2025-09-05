# apps/dashboard/backend/reader/summary_reader.py
from typing import List, Dict, Any
from security_app.reporting.stats import compute_stats
from .rule_reader import _read_run_results
from .run_reader import _list_run_dirs
from .config import LOGS_BASE

def get_summary(run_id: str) -> Dict[str, Any]:
    run_results = _read_run_results(run_id)
    stats = compute_stats(run_results)

    t = stats["totals"]
    summary = {
        "total_rules":    t["total_rules"],
        "all_ok":         t["rules_all_ok"],
        "with_failures":  t["rules_with_fail"],
        "pass_rate":      round(float(t["pass_rate"]), 2),
        "total_commands": t["total_cmds"],
        "commands_ok":    t["total_ok"],
        "commands_failed":t["total_fail"],
    }

    by_sev_src = stats["by_severity"]
    by_sev = {}
    for sev, d in by_sev_src.items():
        by_sev[sev] = {
            "rules": d.get("rules", 0),
            "rules_ok": d.get("rules",0) - d.get("rules_fail",0),
            "cmd_ok": d.get("ok", 0),
            "cmd_fail": d.get("fail", 0),
        }

    idx2agg = {x["rule_index"]: x for x in stats["all_results"]}
    tops = []
    for idx, rid, sev, num_fail, title in stats["top_failing_rules"]:
        rr = idx2agg.get(idx, {})
        tops.append({
            "rule_index": idx,
            "id": rid,
            "severity": sev or "unknown",
            "title": title or "",
            "cmd_ok": rr.get("num_ok", 0),
            "cmd_fail": rr.get("num_fail", num_fail),
            "status": "ok" if rr.get("num_fail", num_fail) == 0 else "fail",
        })

    summary["by_severity"] = by_sev
    summary["top_failing_rules"] = tops

    denied_rules = []
    total_denied_cmds = 0
    order = {"critical":5,"high":4,"medium":3,"low":2,"unknown":1}
    for r in run_results:
        nd = int(r.get("num_denied", 0) or 0)
        if nd > 0:
            total_denied_cmds += nd
            rule = r["rule"] or {}
            denied_rules.append({
                "id": rule.get("id") or str(r["rule_index"]),
                "severity": (rule.get("severity") or "unknown").lower(),
                "title": rule.get("title") or "",
                "denied": nd,
                "examples": r.get("denied_cmds", []),
            })
    denied_rules.sort(key=lambda x: ((-order.get(x["severity"],0)), -x["denied"]))

    summary["denied"] = {
        "rules_with_denied": len(denied_rules),
        "total_denied_cmds": total_denied_cmds,
    }
    summary["denied_rules"] = denied_rules
    return summary

def list_rules(run_id: str) -> List[Dict[str, Any]]:
    rs = _read_run_results(run_id)
    out = []
    for r in rs:
        rule = r["rule"]
        out.append({
            "rule_index": r["rule_index"],
            "id": rule.get("id") or str(r["rule_index"]),
            "severity": (rule.get("severity") or "unknown"),
            "title": rule.get("title") or "",
            "cmd_ok": r["num_ok"],
            "cmd_fail": r["num_fail"],
            "status": "ok" if r["num_fail"] == 0 else "fail",
        })
    return out

def get_timeseries(limit: int = 20) -> List[Dict[str, Any]]:
    runs = _list_run_dirs(LOGS_BASE)[: max(1, int(limit))]
    items: List[Dict[str, Any]] = []
    for r in runs:
        rs = _read_run_results(r["id"])
        stats = compute_stats(rs)
        t = stats["totals"]
        items.append({
            "id": r["id"],
            "mtime": r["mtime"],
            "files": r["files"],
            "total_rules":    t["total_rules"],
            "all_ok":         t["rules_all_ok"],
            "with_failures":  t["rules_with_fail"],
            "pass_rate":      round(float(t["pass_rate"]), 2),
            "total_commands": t["total_cmds"],
            "commands_ok":    t["total_ok"],
            "commands_failed":t["total_fail"],
        })
    items.sort(key=lambda x: x["mtime"])
    return items