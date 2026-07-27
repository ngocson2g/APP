# tests/parsers/test_common.py
import pytest
from security_app.parsers.common import detect_file_type

# --- Test detect_file_type ---

@pytest.mark.parametrize("file_path, expected_type", [
    ("data.csv", "csv"),
    ("/path/to/SCAN.JSON", "json"), # Test case insensitivity and path
    ("report.xml", "xml"),
    ("archive.tar.gz.xml", "xml"), # Test complex filenames
    ("file_with.dots.csv", "csv"),
    ("UPPERCASE.CSV", "csv"),     # Test uppercase extension
])
def test_detect_file_type_known(file_path, expected_type):
    """Tests detection of known file types."""
    assert detect_file_type(file_path) == expected_type

@pytest.mark.parametrize("file_path", [
    "document.txt",
    "image.png",
    "no_extension",
    "/path/to/another.", # Ends with dot
    "",                  # Empty string
])
def test_detect_file_type_unknown(file_path):
    """Tests that unknown file types raise ValueError."""
    with pytest.raises(ValueError, match=r"Unknown file type:"):
        detect_file_type(file_path)

def test_detect_file_type_no_extension():
    """Specific test for files with no extension."""
    with pytest.raises(ValueError, match=r"Unknown file type:"):
        detect_file_type("file_without_extension")
