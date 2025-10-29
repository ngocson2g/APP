# tests/utils/test_text.py
import pytest
from security_app.utils.text import ellipsis_middle, _safe_name, _bar

# --- Tests for ellipsis_middle ---

@pytest.mark.parametrize("input_str, max_chars, expected", [
    ("This is a short string", 40, "This is a short string"), # String is shorter than max
    ("This string is exactly forty characters long", 40, "This string is exactly forty characters long"), # String equals max
    ("This is a much longer string that needs to be truncated in the middle", 40, "This is a much lon...in the middle"), # Basic truncation
    ("Short", 10, "Short"), # Short string, high max
    ("VeryLongWordWithoutSpaces", 10, "Very...ces"), # Long word
    ("Test with ... dots", 15, "Test w... dots"), # String contains dots already
    ("", 20, ""), # Empty string
    ("abc", 2, "a...c"), # Max chars allows only ellipsis and ends
    ("abcd", 3, "a...d"), # Max chars allows only ellipsis and ends (odd max)
    ("abcdef", 5, "ab...ef"), # Minimal reasonable case
])
def test_ellipsis_middle(input_str, max_chars, expected):
    """Tests the ellipsis_middle function for various inputs."""
    assert ellipsis_middle(input_str, max_chars) == expected

def test_ellipsis_middle_default_max():
    """Tests ellipsis_middle with the default max_chars (180)."""
    long_string = "a" * 200
    expected = "a" * 87 + "..." + "a" * 87 # 180 // 2 - 3 = 87
    assert ellipsis_middle(long_string) == expected
    short_string = "b" * 100
    assert ellipsis_middle(short_string) == short_string

# --- Tests for _safe_name ---

@pytest.mark.parametrize("input_str, maxlen, expected", [
    ("Valid Title 1", 60, "Valid_Title_1"), # Spaces replaced by underscore
    ("Rule with /slashes\\ and? special! chars.", 60, "Rule_with_slashes_and_special_chars."), # Special chars replaced
    ("very_long_title_" * 10, 60, "very_long_title_very_long_title_very_long_title_very_long_..."), # Truncated
    (" short name ", 60, "short_name"), # Leading/trailing spaces trimmed
    ("name-with-dots.and-hyphens", 60, "name-with-dots.and-hyphens"), # Dots and hyphens kept
    ("", 60, ""), # Empty string
    ("你好世界", 60, "你好世界"), # Unicode (assuming filesystem supports it, regex allows it)
    ("Test", 5, "Test"), # Shorter than maxlen
    ("LongTest", 7, "LongT..."), # Truncation exact
])
def test_safe_name(input_str, maxlen, expected):
    """Tests the _safe_name function for creating safe filenames."""
    assert _safe_name(input_str, maxlen) == expected

def test_safe_name_default_maxlen():
    """Tests _safe_name with default maxlen (60)."""
    long_string = "a_b-" * 35 # 4*35 = 140 chars
    expected = "a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-a_b-..." # 57 chars + ...
    assert _safe_name(long_string) == expected
    short_string = "short_safe_name"
    assert _safe_name(short_string) == short_string

# --- Tests for _bar ---

@pytest.mark.parametrize("done, total, width, expected", [
    (50, 100, 20, "██████████          "), # 50%
    (0, 100, 10, "          "), # 0%
    (100, 100, 10, "██████████"), # 100%
    (25, 100, 10, "██        "), # 25% -> floor(2.5) = 2
    (75, 100, 10, "███████   "), # 75% -> floor(7.5) = 7
    (1, 3, 10, "███       "), # 33.3% -> floor(3.33) = 3
    (2, 3, 10, "██████    "), # 66.6% -> floor(6.66) = 6
    (150, 100, 10, "██████████"), # Over 100% -> capped at 100%
    (-10, 100, 10, "          "), # Negative done -> capped at 0%
    (50, 0, 10, ""), # Total is zero -> empty string
    (50, -10, 10, ""), # Total is negative -> empty string
    (50, 100, 3, ""), # Width too small (min width is 4) -> should ideally handle gracefully or error? Assuming empty
    (50, 100, 4, "██  "), # Minimum width 4
    ("50", "100", "20", "██████████          "), # String inputs converted
])
def test_bar(done, total, width, expected):
    """Tests the _bar function for creating ASCII progress bars."""
    # Note: The test for width=3 assumes the function returns "" for widths < 4.
    # Adjust if the actual behavior is different (e.g., raises error or uses min width).
    # Update: Based on code `width = max(4, int(width or 20))`, width=3 becomes 4.
    if width == 3:
         assert _bar(done, total, width) == "██  " # Expected for width=4 at 50%
    else:
        assert _bar(done, total, width) == expected

def test_bar_invalid_types():
    """Tests _bar with invalid types that cannot convert to int."""
    assert _bar("abc", 100, 20) == ""
    assert _bar(50, "xyz", 20) == ""
    assert _bar(50, 100, "def") == ""
    assert _bar(None, 100, 20) == ""
    assert _bar(50, None, 20) == ""


# --- Note on testing _term_width and _table ---
# Testing _term_width reliably requires mocking shutil.get_terminal_size.
# Testing _table requires capturing stdout (using pytest's capsys fixture)
# and comparing the multi-line string output, which can be brittle.
# These might be better tested manually or via integration tests if needed.

# Example using capsys for _table (optional, can be complex)
# def test_table_basic(capsys):
#     rows = [[1, 'A'], [2, 'B']]
#     headers = ['Num', 'Char']
#     _table(rows, headers)
#     captured = capsys.readouterr()
#     expected_output = """
# Num | Char
# -+----
# 1   | A
# 2   | B
# """.strip() + "\n" # Ensure newline at the end
#     # Need careful comparison, potentially ignoring whitespace differences
#     assert captured.out.strip().replace('\r\n', '\n') == expected_output.strip().replace('\r\n', '\n')
