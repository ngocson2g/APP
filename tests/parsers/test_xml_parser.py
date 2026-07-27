# tests/parsers/test_xml_parser.py
import pytest
from pathlib import Path
import xml.etree.ElementTree as ET
from security_app.models import Rule
from security_app.parsers.xml_parser import parse_xml

# --- XML Fixtures ---

@pytest.fixture
def xml_valid_xccdf12(tmp_path: Path) -> Path:
    """Valid XCCDF 1.2 format."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<Benchmark xmlns="http://checklists.nist.gov/xccdf/1.2" id="test_bench">
  <status>incomplete</status>
  <title>Test Benchmark</title>
  <Rule id="R-XML-001" severity="high">
    <title>Rule One Title</title>
    <description>Description for rule one.</description>
    <check system="http://oval.mitre.org/XMLSchema/oval-definitions-5">
      <check-content-ref name="oval:org.example:def:1" href="oval_def1.xml"/>
    </check>
    <fixtext>Fix instructions 1.</fixtext>
  </Rule>
  <Rule id="R-XML-002" severity="medium">
    <title>Rule Two Title</title>
    <rationale>Rationale for rule two.</rationale>
    <check system="urn:xccdf:check:script">
       <check-content>$ echo "hello world"\n$ ls -l</check-content>
    </check>
    <fix>Fix instructions 2.</fix>
  </Rule>
</Benchmark>
"""
    p = tmp_path / "valid_xccdf12.xml"
    p.write_text(content, encoding="utf-8")
    return p

@pytest.fixture
def xml_valid_xccdf11_alt_ns(tmp_path: Path) -> Path:
    """Valid XCCDF 1.1 format with alternative namespace prefix."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<x:Benchmark xmlns:x="http://checklists.nist.gov/xccdf/1.1" id="test_bench11">
  <x:status>incomplete</x:status>
  <x:title>Test Benchmark 1.1</x:title>
  <x:Rule id="R-XML11-001" impact="low"> <x:title>Rule 1.1 Title</x:title>
    <x:check>
       <x:check-content>$ pwd</x:check-content>
    </x:check>
  </x:Rule>
</x:Benchmark>
"""
    p = tmp_path / "valid_xccdf11.xml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def xml_missing_id(tmp_path: Path) -> Path:
    """XML missing the required 'id' attribute on Rule."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<Benchmark xmlns="http://checklists.nist.gov/xccdf/1.2" id="test_bench">
  <Rule severity="high"> <title>Rule One Title</title>
    <check><check-content>$ cmd</check-content></check>
  </Rule>
</Benchmark>
"""
    p = tmp_path / "missing_id.xml"
    p.write_text(content, encoding="utf-8")
    return p

@pytest.fixture
def xml_missing_check(tmp_path: Path) -> Path:
    """XML missing the required 'check' element/content."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<Benchmark xmlns="http://checklists.nist.gov/xccdf/1.2" id="test_bench">
  <Rule id="R-MISS-CHECK" severity="high">
    <title>Rule One Title</title>
    </Rule>
</Benchmark>
"""
    p = tmp_path / "missing_check.xml"
    p.write_text(content, encoding="utf-8")
    return p

@pytest.fixture
def xml_invalid_syntax(tmp_path: Path) -> Path:
    """Invalid XML syntax."""
    p = tmp_path / "invalid_syntax.xml"
    p.write_text("<Benchmark><Rule id='R1' severity='high'><title>T1</title></Rule", encoding="utf-8") # Missing closing tag
    return p

# --- Test Functions ---

def test_parse_xml_valid_xccdf12(xml_valid_xccdf12: Path):
    """Test parsing valid XCCDF 1.2."""
    rules = parse_xml(str(xml_valid_xccdf12))
    assert len(rules) == 2
    assert isinstance(rules[0], Rule)
    # Rule 1 (uses check-content-ref)
    assert rules[0].id == "R-XML-001"
    assert rules[0].severity == "high"
    assert rules[0].title == "Rule One Title"
    assert rules[0].description == "Description for rule one."
    assert rules[0].fix == "Fix instructions 1."
    assert rules[0].check == "oval:org.example:def:1" # Extracted name attribute

    # Rule 2 (uses check-content)
    assert rules[1].id == "R-XML-002"
    assert rules[1].severity == "medium"
    assert rules[1].title == "Rule Two Title"
    assert rules[1].description == "Rationale for rule two." # check description alias
    assert rules[1].fix == "Fix instructions 2." # check fix alias
    assert rules[1].check == '$ echo "hello world"\n$ ls -l'

def test_parse_xml_valid_xccdf11(xml_valid_xccdf11_alt_ns: Path):
    """Test parsing valid XCCDF 1.1 with different namespace."""
    rules = parse_xml(str(xml_valid_xccdf11_alt_ns))
    assert len(rules) == 1
    assert rules[0].id == "R-XML11-001"
    assert rules[0].severity == "low" # Normalized from impact
    assert rules[0].title == "Rule 1.1 Title"
    assert rules[0].check == "$ pwd"
    assert rules[0].description == "" # No description element
    assert rules[0].fix == "" # No fix element

def test_parse_xml_missing_id(xml_missing_id: Path):
    """Test error when required 'id' is missing."""
    with pytest.raises(Exception, match=r"Missing required field\(s\) \['id'\] in XML rule ID=\(unknown\)"):
        parse_xml(str(xml_missing_id))

def test_parse_xml_missing_check(xml_missing_check: Path):
    """Test error when required 'check' is missing."""
    with pytest.raises(Exception, match=r"Missing required field\(s\) \['check'\] in XML rule ID=R-MISS-CHECK"):
        parse_xml(str(xml_missing_check))

def test_parse_xml_invalid_syntax(xml_invalid_syntax: Path):
    """Test error for invalid XML syntax."""
    with pytest.raises(ET.ParseError):
        parse_xml(str(xml_invalid_syntax))

def test_parse_xml_empty_file(tmp_path: Path):
    """Test handling of empty or non-XML file."""
    p = tmp_path / "empty.xml"
    p.touch()
    with pytest.raises(ET.ParseError): # Expect parse error for empty file
        parse_xml(str(p))

    p_txt = tmp_path / "not_xml.txt"
    p_txt.write_text("this is not xml")
    with pytest.raises(ET.ParseError): # Expect parse error for non-xml
        parse_xml(str(p_txt))
