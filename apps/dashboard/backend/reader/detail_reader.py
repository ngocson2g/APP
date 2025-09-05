# apps/dashboard/backend/reader/detail_reader.py
import re, os
from typing import Dict, Any
from .rule_reader import _read_rule_file
from .config import _RC_OK_LINE, _ID_LINE, _TITLE_LINE, _SEV_LINE, _CMD_LINE

def get_rule_detail(run_id: str, rule_index: int) -> Dict[str, Any]:
    path = _read_rule_file(run_id, rule_index)

    rid = title = sev = ""
    check_lines, commands = [], []
    in_check = in_cmds = False
    cur = None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip("\n")
            m = _ID_LINE.match(line);     
            if m: rid = m.group(1).strip();           continue
            m = _TITLE_LINE.match(line);  
            if m: title = (m.group(1) or "").strip(); continue
            m = _SEV_LINE.match(line);    
            if m: sev = (m.group(1) or "").strip().lower(); continue

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