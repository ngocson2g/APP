# security_app/parsers/rc_parser.py
from __future__ import annotations

import pandas as pd
from typing import List
from security_app.models import RC_result

def _normalize_columns(cols: list[str]) -> list[str]:
    """Helper to normalize column names for robust lookup."""
    return [str(c).strip().lower().replace("-", "_").replace(" ", "_") for c in cols]

def _split_rc_values(rc_str: str) -> List[str]:
    """
    Tách chuỗi RC thành các ký tự riêng biệt.
    Ví dụ: "0, 0, 1" -> ['0', '0', '1']
            "1" -> ['1']
            "0,2" -> ['0', '2']
    """
    if not rc_str or pd.isna(rc_str):
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
        df = pd.read_csv(path, dtype=str)  # Đọc tất cả dưới dạng string
    except FileNotFoundError:
        print(f"Warning: RC file not found at {path}, skipping.")
        return []
    except Exception as e:
        raise ValueError(f"Failed to read CSV {path}: {e}")

    df.columns = _normalize_columns(list(df.columns))

    # Define aliases for the columns we need
    id_col_aliases = ['id_rule', 'id', 'rule_id', 'vuln_id', 'group_id']
    rc_col_aliases = ['rc', 'returncode', 'result_code']

    # Find the first matching column name from aliases
    id_col = next((c for c in id_col_aliases if c in df.columns), None)
    rc_col = next((c for c in rc_col_aliases if c in df.columns), None)

    if not id_col or not rc_col:
        raise ValueError(
            f"Missing required columns in {path}. "
            f"Need one of {id_col_aliases} and one of {rc_col_aliases}. "
            f"Found columns: {list(df.columns)}"
        )
    
    # Ensure id_col is treated as string
    df[id_col] = df[id_col].astype(str)
    
    # Drop rows where id_rule is missing
    df = df.dropna(subset=[id_col])
    
    # Tách các giá trị RC thành các ký tự riêng biệt
    df[rc_col] = df[rc_col].apply(_split_rc_values)
    
    # Gom nhóm theo id_rule và kết hợp tất cả RC values
    grouped = df.groupby(id_col)[rc_col].apply(
        lambda x: [item for sublist in x for item in sublist]
    ).reset_index()

    # Convert DataFrame to list of RC_result models
    results: List[RC_result] = []
    for _, row in grouped.iterrows():
        results.append(RC_result(
            id_rule=row[id_col], 
            RC=row[rc_col]  # Đây sẽ là list[str] với mỗi phần tử là 1 ký tự
        ))
        
    return results