#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
So sánh hai file STIG (định dạng .csv, .json, hoặc .xml) để tìm sự khác biệt
trong 'fixtext' hoặc 'checktext' cho các rule ID trùng lặp.
"""

import csv
import json
import xml.etree.ElementTree as ET
import argparse
import sys
import os
from typing import Dict, Optional, Any

# Định nghĩa kiểu dữ liệu cho một rule đã được chuẩn hóa
RuleData = Dict[str, str]
RuleDatabase = Dict[str, RuleData]

def normalize_text(text: Optional[str]) -> str:
    """
    Chuẩn hóa text để so sánh.
    - Xóa khoảng trắng đầu/cuối.
    - Thay thế các kiểu xuống dòng khác nhau bằng \n.
    - Xóa khoảng trắng đầu/cuối của từng dòng.
    - Lọc bỏ các dòng trống.
    """
    if not text:
        return ""
    
    # Thay thế \r\n và \r bằng \n
    cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Tách các dòng, xóa khoảng trắng đầu/cuối của mỗi dòng
    lines = [line.strip() for line in cleaned_text.split('\n')]
    
    # Lọc bỏ các dòng trống
    non_empty_lines = [line for line in lines if line]
    
    # Nối lại bằng một ký tự xuống dòng duy nhất
    return "\n".join(non_empty_lines)

def load_csv(filepath: str) -> Optional[RuleDatabase]:
    """Tải và phân tích file STIG định dạng CSV."""
    rules: RuleDatabase = {}
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            # -sig để xử lý BOM (Byte Order Mark) nếu có
            reader = csv.DictReader(f)
            for row in reader:
                rule_id = row.get('id')
                if rule_id:
                    rules[rule_id] = {
                        'fix': normalize_text(row.get('fixtext')),
                        'check': normalize_text(row.get('checktext'))
                    }
        print(f"  -> Đã tải {len(rules)} rules từ {os.path.basename(filepath)}")
        return rules
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {filepath}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Lỗi khi đọc file CSV {filepath}: {e}", file=sys.stderr)
        return None

def load_json(filepath: str) -> Optional[RuleDatabase]:
    """Tải và phân tích file STIG định dạng JSON."""
    rules: RuleDatabase = {}
    try:
        with open(filepath, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            # Giả định cấu trúc JSON theo file mẫu của bạn: {"stig": {"findings": {"V-XXXX": ...}}}
            findings = data.get('stig', {}).get('findings', {})
            if not findings:
                print(f"Cảnh báo: Không tìm thấy 'stig.findings' trong {filepath}", file=sys.stderr)
                return {} # Trả về dict rỗng nếu cấu trúc không khớp

            for rule_id, details in findings.items():
                rules[rule_id] = {
                    'fix': normalize_text(details.get('fixtext')),
                    'check': normalize_text(details.get('checktext'))
                }
        print(f"  -> Đã tải {len(rules)} rules từ {os.path.basename(filepath)}")
        return rules
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {filepath}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Lỗi khi giải mã JSON từ {filepath}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Lỗi khi đọc file JSON {filepath}: {e}", file=sys.stderr)
        return None

def load_xml(filepath: str) -> Optional[RuleDatabase]:
    """Tải và phân tích file STIG định dạng XCCDF XML."""
    rules: RuleDatabase = {}
    try:
        # Đăng ký namespace để làm sạch các lệnh find/findall
        ns = {'xccdf': 'http://checklists.nist.gov/xccdf/1.1'}
        ET.register_namespace('', ns['xccdf'])
        
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Tìm tất cả các <Rule> element ở bất kỳ đâu trong cây
        for rule in root.findall('.//xccdf:Rule', ns):
            rule_id = rule.get('id')
            if not rule_id:
                continue
            
            # Lấy fixtext
            fix_elem = rule.find('xccdf:fixtext', ns)
            fix_text = fix_elem.text if fix_elem is not None else None
            
            # Lấy checktext (thường nằm trong check/check-content)
            check_elem = rule.find('xccdf:check/xccdf:check-content', ns)
            check_text = check_elem.text if check_elem is not None else None
            
            rules[rule_id] = {
                'fix': normalize_text(fix_text),
                'check': normalize_text(check_text)
            }
        print(f"  -> Đã tải {len(rules)} rules từ {os.path.basename(filepath)}")
        return rules
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy file {filepath}", file=sys.stderr)
        return None
    except ET.ParseError as e:
        print(f"Lỗi khi phân tích XML từ {filepath}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Lỗi khi đọc file XML {filepath}: {e}", file=sys.stderr)
        return None

def load_rules_from_file(filepath: str) -> Optional[RuleDatabase]:
    """
    Hàm điều phối, gọi hàm load thích hợp dựa trên phần mở rộng của file.
    """
    # Lấy phần mở rộng của file và chuyển thành chữ thường
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    if ext == '.csv':
        return load_csv(filepath)
    elif ext == '.json':
        return load_json(filepath)
    elif ext == '.xml':
        return load_xml(filepath)
    else:
        print(f"Lỗi: Định dạng file '{ext}' không được hỗ trợ.", file=sys.stderr)
        print("Chương trình chỉ hỗ trợ các file .csv, .json, và .xml.", file=sys.stderr)
        return None

def compare_rules(file1: str, file2: str):
    """
    Hàm chính để tải và so sánh hai file.
    """
    print(f"Đang tải file 1: {file1}")
    rules1 = load_rules_from_file(file1)
    if rules1 is None:
        print("Không thể tiếp tục do lỗi tải file 1.")
        return

    print(f"Đang tải file 2: {file2}")
    rules2 = load_rules_from_file(file2)
    if rules2 is None:
        print("Không thể tiếp tục do lỗi tải file 2.")
        return

    print("\n" + "="*80)
    print(f"BẮT ĐẦU SO SÁNH (File 1: {len(rules1)} rules, File 2: {len(rules2)} rules)")
    print("="*80 + "\n")

    # Lấy tập hợp tất cả các ID chung của cả hai file
    common_ids = set(rules1.keys()) & set(rules2.keys())
    
    if not common_ids:
        print("Không tìm thấy rule ID nào chung giữa hai file.")
        return

    diff_found_count = 0
    
    # Chỉ lặp qua các ID chung
    for rule_id in sorted(list(common_ids)):
        rule1 = rules1[rule_id]
        rule2 = rules2[rule_id]
        
        fix_diff = rule1['fix'] != rule2['fix']
        check_diff = rule1['check'] != rule2['check']
        
        if fix_diff or check_diff:
            diff_found_count += 1
            print(f"--- KHÁC BIỆT TÌM THẤY CHO ID: {rule_id} ---")
            
            if fix_diff:
                print("\n[FIXTEXT KHÁC NHAU]")
                print(f"  File 1 ({os.path.basename(file1)}):\n\"\"\"\n{rule1['fix']}\n\"\"\"")
                print(f"  File 2 ({os.path.basename(file2)}):\n\"\"\"\n{rule2['fix']}\n\"\"\"")
                
            if check_diff:
                print("\n[CHECKTEXT KHÁC NHAU]")
                print(f"  File 1 ({os.path.basename(file1)}):\n\"\"\"\n{rule1['check']}\n\"\"\"")
                print(f"  File 2 ({os.path.basename(file2)}):\n\"\"\"\n{rule2['check']}\n\"\"\"")
            
            print("-" * (len(rule_id) + 30) + "\n")

    print("="*80)
    if diff_found_count == 0:
        print(f"SO SÁNH HOÀN TẤT: Không tìm thấy sự khác biệt nào trong {len(common_ids)} rule ID chung.")
    else:
        print(f"SO SÁNH HOÀN TẤT: Tìm thấy {diff_found_count} rule ID có sự khác biệt.")
    print("="*80)

def main():
    """
    Hàm main để xử lý tham số dòng lệnh.
    """
    parser = argparse.ArgumentParser(
        description="So sánh hai file STIG (csv, json, xml) và tìm các rule ID chung có 'câu lệnh' (fixtext hoặc checktext) khác nhau.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("file1", help="Đường dẫn đến file STIG thứ nhất (csv, json, hoặc xml).")
    parser.add_argument("file2", help="Đường dẫn đến file STIG thứ hai (csv, json, hoặc xml).")
    
    args = parser.parse_args()
    
    # Kiểm tra file tồn tại
    if not os.path.exists(args.file1):
        print(f"Lỗi: File '{args.file1}' không tồn tại.", file=sys.stderr)
        sys.exit(1)
            
    if not os.path.exists(args.file2):
        print(f"Lỗi: File '{args.file2}' không tồn tại.", file=sys.stderr)
        sys.exit(1)
            
    compare_rules(args.file1, args.file2)

if __name__ == "__main__":
    main()
