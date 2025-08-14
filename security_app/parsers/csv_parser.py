import pandas as pd

def parse_csv(file_path):
    df = pd.read_csv(file_path, dtype=str)
    # Chuẩn hóa tên cột
    df.columns = [c.strip().lower() for c in df.columns]
    # Tạo map giữa trường chuẩn và trường thực tế trong file
    col_map = {
        'id': 'id',
        'description': 'description',
        'check': 'checktext',        # <-- Map cột "check" về "checktext"
        'fix': 'fixtext',            # <-- Map cột "fix" về "fixtext"
        'severity': 'severity'
    }
    # Kiểm tra tồn tại các trường cần thiết
    for req, real in col_map.items():
        if real not in df.columns:
            raise Exception(f"Missing column: {real} (for field {req})")
    rules = []
    for _, row in df.iterrows():
        rule = {k: str(row[v]) if v in row and pd.notnull(row[v]) else '' for k, v in col_map.items()}
        rules.append(rule)
    return rules

