# tests/core/test_command_extractor.py
import pytest
from security_app.core.command_extractor import extract_all_commands

# Giả định CMD_MARKER là "$ "
CMD_MARKER = "$ "

checktext_simple = """
Some description here.
$ ls -l
Output expected.
$ pwd
Another output.
"""

checktext_multiline = """
Check with multiline command.
$ grep 'pattern' file \\
  | sort \\
  | uniq -c
Expected result.
$ another command
"""

checktext_no_commands = """
Just descriptive text.
No commands starting with marker.
"""

checktext_mixed = """
$ first command
Output 1
Description line without marker
$ second command # with comment
$ third command \\
continues
$ fourth
"""

checktext_marker_inside = """
Description with $ marker inside, not a command.
$ actual command
"""

checktext_ends_with_command = """
Some text
$ last command
"""

checktext_ends_with_multiline = """
Some text
$ last multi \\
line command
"""


@pytest.mark.parametrize("checktext, expected_commands", [
    (checktext_simple, ["ls -l", "pwd"]),
    (checktext_multiline, ["grep 'pattern' file | sort | uniq -c", "another command"]),
    (checktext_no_commands, []),
    (checktext_mixed, ["first command", "second command", "third command continues", "fourth"]),
    (checktext_marker_inside, ["actual command"]),
    ("", []),
    (None, []),
    (checktext_ends_with_command, ["last command"]),
    (checktext_ends_with_multiline, ["last multi line command"]),
])
def test_extract_all_commands(checktext, expected_commands):
    # Act
    # Giả sử hàm normalize_command hoạt động đúng (đã test riêng)
    extracted = extract_all_commands(checktext)
    # Assert
    assert extracted == expected_commands
