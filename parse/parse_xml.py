import xml.etree.ElementTree as ET

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'xccdf': 'http://checklists.nist.gov/xccdf/1.1'}  # Cập nhật nếu namespace khác
    rules = []
    # Tùy theo format, ví dụ với STIG XCCDF
    for rule in root.findall('.//xccdf:Rule', ns):
        rid = rule.get('id', '')
        desc = rule.findtext('xccdf:description', default='', namespaces=ns)
        check = rule.findtext('.//xccdf:check-content', default='', namespaces=ns)
        fix = rule.findtext('.//xccdf:fixtext', default='', namespaces=ns)
        sev = rule.get('severity', '')
        rules.append({'id': rid, 'description': desc, 'check': check, 'fix': fix, 'severity': sev})
    return rules

