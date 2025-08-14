import json
from security_app.models import Rule

def parse_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    findings = data['stig']['findings']  # dict[id] -> rule_obj
    rules: list[Rule] = []
    for _, r in findings.items():
        rules.append(Rule(
            id=str(r.get('id', '')),
            description=str(r.get('description', '')),
            check=str(r.get('checktext', '')),
            fix=str(r.get('fixtext', '')),
            severity=str(r.get('severity', '')).lower(),
            title=str(r.get('title') or r.get('name') or ''),
        ))
    return rules
