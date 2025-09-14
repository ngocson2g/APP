# security_app/parsers/schema.py
"""
Schema alias dùng chung cho CSV/JSON.
Lưu ý: các parser sẽ normalize tên cột/khóa về lowercase trước khi tra cứu.
"""

# Field chuẩn -> danh sách alias (lowercase)
COL_MAP = {
    "id": [
        "id", "rule_id", "vuln_id", "vulnid", "vuln-id",
        "control", "control_id", "cci", "ref_id", "vuln_num",
    ],
    "description": [
        "description", "desc", "discussion", "rationale", "summary", "details",
    ],
    "check": [
        "checktext", "check_text", "check", "check-content", "check_content",
        "command", "commands", "audit", "audit_procedure",
    ],
    "fix": [
        "fixtext", "fix_text", "fix", "remediation", "solution",
    ],
    "severity": [
        "severity", "sev", "impact", "level",
    ],
    # không bắt buộc – phục vụ hiển thị
    "title": ["title", "rule_title", "name"],
    "name":  ["name", "title"],
}

# Trường bắt buộc phải có dữ liệu
REQ_FIELDS = ["id", "description", "check"]

