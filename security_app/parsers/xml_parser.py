import xml.etree.ElementTree as ET
from security_app.models import Rule

COL_MAP = {
    'id': 'id',
    'description': 'description',
    'check': 'check-content',
    'fix': 'fixtext',
    'severity': 'severity',
    'title': 'title',
    'name': 'name',
}

REQ_FIELDS = ['id', 'description', 'check', 'fix', 'severity']

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'xccdf': 'http://checklists.nist.gov/xccdf/1.1'}

    rules: list[Rule] = []
    for rule in root.findall('.//xccdf:Rule', ns):
        rid   = rule.get(COL_MAP['id'], '')
        desc  = rule.findtext(f"xccdf:{COL_MAP['description']}", default='', namespaces=ns)
        check = rule.findtext(f".//xccdf:{COL_MAP['check']}", default='', namespaces=ns)
        fix   = rule.findtext(f".//xccdf:{COL_MAP['fix']}", default='', namespaces=ns)
        sev   = (rule.get(COL_MAP['severity'], '') or '').lower()
        title = rule.get(COL_MAP['title']) or rule.get(COL_MAP['name']) or ''

        # validate
        if not all([rid, desc, check, fix, sev]):
            raise Exception(f"Missing required field in XML rule ID={rid}")
        
        rules.append(Rule(id=rid, description=desc, check=check, fix=fix, severity=sev, title=title))
    return rules
