import pandas as pd
from security_app.models import Rule
from security_app.parsers.schema import COL_MAP, REQ_FIELDS

def _normalize_columns(cols):
    # về lowercase, thay khoảng trắng/dấu gạch thành underscore để ổn định tra cứu
    return [str(c).strip().lower().replace("-", "_").replace(" ", "_") for c in cols]

def _pick_first(row, aliases):
    for k in aliases:
        if k in row and pd.notnull(row[k]) and str(row[k]).strip():
            return str(row[k]).strip()
    return ""

def parse_csv(path: str):
    df = pd.read_csv(path, dtype=str)
    df.columns = _normalize_columns(df.columns)

    rules: list[Rule] = []
    for _, r in df.iterrows():
        rid   = _pick_first(r, COL_MAP["id"])
        desc  = _pick_first(r, COL_MAP["description"])
        check = _pick_first(r, COL_MAP["check"])
        fix   = _pick_first(r, COL_MAP["fix"])
        sev   = (_pick_first(r, COL_MAP["severity"]) or "").lower()
        title = _pick_first(r, COL_MAP.get("title", [])) or _pick_first(r, COL_MAP.get("name", []))

        # validate theo REQ_FIELDS
        vals = {"id": rid, "description": desc, "check": check, "fix": fix, "severity": sev}
        missing = [f for f in REQ_FIELDS if not vals.get(f)]
        if missing:
            raise Exception(f"Missing {missing} in CSV row (tentative id={rid or '(unknown)'})")

        rules.append(Rule(
            id=rid, description=desc, check=check, fix=fix, severity=sev, title=title or ""
        ))
    return rules
