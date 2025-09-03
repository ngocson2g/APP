#security_app/parser/json_parser.py
import json

from security_app.models import Rule
from security_app.parsers.schema import COL_MAP, REQ_FIELDS


def _lower_keys(d: dict):
    return {str(k).strip().lower(): v for k, v in d.items()}

def _get_first(d: dict, aliases):
    for k in aliases:
        if k in d and isinstance(d[k], str) and d[k].strip():
            return d[k].strip()
    return ""

def _looks_like_rule(obj: dict) -> bool:
    if not isinstance(obj, dict):
        return False
    keys = {str(k).strip().lower() for k in obj}
    def has_any(aliases): return any(a in keys for a in aliases)
    return has_any(COL_MAP["id"]) and has_any(COL_MAP["severity"]) and (
        has_any(COL_MAP["check"]) or has_any(COL_MAP["description"])
    )

def _extract_items(data):
    """
    Trả về list các item rule từ nhiều cấu trúc JSON khác nhau:
    - list trực tiếp
    - dict với stig.findings (dict hoặc list)
    - dict với findings/rules/items (dict hoặc list)
    - dict id->rule (tất cả value là dict có hình dáng rule)
    """
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        candidates = []
        stig = data.get("stig")
        if isinstance(stig, dict):
            candidates.append(stig.get("findings"))
        candidates += [data.get("findings"), data.get("rules"), data.get("items")]

        for c in candidates:
            if isinstance(c, list):
                return c
            if isinstance(c, dict):
                return list(c.values())

        if data and all(isinstance(v, dict) for v in data.values()):
            vals = list(data.values())
            if any(_looks_like_rule(v) for v in vals):
                return vals
    return None

def parse_json(path: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    items = _extract_items(data)
    if items is None:
        raise Exception("JSON format not supported: couldn't locate list/dict of findings/rules")

    rules: list[Rule] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        r = _lower_keys(raw)

        rid   = _get_first(r, COL_MAP["id"])
        desc  = _get_first(r, COL_MAP["description"])
        check = _get_first(r, COL_MAP["check"])
        fix   = _get_first(r, COL_MAP["fix"])
        sev   = (_get_first(r, COL_MAP["severity"]) or "").lower()
        title = _get_first(r, COL_MAP.get("title", [])) or _get_first(r, COL_MAP.get("name", []))

        vals = {"id": rid, "description": desc, "check": check, "fix": fix, "severity": sev}
        missing = [f for f in REQ_FIELDS if not vals.get(f)]
        if missing:
            tentative = r.get("id") or rid or "(unknown)"
            raise Exception(f"Missing {missing} in JSON item ID={tentative}")

        rules.append(Rule(
            id=rid, description=desc, check=check, fix=fix, severity=sev, title=title or ""
        ))
    return rules

