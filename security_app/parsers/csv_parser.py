import pandas as pd
from security_app.models import Rule

def parse_csv(file_path):
    df = pd.read_csv(file_path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    col_map = {
        'id': 'id',
        'description': 'description',
        'check': 'checktext',
        'fix': 'fixtext',
        'severity': 'severity',
        # nếu CSV có tiêu đề riêng
        'title': 'title',
        'name': 'name',
    }
    # validate cột bắt buộc
    for req, real in [('id','id'), ('description','description'),
                      ('check','checktext'), ('fix','fixtext'),
                      ('severity','severity')]:
        if real not in df.columns:
            raise Exception(f"Missing column: {real} (for field {req})")

    rules: list[Rule] = []
    for _, row in df.iterrows():
        get = lambda k: str(row[k]) if k in row and pd.notnull(row[k]) else ""
        title = ""
        if 'title' in df.columns and get('title'):
            title = get('title')
        elif 'name' in df.columns and get('name'):
            title = get('name')

        rules.append(Rule(
            id=get(col_map['id']),
            description=get(col_map['description']),
            check=get(col_map['check']),
            fix=get(col_map['fix']),
            severity=get(col_map['severity']).lower(),
            title=title,
        ))
    return rules
