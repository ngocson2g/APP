import json
from security_app.models import Rule

# Field chuẩn -> danh sách key có thể có trong từng item JSON (đã lowercase khi so sánh logic)
COL_MAP = {
    "id": [
        "id", "rule_id", "vuln_id", "vulnid", "vuln-id", "control", "control_id", "cci", "ref_id"
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
    "name": [
        "name", "rule_name"
    ],
}

REQ_FIELDS = ['id', 'description', 'check', 'fix', 'severity']

def _get_first(d: dict, candidates: list[str]) -> str:
    # tìm khóa theo dạng "case-insensitive"
    # không ép biến thể nested; kỳ vọng item là phẳng như đầu vào STIG JSON của bạn
    lower_map = {str(k).lower(): k for k in d.keys()}
    for c in candidates:
        key = lower_map.get(c.lower())
        if key is not None:
            val = d.get(key, "")
            if val is None:
                continue
            sval = str(val).strip()
            if sval:
                return sval
    return ""

def parse_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    findings = data.get('stig', {}).get('findings', {})
    if not isinstance(findings, dict):
        raise Exception("Invalid JSON structure: expected dict at stig.findings")
    
    rules: list[Rule] = []
    for _, r in findings.items():
        rid   = _get_first(r, COL_MAP["id"])
        desc  = _get_first(r, COL_MAP["description"])
        check = _get_first(r, COL_MAP["check"])
        fix   = _get_first(r, COL_MAP["fix"])
        sev   = _get_first(r, COL_MAP["severity"]).lower()
        title = _get_first(r, COL_MAP["title"]) or _get_first(r, COL_MAP["name"])

        # validate
        missing = [f for f, v in [("id", rid), ("description", desc), ("check", check), ("fix", fix), ("severity", sev)] if not v]
        if missing:
            tentative = r.get("id") or rid or "(unknown)"
            raise Exception(f"Missing field(s) {missing} in JSON item ID={tentative}")

        rules.append(Rule(
            id=rid,
            description=desc,
            check=check,
            fix=fix,
            severity=sev,
            title=title or "",
        ))
    return rules
