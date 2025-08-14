import pandas as pd
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

def parse_csv(file_path):
    df = pd.read_csv(file_path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]

    rules: list[Rule] = []
    for _, row in df.iterrows():
        get = lambda k: str(row[k]) if k in row and pd.notnull(row[k]) else ""
        title = ""
        if COL_MAP['title'] in df.columns and get(COL_MAP['title']):
            title = get(COL_MAP['title'])
        elif COL_MAP['name'] in df.columns and get(COL_MAP['name']):
            title = get(COL_MAP['name'])

        rules.append(Rule(
            id=get(COL_MAP['id']),
            description=get(COL_MAP['description']),
            check=get(COL_MAP['check']),
            fix=get(COL_MAP['fix']),
            severity=get(COL_MAP['severity']).lower(),
            title=title,
        ))
    return rules
