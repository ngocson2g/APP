# tests/parsers/test_dispatch.py
import pytest
from unittest.mock import patch, MagicMock

# Import the function to be tested
from security_app.parsers.dispatch import parse_file

# Define dummy return values for mocked parsers
MOCK_CSV_RESULT = [MagicMock(id="csv_rule")]
MOCK_JSON_RESULT = [MagicMock(id="json_rule")]
MOCK_XML_RESULT = [MagicMock(id="xml_rule")]

# Test suite using patching
# Patch the dependencies directly where they are looked up by dispatch.py
@patch('security_app.parsers.dispatch.detect_file_type')
@patch('security_app.parsers.dispatch.parse_csv')
@patch('security_app.parsers.dispatch.parse_json')
@patch('security_app.parsers.dispatch.parse_xml')
def test_parse_file_dispatches_to_csv(mock_parse_xml, mock_parse_json, mock_parse_csv, mock_detect):
    """Test parse_file calls parse_csv for .csv files."""
    # Arrange
    mock_detect.return_value = "csv"
    mock_parse_csv.return_value = MOCK_CSV_RESULT
    file_path = "input.csv"

    # Act
    result = parse_file(file_path)

    # Assert
    mock_detect.assert_called_once_with(file_path)
    mock_parse_csv.assert_called_once_with(file_path)
    mock_parse_json.assert_not_called()
    mock_parse_xml.assert_not_called()
    assert result == MOCK_CSV_RESULT

@patch('security_app.parsers.dispatch.detect_file_type')
@patch('security_app.parsers.dispatch.parse_csv')
@patch('security_app.parsers.dispatch.parse_json')
@patch('security_app.parsers.dispatch.parse_xml')
def test_parse_file_dispatches_to_json(mock_parse_xml, mock_parse_json, mock_parse_csv, mock_detect):
    """Test parse_file calls parse_json for .json files."""
    # Arrange
    mock_detect.return_value = "json"
    mock_parse_json.return_value = MOCK_JSON_RESULT
    file_path = "input.json"

    # Act
    result = parse_file(file_path)

    # Assert
    mock_detect.assert_called_once_with(file_path)
    mock_parse_csv.assert_not_called()
    mock_parse_json.assert_called_once_with(file_path)
    mock_parse_xml.assert_not_called()
    assert result == MOCK_JSON_RESULT

@patch('security_app.parsers.dispatch.detect_file_type')
@patch('security_app.parsers.dispatch.parse_csv')
@patch('security_app.parsers.dispatch.parse_json')
@patch('security_app.parsers.dispatch.parse_xml')
def test_parse_file_dispatches_to_xml(mock_parse_xml, mock_parse_json, mock_parse_csv, mock_detect):
    """Test parse_file calls parse_xml for .xml files."""
    # Arrange
    mock_detect.return_value = "xml"
    mock_parse_xml.return_value = MOCK_XML_RESULT
    file_path = "input.xml"

    # Act
    result = parse_file(file_path)

    # Assert
    mock_detect.assert_called_once_with(file_path)
    mock_parse_csv.assert_not_called()
    mock_parse_json.assert_not_called()
    mock_parse_xml.assert_called_once_with(file_path)
    assert result == MOCK_XML_RESULT

@patch('security_app.parsers.dispatch.detect_file_type')
@patch('security_app.parsers.dispatch.parse_csv')
@patch('security_app.parsers.dispatch.parse_json')
@patch('security_app.parsers.dispatch.parse_xml')
def test_parse_file_unsupported_type(mock_parse_xml, mock_parse_json, mock_parse_csv, mock_detect):
    """Test parse_file raises ValueError for unsupported types."""
    # Arrange
    mock_detect.return_value = "txt" # Simulate detect returning an unsupported type
    file_path = "input.txt"

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file(file_path)

    # Check that no parser was called
    mock_detect.assert_called_once_with(file_path)
    mock_parse_csv.assert_not_called()
    mock_parse_json.assert_not_called()
    mock_parse_xml.assert_not_called()

@patch('security_app.parsers.dispatch.detect_file_type', side_effect=ValueError("Test detection error"))
@patch('security_app.parsers.dispatch.parse_csv')
@patch('security_app.parsers.dispatch.parse_json')
@patch('security_app.parsers.dispatch.parse_xml')
def test_parse_file_detection_error(mock_parse_xml, mock_parse_json, mock_parse_csv, mock_detect):
    """Test parse_file propagates error from detect_file_type."""
    # Arrange
    file_path = "bad_extension."

    # Act & Assert
    with pytest.raises(ValueError, match="Test detection error"):
        parse_file(file_path)

    # Check that no parser was called
    mock_detect.assert_called_once_with(file_path)
    mock_parse_csv.assert_not_called()
    mock_parse_json.assert_not_called()
    mock_parse_xml.assert_not_called()
