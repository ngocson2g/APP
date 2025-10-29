# tests/test_models.py
import pytest
from types import SimpleNamespace # For testing object with attributes
from security_app.models import Rule, CmdResult, RuleLogRecord, Settings, as_rule

# --- Test dataclasses (basic instantiation is often enough) ---

def test_rule_instantiation():
    """Test basic Rule creation."""
    rule = Rule(id="R1", description="Desc", check="$ cmd", fix="Fix", severity="high", title="Title", assessment_status="manual")
    assert rule.id == "R1"
    assert rule.description == "Desc"
    assert rule.check == "$ cmd"
    assert rule.fix == "Fix"
    assert rule.severity == "high"
    assert rule.title == "Title"
    assert rule.assessment_status == "manual"

def test_cmd_result_instantiation():
    """Test basic CmdResult creation."""
    res = CmdResult(cmd="$ ls", returncode=0, stdout="out", stderr="", duration_sec=0.1, ok=True)
    assert res.cmd == "$ ls"
    assert res.ok is True
    assert res.duration_sec == 0.1

def test_rule_log_record_instantiation():
    """Test basic RuleLogRecord creation."""
    cmds = [CmdResult(cmd="$ ls", returncode=0, stdout="out", stderr="", duration_sec=0.1, ok=True)]
    rec = RuleLogRecord(index=1, rule_id="R1", title="Title", severity="low", check_masked="$ ls #masked", cmds=cmds)
    assert rec.index == 1
    assert rec.rule_id == "R1"
    assert rec.check_masked == "$ ls #masked"
    assert rec.cmds == cmds

def test_settings_instantiation():
    """Test basic Settings creation."""
    s = Settings(shell_timeout=15.0, retry_attempts=2, retry_delay_sec=0.5, retry_on_timeout=True, exec_cwd="/tmp", clean_env=False)
    assert s.shell_timeout == 15.0
    assert s.retry_attempts == 2
    assert s.exec_cwd == "/tmp"
    assert s.clean_env is False

# --- Test as_rule function ---

def test_as_rule_with_rule_input():
    """Test as_rule when input is already a Rule."""
    rule_in = Rule(id="R1", description="Desc", check="$ cmd", fix="Fix", severity="high", title="Title", assessment_status="auto")
    rule_out = as_rule(rule_in)
    assert rule_out is rule_in # Should return the same object

def test_as_rule_with_dict_input_basic():
    """Test as_rule with a simple dictionary."""
    dict_in = {
        "id": "R2",
        "description": "Dict Desc",
        "check": "$ cmd2",
        "fix": "Dict Fix",
        "severity": "Medium", # Mixed case
        "title": "Dict Title",
        "assessment_status": "Manual" # Mixed case
    }
    rule_out = as_rule(dict_in)
    assert isinstance(rule_out, Rule)
    assert rule_out.id == "R2"
    assert rule_out.description == "Dict Desc"
    assert rule_out.check == "$ cmd2"
    assert rule_out.fix == "Dict Fix"
    assert rule_out.severity == "medium" # Normalized to lower
    assert rule_out.title == "Dict Title"
    assert rule_out.assessment_status == "manual" # Normalized to lower

def test_as_rule_with_dict_aliases():
    """Test as_rule using alias keys defined in COL_MAP."""
    dict_in = {
        "rule_id": "R3",         # Alias for id
        "discussion": "Alias Desc", # Alias for description
        "checktext": "$ cmd3",   # Alias for check
        "remediation": "Alias Fix", # Alias for fix
        "impact": "Low",         # Alias for severity
        "name": "Alias Title",     # Alias for title
        "status": "NA"            # Alias for assessment_status
    }
    rule_out = as_rule(dict_in)
    assert isinstance(rule_out, Rule)
    assert rule_out.id == "R3"
    assert rule_out.description == "Alias Desc"
    assert rule_out.check == "$ cmd3"
    assert rule_out.fix == "Alias Fix"
    assert rule_out.severity == "low"
    assert rule_out.title == "Alias Title"
    assert rule_out.assessment_status == "na"

def test_as_rule_with_dict_missing_optional():
    """Test as_rule when optional fields (title, desc, fix, status) are missing."""
    dict_in = {
        "id": "R4",
        "check": "$ cmd4",
        "severity": "critical"
        # Missing description, fix, title, assessment_status
    }
    rule_out = as_rule(dict_in)
    assert isinstance(rule_out, Rule)
    assert rule_out.id == "R4"
    assert rule_out.check == "$ cmd4"
    assert rule_out.severity == "critical"
    # Optional fields should default to empty string
    assert rule_out.description == ""
    assert rule_out.fix == ""
    assert rule_out.title == ""
    assert rule_out.assessment_status == ""

def test_as_rule_with_dict_non_string_values():
    """Test as_rule correctly converts non-string values to string."""
    dict_in = {
        "id": 123, # int
        "check": "$ cmd",
        "severity": None, # None
        "description": True, # bool
    }
    rule_out = as_rule(dict_in)
    assert isinstance(rule_out, Rule)
    assert rule_out.id == "123"
    assert rule_out.check == "$ cmd"
    assert rule_out.severity == "" # None becomes empty string, then lower
    assert rule_out.description == "True"
    assert rule_out.fix == ""
    assert rule_out.title == ""
    assert rule_out.assessment_status == ""


def test_as_rule_with_object_input():
    """Test as_rule with an object having attributes."""
    obj_in = SimpleNamespace(
        id="R5-Obj",
        description="Object Desc",
        check="$ cmd_obj",
        fix="Object Fix",
        severity="High", # Mixed case
        title="Object Title",
        assessment_status="Auto" # Mixed case
        # extra_attr="should be ignored"
    )
    rule_out = as_rule(obj_in)
    assert isinstance(rule_out, Rule)
    assert rule_out.id == "R5-Obj"
    assert rule_out.description == "Object Desc"
    assert rule_out.check == "$ cmd_obj"
    assert rule_out.fix == "Object Fix"
    assert rule_out.severity == "high" # Normalized
    assert rule_out.title == "Object Title"
    assert rule_out.assessment_status == "auto" # Normalized

def test_as_rule_with_object_missing_optional():
    """Test as_rule with an object missing optional attributes."""
    obj_in = SimpleNamespace(
        id="R6-Obj",
        check="$ cmd_obj_missing",
        severity="low"
        # Missing description, fix, title, assessment_status
    )
    rule_out = as_rule(obj_in)
    assert isinstance(rule_out, Rule)
    assert rule_out.id == "R6-Obj"
    assert rule_out.check == "$ cmd_obj_missing"
    assert rule_out.severity == "low"
    assert rule_out.description == ""
    assert rule_out.fix == ""
    assert rule_out.title == ""
    assert rule_out.assessment_status == ""

def test_as_rule_empty_input():
    """Test as_rule with empty dict or object."""
    empty_dict = {}
    rule_out_dict = as_rule(empty_dict)
    assert isinstance(rule_out_dict, Rule)
    assert rule_out_dict.id == ""
    assert rule_out_dict.check == "" # Note: check is required by schema, but as_rule handles missing gracefully
    assert rule_out_dict.severity == ""

    empty_obj = SimpleNamespace()
    rule_out_obj = as_rule(empty_obj)
    assert isinstance(rule_out_obj, Rule)
    assert rule_out_obj.id == ""
    assert rule_out_obj.check == ""
    assert rule_out_obj.severity == ""
