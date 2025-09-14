#sercurity_app/xml_parser.py
import xml.etree.ElementTree as ET

from .schema import REQ_FIELDS
from security_app.models import Rule

# Với XML (XCCDF), có cả attribute và element; ta khai nhiều ứng viên
XML_ATTR_CANDIDATES = {
    "id":       ["id", "rule-id"],
    "severity": ["severity", "impact"],
    "title":    ["title", "name"],  # attribute (ít gặp), fallback element bên dưới
    "name":     ["name"],
}

# Ứng viên element theo tag (trong namespace xccdf)
XML_ELEM_CANDIDATES = {
    "title":       ["title"],  # <xccdf:title>
    "description": ["description", "rationale", "discussion", "front-matter"],
}

# Ứng viên XPATH để lôi nội dung check / fix
XML_CHECK_XPATHS = [
    ".//xccdf:check-content",
    ".//xccdf:check/xccdf:check-content",
    ".//xccdf:check-content-ref",
    ".//xccdf:check/xccdf:check-content-ref",
]
XML_FIX_XPATHS = [
    ".//xccdf:fixtext",
    ".//xccdf:fix",
]

def _first_attr(elem, names):
    for n in names:
        v = elem.get(n)
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""

def _first_elem_text(elem, tag_names, ns):
    for t in tag_names:
        v = elem.findtext(f"xccdf:{t}", default="", namespaces=ns)
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""

def _first_xpath_text(elem, xpaths, ns):
    for xp in xpaths:
        v = elem.findtext(xp, default="", namespaces=ns)
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""

def parse_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {"xccdf": "http://checklists.nist.gov/xccdf/1.1"}

    rules: list[Rule] = []
    for rule in root.findall(".//xccdf:Rule", ns):
        rid   = _first_attr(rule, XML_ATTR_CANDIDATES["id"])
        desc  = _first_elem_text(rule, XML_ELEM_CANDIDATES["description"], ns)
        check = _first_xpath_text(rule, XML_CHECK_XPATHS, ns)
        fix   = _first_xpath_text(rule, XML_FIX_XPATHS, ns)
        sev   = (_first_attr(rule, XML_ATTR_CANDIDATES["severity"]) or "").lower()

            # title: ưu tiên attr (nếu có), fallback element <title>
        title_attr  = _first_attr(rule, XML_ATTR_CANDIDATES["title"])
        title_elem  = _first_elem_text(rule, XML_ELEM_CANDIDATES["title"], ns)
        title_name  = _first_attr(rule, XML_ATTR_CANDIDATES["name"])
        title = title_attr or title_elem or title_name or ""

        # validate
        missing = [f for f, v in [("id", rid), ("description", desc), ("check", check), ("fix", fix), ("severity", sev)] if not v]
        if missing:
            raise Exception(f"Missing required field(s) {missing} in XML rule ID={rid or '(unknown)'}")
        
        rules.append(Rule(id=rid, description=desc, check=check, fix=fix, severity=sev, title=title))
    return rules

