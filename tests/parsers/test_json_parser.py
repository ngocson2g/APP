# tests/parsers/test_json_parser.py
import pytest
import json
from pathlib import Path
from security_app.models import Rule
from security_app.parsers.json_parser import parse_json, _looks_like_rule, _extract_items

# --- Helper Tests ---

def test_looks_like_rule_positive():
    assert _looks_like_rule({"id": "R1", "severity": "high", "check": "$ cmd"}) is True
    assert _looks_like_rule({"rule_id": "R2", "impact": "medium", "description": "desc"}) is True # Check/Desc is enough
    assert _looks_like_rule({"vulnid": "V3", "level": "low", "audit": "$ cmd"}) is True

def test_looks_like_rule_negative():
    assert _looks_like_rule({"name": "Something", "value": 1}) is False
    assert _looks_like_rule({}) is False
    assert _looks_like_rule([]) is False
    assert _looks_like_rule("not a dict") is False
    assert _looks_like_rule({"id": "R1"}) is False # Missing severity and check/desc

def test_extract_items_direct_list():
    data = [{"id": "R1"}, {"id": "R2"}]
    assert _extract_items(data) == data

def test_extract_items_dict_findings_list():
    data = {"findings": [{"id": "R1"}, {"id": "R2"}]}
    assert _extract_items(data) == data["findings"]

def test_extract_items_dict_stig_findings_dict():
    data = {"stig": {"findings": {"R1": {"severity": "high"}, "R2": {"severity": "low"}}}}
    assert _extract_items(data) == [{"severity": "high"}, {"severity": "low"}]

def test_extract_items_dict_rules_dict_values():
    data = {"rules": {"R1": {"id": "R1", "severity": "high", "check":"$ c"}, "R2": {"id": "R2", "severity": "low", "check":"$ c"}}}
    assert _extract_items(data) == list(data["rules"].values())

def test_extract_items_not_found():
     assert _extract_items({"other": "data"}) is None
     assert _extract_items({}) is None
     assert _extract_items({"findings": "not a list or dict"}) is None


# --- Main Parser Tests ---

@pytest.fixture
def json_valid_list(tmp_path: Path) -> Path:
    """Valid JSON as a list of rules."""
    content = [
        {"id": "RULE-JSON-001", "description": "Desc 1", "check": "$ cmd1", "fix": "Fix 1", "severity": "high", "title": "Title 1"},
        {"rule_id": "RULE-JSON-002", "desc": "Desc 2", "check_text": "$ cmd2\n$ cmd3", "fixtext": "Fix 2", "impact": "Medium", "name": "Title 2"}
    ]
    p = tmp_path / "valid_list.json"
    p.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return p

@pytest.fixture
def json_valid_dict_findings(tmp_path: Path) -> Path:
    """Valid JSON as a dict with a 'findings' list."""
    content = {
        "metadata": {},
        "findings": [
             {"id": "RULE-DICT-001", "check": "$ cmd1", "severity": "low"}
        ]
    }
    p = tmp_path / "valid_dict.json"
    p.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return p

@pytest.fixture
def json_missing_check(tmp_path: Path) -> Path:
    """JSON missing the required 'check' field."""
    content = [{"id": "RULE-MISS-001", "severity": "low"}]
    p = tmp_path / "missing_check.json"
    p.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return p

@pytest.fixture
def json_invalid_syntax(tmp_path: Path) -> Path:
    """Invalid JSON syntax."""
    p = tmp_path / "invalid_syntax.json"
    p.write_text("[{'id': 'bad json',}]", encoding="utf-8") # Single quotes, trailing comma
    return p

@pytest.fixture
def json_unsupported_format(tmp_path: Path) -> Path:
    """Valid JSON but cannot find rules list/dict."""
    content = {"config": {"key": "value"}, "other_list": [1, 2, 3]}
    p = tmp_path / "unsupported.json"
    p.write_text(json.dumps(content, indent=2), encoding="utf-8")
    return p

def test_parse_json_valid_list(json_valid_list: Path):
    """Test parsing a valid JSON list."""
    rules = parse_json(str(json_valid_list))
    assert len(rules) == 2
    assert isinstance(rules[0], Rule)
    assert rules[0].id == "RULE-JSON-001"
    assert rules[0].severity == "high"
    assert rules[0].title == "Title 1"
    assert rules[0].check == "$ cmd1"
    assert rules[1].id == "RULE-JSON-002"
    assert rules[1].severity == "medium" # Normalized to lower
    assert rules[1].title == "Title 2"
    assert rules[1].check == "$ cmd2\n$ cmd3"

def test_parse_json_valid_dict(json_valid_dict_findings: Path):
    """Test parsing a valid JSON dict with 'findings'."""
    rules = parse_json(str(json_valid_dict_findings))
    assert len(rules) == 1
    assert rules[0].id == "RULE-DICT-001"
    assert rules[0].severity == "low"
    assert rules[0].check == "$ cmd1"
    # Fields not present should be empty strings
    assert rules[0].title == ""
    assert rules[0].description == ""
    assert rules[0].fix == ""

def test_parse_json_missing_required_field(json_missing_check: Path):
    """Test error when required 'check' field is missing."""
    with pytest.raises(Exception, match=r"Missing \['check'\] in JSON item ID=RULE-MISS-001"):
        parse_json(str(json_missing_check))

def test_parse_json_invalid_syntax(json_invalid_syntax: Path):
    """Test error for invalid JSON syntax."""
    with pytest.raises(json.JSONDecodeError):
        parse_json(str(json_invalid_syntax))

def test_parse_json_unsupported_format(json_unsupported_format: Path):
    """Test error when the JSON structure is not recognized."""
    with pytest.raises(Exception, match="JSON format not supported"):
        parse_json(str(json_unsupported_format))

def test_parse_json_non_dict_in_list(tmp_path: Path):
    """Test skipping non-dict items in a list."""
    content = [{"id": "R1", "check":"$c", "severity":"low"}, "string_item", None, {"id": "R2", "check":"$c", "severity":"high"}]
    p = tmp_path / "mixed_list.json"
    p.write_text(json.dumps(content, indent=2), encoding="utf-8")
    rules = parse_json(str(p))
    assert len(rules) == 2
    assert rules[0].id == "R1"
    assert rules[1].id == "R2"
