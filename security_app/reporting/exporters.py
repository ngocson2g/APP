#security_app/reporting/exporters.py
"""
Xuất báo cáo sang các format JSON/CSV
"""
import csv
import json
import os
import sys
from typing import Any

from security_app.models import as_rule
from security_app.reporting.scoring import compute_compliance_score, score_grade


def _summary_from_stats(stats: dict[str, Any]) -> dict[str, Any]:
    t = stats.get("totals", {})
    c_score = compute_compliance_score(stats)
    # Giữ schema "gần" với API backend / frontend đang dùng
    return {
        "total_rules":     t.get("total_rules", 0),
        "all_ok":          t.get("rules_all_ok", 0),
        "with_failures":   t.get("rules_with_fail", 0),
        "pass_rate":       round(float(t.get("pass_rate", 0.0)), 2),
        "compliance_score": c_score,
        "compliance_grade": score_grade(c_score),
        "total_commands":  t.get("total_cmds", 0),
        "commands_ok":     t.get("total_ok", 0),
        "commands_failed": t.get("total_fail", 0),
    }

def _by_sev_from_stats(stats: dict[str, Any]) -> dict[str, dict[str, int]]:
    out = {}
    by = stats.get("by_severity", {}) or {}
    for sev, d in by.items():
        rules      = int(d.get("rules", 0))
        rules_fail = int(d.get("rules_fail", 0))
        out[str(sev or "unknown").lower()] = {
            "rules": rules,
            "rules_ok": rules - rules_fail,
            "cmd_ok": int(d.get("ok", 0)),
            "cmd_fail": int(d.get("fail", 0)),
        }
    return out

def _top_from_stats(stats: dict[str, Any]) -> list[dict[str, Any]]:
    tops = []
    idx2agg = {x["rule_index"]: x for x in stats.get("all_results", [])}
    for idx, rid, sev, num_fail, title in stats.get("top_failing_rules", []):
        rr = idx2agg.get(idx, {})
        tops.append({
            "id": str(rid or idx),
            "severity": (sev or "unknown"),
            "title": title or "",
            "cmd_ok": int(rr.get("num_ok", 0)),
            "cmd_fail": int(rr.get("num_fail", num_fail)),
            "status": "ok" if int(rr.get("num_fail", num_fail)) == 0 else "fail",
        })
    return tops


def build_stats_json(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": _summary_from_stats(stats),
        "by_severity": _by_sev_from_stats(stats),
        "top_failing_rules": _top_from_stats(stats),
        "rules": [
            (lambda rule, rec: {
                "id": rule.id or str(rec["rule_index"]),
                "severity": rule.severity or "unknown",
                "title": rule.title or "",
                "cmd_ok": int(rec.get("num_ok", 0)),
                "cmd_fail": int(rec.get("num_fail", 0)),
                "status": "ok" if int(rec.get("num_fail", 0)) == 0 else "fail",
            })(as_rule(rec["rule"]), rec)
            for rec in stats.get("all_results", [])
        ]
    }

def dump_stats_json(stats: dict[str, Any], path: str) -> None:
    data = build_stats_json(stats)
    s = json.dumps(data, ensure_ascii=False, indent=2)
    if path == "-" or path.strip() == "":
        sys.stdout.write(s + "\n")
        return
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)

def _write_csv(path: str, headers: list[str], rows: list[list[object]]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)

def write_stats_csv_bundle(stats: dict[str, Any], out_dir: str) -> None:
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # summary.csv (key,value)
    summary = _summary_from_stats(stats)
    _write_csv(
        os.path.join(out_dir, "summary.csv"),
        ["key", "value"],
        [[k, v] for k, v in summary.items()]
    )

    # by_severity.csv
    by = _by_sev_from_stats(stats)
    _write_csv(
        os.path.join(out_dir, "by_severity.csv"),
        ["severity", "rules", "rules_ok", "cmd_ok", "cmd_fail"],
        [[sev, d["rules"], d["rules_ok"], d["cmd_ok"], d["cmd_fail"]] for sev, d in by.items()]
    )

    # top_failing.csv
    tops = _top_from_stats(stats)
    _write_csv(
        os.path.join(out_dir, "top_failing.csv"),
        ["#", "id", "severity", "title", "cmd_ok", "cmd_fail", "status"],
        [[i+1, t["id"], t["severity"], t["title"], t["cmd_ok"], t["cmd_fail"], t["status"]] for i, t in enumerate(tops)]
    )

    # rules.csv
    rules = build_stats_json(stats)["rules"]
    _write_csv(
        os.path.join(out_dir, "rules.csv"),
        ["id", "severity", "title", "cmd_ok", "cmd_fail", "status"],
        [[r["id"], r["severity"], r["title"], r["cmd_ok"], r["cmd_fail"], r["status"]] for r in rules]
    )

