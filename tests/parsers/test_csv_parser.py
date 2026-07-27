# tests/parsers/test_csv_parser.py
import pytest
from io import StringIO
from security_app.parsers.csv_parser import parse_csv
from security_app.models import Rule

# Dữ liệu CSV mẫu
csv_valid_content = """id,description,check,fix,severity,title
RULE-001,Desc 1,"$ cmd1",Fix 1,high,Title 1
RULE-002,Desc 2,"$ cmd2\\n$ cmd3",Fix 2,medium,
"""

csv_missing_check_content = """id,description,fix,severity,title
RULE-003,Desc 3,Fix 3,low,Title 3
"""

csv_extra_col_content = """id,check,severity,author
RULE-004,$ cmd4,low,Tester
"""

def test_parse_csv_valid(tmp_path):
    """Kiểm tra parse file CSV hợp lệ."""
    # Arrange
    csv_file = tmp_path / "valid.csv"
    csv_file.write_text(csv_valid_content, encoding="utf-8")
    # Act
    rules = parse_csv(str(csv_file))
    # Assert
    assert len(rules) == 2
    assert isinstance(rules[0], Rule)
    assert rules[0].id == "RULE-001"
    assert rules[0].severity == "high"
    assert rules[0].title == "Title 1"
    assert rules[0].check == "$ cmd1"
    assert rules[1].id == "RULE-002"
    assert rules[1].severity == "medium"
    assert rules[1].title == "" # Tiêu đề trống được chấp nhận
    assert rules[1].check == "$ cmd2\\n$ cmd3"

def test_parse_csv_missing_required_field(tmp_path):
    """Kiểm tra lỗi khi thiếu trường bắt buộc (check)."""
    # Arrange
    csv_file = tmp_path / "missing.csv"
    csv_file.write_text(csv_missing_check_content, encoding="utf-8")
    # Act & Assert
    with pytest.raises(Exception, match=r"Missing \['check'\]"):
        parse_csv(str(csv_file))

def test_parse_csv_extra_column(tmp_path):
    """Kiểm tra việc bỏ qua cột thừa không gây lỗi."""
    # Arrange
    csv_file = tmp_path / "extra.csv"
    csv_file.write_text(csv_extra_col_content, encoding="utf-8")
    # Act
    rules = parse_csv(str(csv_file))
    # Assert
    assert len(rules) == 1
    assert rules[0].id == "RULE-004"
    assert rules[0].severity == "low"
    assert hasattr(rules[0], 'author') is False # Đảm bảo cột thừa không được thêm vào
    # Lưu ý: Mô tả và fix sẽ là chuỗi rỗng vì không có trong CSV
    assert rules[0].description == ""
    assert rules[0].fix == ""
