# apps/dashboard/backend/reader/rule_reader.py
import glob
import os
from typing import Any, Dict, List

from .config import (_CMD_LINE, _DENIED_MARK, _ID_LINE, _RC_OK_LINE, _SEV_LINE,
                     _TITLE_LINE, LOGS_BASE)


def _parse_rule_log(path: str) -> Dict[str, Any]:
    base = os.path.basename(path)
    try:
        idx = int(base.split("_", 1)[0].replace("rule-", ""))
    except Exception:
        idx = 0

    rid = title = sev = ""
    num_ok = num_fail = 0
    num_denied = 0
    denied_cmds = []
    current_cmd = None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")

            m = _CMD_LINE.match(line)
            if m:
                current_cmd = m.group(1).strip()
                continue

            m = _RC_OK_LINE.match(line)
            if m:
                ok = m.group("ok") == "True"
                if ok: num_ok += 1
                else:  num_fail += 1
                continue

            if _DENIED_MARK.search(line):
                num_denied += 1
                if current_cmd:
                    denied_cmds.append(current_cmd)
                continue

            m = _ID_LINE.match(line)
            if m:
                rid = m.group(1).strip(); continue
            m = _TITLE_LINE.match(line)
            if m:
                title = m.group(1).strip(); continue
            m = _SEV_LINE.match(line)
            if m:
                sev = (m.group(1) or "").strip().lower(); continue

    return {
        "rule_index": idx,
        "rule": {"id": rid, "title": title, "severity": sev},
        "cmd_results": None,
        "num_cmds": num_ok + num_fail,
        "num_ok": num_ok,
        "num_fail": num_fail,
        "num_denied": num_denied,
        "denied_cmds": denied_cmds[:3],
    }

def _read_run_results(run_id: str) -> List[Dict[str, Any]]:
    run_dir = os.path.join(LOGS_BASE, run_id)
    files = sorted(glob.glob(os.path.join(run_dir, "rule-*.log")))
    results = [_parse_rule_log(p) for p in files]
    results.sort(key=lambda x: x["rule_index"])
    return results

def _read_rule_file(run_id: str, rule_index: int) -> str:
    run_dir = os.path.join(LOGS_BASE, run_id)
    patt1 = os.path.join(run_dir, f"rule-{rule_index:03d}_*.log")
    patt2 = os.path.join(run_dir, f"rule-{rule_index}_*.log")
    matches = glob.glob(patt1) or glob.glob(patt2)
    if not matches:
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