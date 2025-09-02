# apps/dashboard/backend/reader.py
# stdlib
import os, re, glob, json, time
from dataclasses import dataclass
from typing import List, Dict, Any
from security_app.reporting.stats import compute_stats

# dùng lại compute_stats của CLI để đảm bảo cùng một công thức
from security_app.reporting.stats import compute_stats  # totals/by_severity/top_failing/all_results

LOGS_BASE = os.environ.get("LOGS_DIR", "logs")

_RC_OK_LINE = re.compile(r"^RC=(?P<rc>-?\d+|None)\s*\|\s*OK=(?P<ok>True|False)\b")
_ID_LINE     = re.compile(r"^ID\s*: (.+)$")
_TITLE_LINE  = re.compile(r"^Title\s*: (.*)$")
_SEV_LINE    = re.compile(r"^Severity\s*: (.*)$")

@dataclass
class RuleFile:
    index: int
    path: str

def _list_run_dirs(base: str) -> List[Dict[str, Any]]:
    if not os.path.isdir(base):
        return []
    items = []
    for name in os.listdir(base):
        p = os.path.join(base, name)
        if not os.path.isdir(p):
            continue
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            mtime = 0.0
        files = len(glob.glob(os.path.join(p, "rule-*.log")))
        items.append({"id": name, "title": f"Run {name}", "mtime": mtime, "files": files})
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def list_runs() -> List[Dict[str, Any]]:
    return _list_run_dirs(LOGS_BASE)

def _parse_rule_log(path: str) -> Dict[str, Any]:
    # lấy index từ tên file rule-XXX_*.log
    base = os.path.basename(path)
    try:
        idx = int(base.split("_", 1)[0].replace("rule-", ""))
    except Exception:
        idx = 0

    rid = title = sev = ""
    num_ok = num_fail = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            m = _ID_LINE.match(line)
            if m: 
                rid = m.group(1).strip()
                continue
            m = _TITLE_LINE.match(line)
            if m:
                title = m.group(1).strip()
                continue
            m = _SEV_LINE.match(line)
            if m:
                sev = (m.group(1) or "").strip().lower()
                continue
            m = _RC_OK_LINE.match(line)
            if m:
                ok = m.group("ok") == "True"
                if ok: num_ok += 1
                else:  num_fail += 1

    return {
        "rule_index": idx,
        "rule": {"id": rid, "title": title, "severity": sev},
        "cmd_results": None,                    # không cần cho stats
        "num_cmds": num_ok + num_fail,
        "num_ok": num_ok,
        "num_fail": num_fail,
    }

def _read_run_results(run_id: str) -> List[Dict[str, Any]]:
    run_dir = os.path.join(LOGS_BASE, run_id)
    files = sorted(glob.glob(os.path.join(run_dir, "rule-*.log")))
    results = [_parse_rule_log(p) for p in files]
    results.sort(key=lambda x: x["rule_index"])
    return results

def get_summary(run_id: str) -> Dict[str, Any]:
    run_results = _read_run_results(run_id)
    stats = compute_stats(run_results)   # chuẩn công thức CLI 

    t = stats["totals"]
    # Chuẩn hoá về key mà frontend đang dùng (không đổi công thức)
    summary = {
        "total_rules":    t["total_rules"],
        "all_ok":         t["rules_all_ok"],
        "with_failures":  t["rules_with_fail"],
        "pass_rate":      round(float(t["pass_rate"]), 2),  # % theo RULE, như CLI
        "total_commands": t["total_cmds"],
        "commands_ok":    t["total_ok"],
        "commands_failed":t["total_fail"],
    }

    # map by_severity -> đúng field UI: rules_ok, cmd_ok, cmd_fail
    by_sev_src = stats["by_severity"]  # {sev:{rules,rules_fail,ok,fail,cmds}}
    by_sev = {}
    for sev, d in by_sev_src.items():
        by_sev[sev] = {
            "rules": d.get("rules", 0),
            "rules_ok": d.get("rules",0) - d.get("rules_fail",0),
            "cmd_ok": d.get("ok", 0),
            "cmd_fail": d.get("fail", 0),
        }

    # top failing cho bảng
    # stats["top_failing_rules"] là list tuple (idx, id, sev, num_fail, title) 
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
    """
    Trả về chuỗi thời gian của các lần run gần nhất (tối đa 'limit'),
    mỗi điểm gồm pass_rate và các số đếm tổng quan để vẽ biểu đồ.
    """
    # list_runs hiện sort theo mtime DESC (mới nhất trước) → ta đảo lại để vẽ trái→phải theo thời gian.
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
    items.sort(key=lambda x: x["mtime"])  # thời gian tăng dần cho trục X
    return items

def _read_rule_file(run_id: str, rule_index: int) -> str:
    run_dir = os.path.join(LOGS_BASE, run_id)
    # ưu tiên rule-XXX_*.log (3 chữ số); fallback rule-X_*.log
    patt1 = os.path.join(run_dir, f"rule-{rule_index:03d}_*.log")
    patt2 = os.path.join(run_dir, f"rule-{rule_index}_*.log")
    matches = glob.glob(patt1) or glob.glob(patt2)
    if not matches:
        # thêm fallback: quét toàn bộ rồi lọc prefix
        all_logs = sorted(glob.glob(os.path.join(run_dir, "rule-*.log")))
        pref = f"rule-{rule_index:03d}_"
        pref2 = f"rule-{rule_index}_"
        for p in all_logs:
            b = os.path.basename(p)
            if b.startswith(pref) or b.startswith(pref2):
                matches = [p]; break
    if not matches:
        raise FileNotFoundError(f"Rule file not found for idx={rule_index}")
    return matches[0]

def get_rule_detail(run_id: str, rule_index: int) -> Dict[str, Any]:
    run_dir = os.path.join(LOGS_BASE, run_id)
    patt1 = os.path.join(run_dir, f"rule-{rule_index:03d}_*.log")
    patt2 = os.path.join(run_dir, f"rule-{rule_index}_*.log")
    matches = glob.glob(patt1) or glob.glob(patt2)
    if not matches:
        raise FileNotFoundError(f"Rule file not found for idx={rule_index}")
    path = matches[0]

    rid = title = sev = ""
    check_lines, commands = [], []
    in_check = in_cmds = False
    cur = None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")
            # headers
            m = _ID_LINE.match(line);     
            if m: rid = m.group(1).strip();           continue
            m = _TITLE_LINE.match(line);  
            if m: title = (m.group(1) or "").strip(); continue
            m = _SEV_LINE.match(line);    
            if m: sev = (m.group(1) or "").strip().lower(); continue

            # sections
            if line.strip() == "---- Check ----":
                in_check, in_cmds = True, False;  continue
            if line.strip() == "---- Command Results ----":
                in_check, in_cmds = False, True;  continue

            if in_check:
                check_lines.append(line);          continue

            if in_cmds:
                if line.startswith("$ "):
                    if cur: commands.append(cur);  cur = None
                    cur = {"cmd": line[2:].strip(), "returncode": None, "ok": False,
                           "duration_sec": 0.0, "stdout": "", "stderr": "", "_mode": "stdout"}
                    continue
                m = _RC_OK_LINE.match(line)
                if m and cur:
                    rc = m.group("rc")
                    cur["returncode"] = (None if rc == "None" else int(rc))
                    cur["ok"] = (m.group("ok") == "True")
                    md = re.search(r"([0-9.]+)s$", line)
                    if md:
                        try: cur["duration_sec"] = float(md.group(1))
                        except Exception: pass
                    continue
                if line.strip() == "-- stdout --":
                    if cur: cur["_mode"] = "stdout";  continue
                if line.strip() == "-- stderr --":
                    if cur: cur["_mode"] = "stderr";  continue
                if cur:
                    if cur.get("_mode") == "stderr":
                        cur["stderr"] += (line + "\n")
                    else:
                        cur["stdout"] += (line + "\n")

    if cur: commands.append(cur)
    return {
        "rule_index": rule_index,
        "rule": {"id": rid, "title": title, "severity": sev},
        "check": "\n".join(check_lines).rstrip("\n"),
        "commands": [{k: v for k, v in c.items() if not k.startswith("_")} for c in commands],
        "path": os.path.basename(path),
    }