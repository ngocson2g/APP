# security_app/parsers/rc_parser.py
from __future__ import annotations

import csv
from typing import List, Dict
from collections import defaultdict
from security_app.models import RC_result

def _normalize_columns(cols: list[str]) -> list[str]:
    """Helper to normalize column names for robust lookup."""
    return [str(c).strip().lower().replace("-", "_").replace(" ", "_") if c else "" for c in cols]

def _split_rc_values(rc_str: str) -> List[str]:
    """
    Tách chuỗi RC thành các ký tự riêng biệt.
    Ví dụ: "0, 0, 1" -> ['0', '0', '1']
            "1" -> ['1']
            "0,2" -> ['0', '2']
    """
    if not rc_str:
        return []
    
    # Tách chuỗi bằng dấu phẩy và loại bỏ khoảng trắng
    parts = [part.strip() for part in str(rc_str).split(',')]
    # Loại bỏ phần tử rỗng
    return [part for part in parts if part]

def parse_rc_stigs(path: str) -> List[RC_result]:
    """
    Parses the result_RC_stigs.csv file.
    Assumes columns like 'id_rule' and 'RC'.
    Tách các giá trị RC thành các ký tự riêng biệt.
    """
    try:
        f = open(path, mode="r", encoding="utf-8-sig")
    except FileNotFoundError:
        print(f"Warning: RC file not found at {path}, skipping.")
        return []
    except Exception as e:
        raise ValueError(f"Failed to read CSV {path}: {e}")

    with f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return []
            
        headers = _normalize_columns(headers)
        
        # Define aliases for the columns we need
        id_col_aliases = ['id_rule', 'id', 'rule_id', 'vuln_id', 'group_id']
        rc_col_aliases = ['rc', 'returncode', 'result_code']
        
        # Find the first matching column name from aliases
        id_col = next((c for c in id_col_aliases if c in headers), None)
        rc_col = next((c for c in rc_col_aliases if c in headers), None)

        if not id_col or not rc_col:
            raise ValueError(
                f"Missing required columns in {path}. "
                f"Need one of {id_col_aliases} and one of {rc_col_aliases}. "
                f"Found columns: {headers}"
            )
            
        f.seek(0)
        dict_reader = csv.DictReader(f)
        dict_reader.fieldnames = headers
        next(dict_reader, None)  # Bỏ qua header
        
        # Gom nhóm theo id_rule và kết hợp tất cả RC values
        grouped_rcs: Dict[str, List[str]] = defaultdict(list)
        
        for row in dict_reader:
            rule_id = row.get(id_col)
            if not rule_id or not str(rule_id).strip():
                continue
                
            rule_id = str(rule_id).strip()
            rc_val = row.get(rc_col)
            if rc_val:
                split_rcs = _split_rc_values(rc_val)
                grouped_rcs[rule_id].extend(split_rcs)
                
    # Convert dict to list of RC_result models
    results: List[RC_result] = []
    for rule_id, rcs in grouped_rcs.items():
        results.append(RC_result(
            id_rule=rule_id, 
            RC=rcs  # Đây sẽ là list[str] với mỗi phần tử là 1 ký tự
        ))
        
    return results