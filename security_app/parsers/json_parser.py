import json
from security_app.models import Rule

COL_MAP = {
    'id': 'id',
    'description': 'description',
    'check': 'checktext',
    'fix': 'fixtext',
    'severity': 'severity',
    'title': 'title',
    'name': 'name',
}

REQ_FIELDS = ['id', 'description', 'check', 'fix', 'severity']

def parse_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    findings = data.get('stig', {}).get('findings', {})
    if not isinstance(findings, dict):
        raise Exception("Invalid JSON structure: expected dict at stig.findings")
    
    rules: list[Rule] = []
    for _, r in findings.items():
        get = lambda key: str(r.get(COL_MAP[key], '') or '') if key in COL_MAP else ""
        title = r.get(COL_MAP['title']) or r.get(COL_MAP['name']) or ""

        # validate
        for field in REQ_FIELDS:
            if not get(field):
                raise Exception(f"Missing field: {field} in JSON item ID={r.get('id')}")

        rules.append(Rule(
            id=get('id'),
            description=get('description'),
            check=get('check'),
            fix=get('fix'),
            severity=get('severity').lower(),
            title=str(title),
        ))
    return rules
