import json

def parse_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    findings = data['stig']['findings']
    # findings là dict, cần chuyển sang list các dict
    rules_list = []
    col_map = {
        'id': 'id',
        'description': 'description',
        'check': 'checktext',
        'fix': 'fixtext',
        'severity': 'severity'
    }
    for rule_id, rule in findings.items():
        # Map các trường chuẩn, thiếu thì trả về ''
        rule_item = {k: str(rule.get(v, '')) for k, v in col_map.items()}
        rules_list.append(rule_item)
    return rules_list

