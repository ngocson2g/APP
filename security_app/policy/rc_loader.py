# security_app/policy/rc_loader.py
from __future__ import annotations

import csv
import os
import re
import sys
from typing import Dict, Set

# Regex để tìm các token hợp lệ: số nguyên hoặc dấu #
_RC_TOKEN_RX = re.compile(r"(\d+|#)")

def _parse_rc_string(rc_str: str) -> Set[str]:
    """
    Phân tích chuỗi RC từ CSV thành một tập hợp (set) các giá trị "pass".
    Ví dụ: '0, 0, 0' -> {'0'}
           '3 or 4' -> {'3', '4'}
           '0,0,1'  -> {'0', '1'}
           '#'      -> {'#'}
           '#0'     -> {'#', '0'}
           '00'     -> {'0'}
    """
    s = rc_str.strip()
    if not s:
        return {"0"}  # Mặc định là '0' nếu chuỗi rỗng

    # Tìm tất cả token (số hoặc #)
    tokens = _RC_TOKEN_RX.findall(s)
    if not tokens:
        # Fallback nếu chuỗi không hợp lệ (ví dụ: "N/A")
        return {"0"}

    # Chuẩn hóa: '00' -> '0'
    normalized_tokens = {str(int(t)) if t.isdigit() else t for t in tokens}
    return normalized_tokens

def load_rc_map_from_csv(file_path: str) -> Dict[str, Set[str]]:
    """Tải tệp CSV  và xây dựng map: {rule_id -> set_of_pass_rcs}."""
    rc_map: Dict[str, Set[str]] = {}
    if not os.path.exists(file_path):
        print(f"[WARN] Không tìm thấy tệp định nghĩa RC: {file_path}", file=sys.stderr)
        return {}  # Trả về map rỗng

    try:
        # dùng utf-8-sig để xử lý BOM (Byte Order Mark) nếu có
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rule_id = row.get('id', '').strip()
                rc_val = row.get('RC', '').strip()
                if rule_id:
                    rc_map[rule_id] = _parse_rc_string(rc_val)
    except Exception as e:
        print(f"[ERROR] Không thể tải RC map: {e}", file=sys.stderr)
        return {}  # Trả về map rỗng nếu lỗi
    
    print(f"[INFO] Đã tải thành công {len(rc_map)} định nghĩa RC từ {file_path}")
    return rc_map

# --- Global cache cho RC map ---
# Tải một lần duy nhất khi ứng dụng khởi động
_RC_MAP_PATH = os.getenv("SECAPP_RC_MAP_PATH", "data/result_RC.csv")
_RC_MAP_CACHE: Dict[str, Set[str]] | None = None

def get_rc_map() -> Dict[str, Set[str]]:
    """Lấy RC map từ cache, tải lần đầu nếu cần."""
    global _RC_MAP_CACHE
    if _RC_MAP_CACHE is None:
        _RC_MAP_CACHE = load_rc_map_from_csv(_RC_MAP_PATH)
    return _RC_MAP_CACHE

def check_rc_pass(rule_id: str, actual_rc: int | None) -> bool:
    """
    Kiểm tra xem actual_rc (int) có phải là điều kiện "pass"
    cho rule_id dựa trên map đã tải từ CSV  hay không.
    """
    # 1. Lệnh bị timeout/denied (rc=None) luôn là 'fail'
    if actual_rc is None:
        return False

    rc_map = get_rc_map()
    expected_set = rc_map.get(rule_id)

    # 2. Nếu rule_id không có trong CSV  -> dùng logic mặc định (0 là pass)
    if expected_set is None:
        return actual_rc == 0

    # 3. Kiểm tra trường hợp đặc biệt '#' (N/A, Manual)  -> luôn pass
    if "#" in expected_set:
        return True

    # 4. Kiểm tra RC thực tế với tập hợp RC "pass"
    actual_rc_str = str(actual_rc)
    return actual_rc_str in expected_set