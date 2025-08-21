import pandas as pd
from security_app.models import Rule
import re

# Mỗi field chuẩn -> danh sách các tên cột có thể gặp trong CSV (đã normalize lowercase)
COL_MAP = {
    "id": [
        "id", "rule_id", "vuln_id", "vulnid", "vuln-id", "vuln_num",
        "control", "control_id", "cci", "ref_id"
    ],
    "description": [
        "description", "desc", "discussion", "rationale", "summary", "details"
    ],
    "check": [
        "checktext", "check_text", "check", "check-content", "check_content",
        "command", "commands", "audit", "audit_procedure"
    ],
    "fix": [
        "fixtext", "fix_text", "fix", "remediation", "solution", "how_to_fix"
    ],
    "severity": [
        "severity", "impact", "risk", "level", "priority"
    ],
    "title": [
        "title", "rule_title", "short_title", "name"
    ],
    # không bắt buộc, chỉ để fallback cho title
    "name": [
        "name", "rule_name"
    ],
}

REQ_FIELDS = ['id', 'description', 'check', 'fix', 'severity']

def _normalize_columns(cols):
    # về lowercase + thay khoảng trắng/dấu gạch nối -> underscore
    return [re.sub(r"[\s\-]+", "_", str(c).strip().lower()) for c in cols]

def _pick_from_row(row, candidates):
    for k in candidates:
        if k in row and pd.notnull(row[k]):
            val = str(row[k]).strip()
            if val:
                return val
    return ""

def parse_csv(file_path):
    df = pd.read_csv(file_path, dtype=str)
    df.columns = _normalize_columns(df.columns)

    rules: list[Rule] = []
    for _, row in df.iterrows():
        rid   = _pick_from_row(row, COL_MAP["id"])
        desc  = _pick_from_row(row, COL_MAP["description"])
        check = _pick_from_row(row, COL_MAP["check"])
        fix   = _pick_from_row(row, COL_MAP["fix"])
        sev   = _pick_from_row(row, COL_MAP["severity"]).lower()
        title = _pick_from_row(row, COL_MAP["title"]) or _pick_from_row(row, COL_MAP["name"])

        # validate required fields
        missing = [f for f, v in [("id", rid), ("description", desc), ("check", check), ("fix", fix), ("severity", sev)] if not v]
        if missing:
            raise Exception(f"Missing required fields {missing} in CSV row with tentative ID={rid or '(unknown)'}")

        rules.append(Rule(
            id=rid,
            description=desc,
            check=check,
            fix=fix,
            severity=sev,
            title=title or ""
        ))
    return rules
