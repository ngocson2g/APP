# security_app/parsers/xml_parser.py
from __future__ import annotations

import xml.etree.ElementTree as ET

from security_app.models import Rule

from .schema import REQ_FIELDS

# Ứng viên attribute trên <Rule>
XML_ATTR_CANDIDATES = {
    "id":       ["id", "rule-id"],
    "severity": ["severity", "impact"],
    "title":    ["title", "name"],  # attribute (ít gặp)
    "name":     ["name"],
}

# Ứng viên element theo tag (trong namespace xccdf)
XML_ELEM_CANDIDATES = {
    "title":       ["title"],  # <xccdf:title>
    "description": ["description", "rationale", "discussion", "front-matter"],
}

# Ứng viên XPATH để lôi nội dung check / fix
XML_CHECK_XPATHS_TEXT = [
    ".//xccdf:check-content",
    ".//xccdf:check/xccdf:check-content",
]
XML_CHECK_XPATHS_REF = [
    ".//xccdf:check-content-ref",
    ".//xccdf:check/xccdf:check-content-ref",
]
XML_FIX_XPATHS = [
    ".//xccdf:fixtext",
    ".//xccdf:fix",
]


def _first_attr(elem: ET.Element, names) -> str:
    for n in names:
        v = elem.get(n)
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""


def _first_elem_text(elem: ET.Element, tag_names, ns) -> str:
    for t in tag_names:
        v = elem.findtext(f"xccdf:{t}", default="", namespaces=ns)
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""


def _first_xpath_text(elem: ET.Element, xpaths, ns) -> str:
    for xp in xpaths:
        v = elem.findtext(xp, default="", namespaces=ns)
        if v:
            v = str(v).strip()
            if v:
                return v
    return ""


def _first_xpath_attr_or_text(elem: ET.Element, xpaths, ns, attr_names=("name", "href")) -> str:
    """
    Trả về text nếu có; nếu trống thì thử lấy từ attribute (name/href).
    Hữu ích cho check-content-ref (OVAL).
    """
    for xp in xpaths:
        node = elem.find(xp, ns)
        if node is not None:
            txt = (node.text or "").strip()
            if txt:
                return txt
            for an in attr_names:
                val = (node.get(an) or "").strip()
                if val:
                    return val
    return ""


def parse_xml(file_path: str) -> list[Rule]:
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Tự phát hiện namespace XCCDF (1.1/1.2)
    if root.tag.startswith("{"):
        ns_url = root.tag.split("}")[0][1:]
    else:
        ns_url = "http://checklists.nist.gov/xccdf/1.2"  # default an toàn
    ns = {"xccdf": ns_url}

    rules: list[Rule] = []
    for rule in root.findall(".//xccdf:Rule", ns):
        # id & tiêu đề
        rid = _first_attr(rule, XML_ATTR_CANDIDATES["id"])
        title_attr = _first_attr(rule, XML_ATTR_CANDIDATES["title"])
        title_elem = _first_elem_text(rule, XML_ELEM_CANDIDATES["title"], ns)
        title_name = _first_attr(rule, XML_ATTR_CANDIDATES["name"])
        title = title_attr or title_elem or title_name or ""

        # mô tả / fix / severity (đều optional)
        desc = _first_elem_text(rule, XML_ELEM_CANDIDATES["description"], ns) or ""
        fix = _first_xpath_text(rule, XML_FIX_XPATHS, ns) or ""
        sev = (_first_attr(rule, XML_ATTR_CANDIDATES["severity"]) or "").strip().lower() or "unknown"

        # check: ưu tiên check-content (text), fallback sang check-content-ref (text/name/href)
        check = _first_xpath_text(rule, XML_CHECK_XPATHS_TEXT, ns)
        if not check:
            check = _first_xpath_attr_or_text(rule, XML_CHECK_XPATHS_REF, ns)

        # Validate theo hợp đồng tối thiểu
        missing = [k for k in REQ_FIELDS if (k == "id" and not rid) or (k == "check" and not check)]
        if missing:
            raise Exception(f"Missing required field(s) {missing} in XML rule ID={rid or '(unknown)'}")

        rules.append(
            Rule(
                id=rid,
                title=title,
                description=desc,
                check=check,
                fix=fix,
                severity=sev,
            )
        )

    return rules
