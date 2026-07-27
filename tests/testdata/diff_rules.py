import csv
import json
import os

def clean_csv_string(text: str) -> str:
    """
    Thay thế các thực thể HTML (&#039;) trong file CSV bằng ký tự tương ứng.
    Lưu ý của bạn nói là nháy kép, nhưng &#039; là mã cho nháy đơn (').
    """
    return text.replace("&#039;", "'")

def extract_code_lines(text_block: str | None, clean_func=None) -> list[str]:
    """
    Trích xuất tất cả các dòng bắt đầu bằng '$' từ một khối văn bản.
    """
    lines = []
    if not text_block:
        return lines
    
    # Áp dụng hàm dọn dẹp (ví dụ: cho CSV) nếu được cung cấp
    if clean_func:
        text_block = clean_func(text_block)
        
    for line in text_block.splitlines():
        # Tách và làm sạch từng dòng
        cleaned_line = line.strip()
        if cleaned_line.startswith('$'):
            lines.append(cleaned_line)
    return lines

def parse_csv_file(filename: str, rules_dict: dict):
    """
    Đọc file CSV và điền vào 'rules_dict' với {rule_id: [dòng code]}.
    """
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            # Sử dụng DictReader để dễ dàng truy cập cột bằng tên
            reader = csv.DictReader(f)
            for row in reader:
                rule_id = row.get('id')
                if not rule_id:
                    continue
                
                fix_text = row.get('fixtext', '')
                check_text = row.get('checktext', '')
                
                # Trích xuất code, áp dụng hàm dọn dẹp cho CSV
                code_lines = []
                code_lines.extend(extract_code_lines(fix_text, clean_csv_string))
                code_lines.extend(extract_code_lines(check_text, clean_csv_string))
                
                if rule_id not in rules_dict:
                    rules_dict[rule_id] = []
                rules_dict[rule_id].extend(code_lines)
                
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {filename}")
    except Exception as e:
        print(f"LỖI khi đọc file CSV {filename}: {e}")

def parse_json_file(filename: str, rules_dict: dict):
    """
    Đọc file JSON (STIG) và điền vào 'rules_dict' với {rule_id: [dòng code]}.
    """
    try:
        with open(filename, mode='r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Điều hướng cấu trúc file STIG JSON
            findings = data.get('stig', {}).get('findings', {})
            if not findings:
                print(f"LƯU Ý: File JSON {filename} không có cấu trúc 'stig.findings' như mong đợi.")
                return

            for rule_id, details in findings.items():
                fix_text = details.get('fixtext')
                check_text = details.get('checktext')
                
                # Trích xuất code (không cần hàm dọn dẹp cho JSON)
                code_lines = []
                code_lines.extend(extract_code_lines(fix_text))
                code_lines.extend(extract_code_lines(check_text))
                
                if rule_id not in rules_dict:
                    rules_dict[rule_id] = []
                rules_dict[rule_id].extend(code_lines)

    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {filename}")
    except json.JSONDecodeError:
        print(f"LỖI: File {filename} không phải là file JSON hợp lệ.")
    except Exception as e:
        print(f"LỖI khi đọc file JSON {filename}: {e}")

def compare_rules(csv_file: str, json_file: str):
    """
    Hàm chính để tải, phân tích và so sánh hai file rules.
    """
    csv_rules_code = {}
    json_rules_code = {}
    
    print(f"Đang xử lý file CSV: {csv_file}...")
    parse_csv_file(csv_file, csv_rules_code)
    
    print(f"Đang xử lý file JSON: {json_file}...")
    parse_json_file(json_file, json_rules_code)
    
    print("\n--- BẮT ĐẦU SO SÁNH ---")
    
    # Lấy tất cả các mã rule từ cả hai file
    all_rule_ids = set(csv_rules_code.keys()) | set(json_rules_code.keys())
    
    if not all_rule_ids:
        print("Không tìm thấy rule nào trong cả hai file.")
        return

    discrepancies_found = False
    
    # Sắp xếp để output có thứ tự
    for rule_id in sorted(list(all_rule_ids)):
        # Chuyển danh sách code thành 'set' để so sánh dễ dàng
        # .get(rule_id, []) trả về list rỗng nếu rule không tồn tại ở 1 trong 2 file
        csv_lines = set(csv_rules_code.get(rule_id, []))
        json_lines = set(json_rules_code.get(rule_id, []))
        
        # Tìm các dòng chỉ có ở CSV hoặc chỉ có ở JSON
        unique_to_csv = sorted(list(csv_lines - json_lines))
        unique_to_json = sorted(list(json_lines - csv_lines))
        
        # Nếu có bất kỳ sự khác biệt nào...
        if unique_to_csv or unique_to_json:
            discrepancies_found = True
            
            # Ghép cặp các dòng khác biệt để in ra
            max_len = max(len(unique_to_csv), len(unique_to_json))
            for i in range(max_len):
                print(f"\nRule: {rule_id}") # Dòng 1: Mã Rule
                
                # Dòng 2: Code từ CSV (hoặc placeholder)
                csv_line = unique_to_csv[i] if i < len(unique_to_csv) else "(Không có dòng khác biệt tương ứng trong CSV)"
                print(f"  CSV : {csv_line}")
                
                # Dòng 3: Code từ JSON (hoặc placeholder)
                json_line = unique_to_json[i] if i < len(unique_to_json) else "(Không có dòng khác biệt tương ứng trong JSON)"
                print(f"  JSON: {json_line}")

    if not discrepancies_found:
        print("\nHoàn tất: Không tìm thấy sự khác biệt nào về code giữa hai file.")
    else:
        print("\n--- SO SÁNH HOÀN TẤT ---")

# --- CHẠY CHƯƠNG TRÌNH ---
if __name__ == "__main__":
    # Đặt tên file của bạn ở đây
    # Giả sử các file nằm cùng thư mục với script
    CSV_FILENAME = 'canonical_ubuntu_24.04_lts.csv'
    JSON_FILENAME = 'canonical_ubuntu_24.04_lts.json'
    
    if not os.path.exists(CSV_FILENAME) or not os.path.exists(JSON_FILENAME):
        print(f"LỖI: Vui lòng đảm bảo 2 file '{CSV_FILENAME}' và '{JSON_FILENAME}' tồn tại trong cùng thư mục.")
    else:
        compare_rules(CSV_FILENAME, JSON_FILENAME)
