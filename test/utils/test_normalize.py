# tests/utils/test_normalize.py
import pytest
from security_app.utils.normalize import normalize_command, _strip_comments_outside_quotes, _collapse_ws_outside_quotes

# --- Test normalize_command (Ví dụ đã có) ---
@pytest.mark.parametrize("input_cmd, expected_output", [
    ("ls -l # List files", "ls -l"),
    ("echo 'hello world'  ", "echo 'hello world'"),
    ("cmd1 && cmd2 ; ", "cmd1 && cmd2"),
    ("echo '  spaces  ' # comment", "echo '  spaces  '"),
    ("grep '#important' file", "grep '#important' file"),
    ("cmd multi\\\nline", "cmd multiline"),
    ("", ""),
    ("cmd #comment \n next line", "cmd next line"), # Test comment và newline
    ("cmd \\# not a comment", "cmd \\# not a comment"), # Test escaped hash
])
def test_normalize_command(input_cmd, expected_output):
    assert normalize_command(input_cmd) == expected_output

# --- Có thể test các hàm helper nếu cần ---
def test_strip_comments_simple():
    assert _strip_comments_outside_quotes("command # ignore this") == "command "

def test_strip_comments_in_quotes():
    assert _strip_comments_outside_quotes("echo 'value # not comment'") == "echo 'value # not comment'"

def test_collapse_ws():
    assert _collapse_ws_outside_quotes("cmd  arg1 \n arg2\targ3") == "cmd arg1 arg2 arg3"

def test_collapse_ws_in_quotes():
    assert _collapse_ws_outside_quotes("echo '  keep \n spaces '") == "echo '  keep \n spaces '"
