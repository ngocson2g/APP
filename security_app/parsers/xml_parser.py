import xml.etree.ElementTree as ET
from security_app.models import Rule

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'xccdf': 'http://checklists.nist.gov/xccdf/1.1'}

    rules: list[Rule] = []
    for rule in root.findall('.//xccdf:Rule', ns):
        rid   = rule.get('id', '')
        desc  = rule.findtext('xccdf:description', default='', namespaces=ns)
        check = rule.findtext('.//xccdf:check-content', default='', namespaces=ns)
        fix   = rule.findtext('.//xccdf:fixtext', default='', namespaces=ns)
        sev   = (rule.get('severity', '') or '').lower()
        title = rule.get('title') or rule.get('name') or ''
        rules.append(Rule(id=rid, description=desc, check=check, fix=fix, severity=sev, title=title))
    return rules
