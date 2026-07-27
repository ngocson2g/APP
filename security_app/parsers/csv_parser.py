#security_app/parser/csv_parser.py
import csv
import html

from security_app.models import Rule
from security_app.parsers.schema import COL_MAP, REQ_FIELDS


def _normalize_columns(cols):
    # về lowercase, thay khoảng trắng/dấu gạch thành underscore để ổn định tra cứu
    return [str(c).strip().lower().replace("-", "_").replace(" ", "_") if c else "" for c in cols]

def _pick_first(row, aliases):
    for k in aliases:
        val = row.get(k)
        if val is not None and str(val).strip():
            value = str(val).strip()
            # Tự động chuẩn hóa (unescape) các ký tự HTML
            return html.unescape(value)
    return ""

def parse_csv(path: str):
    rules: list[Rule] = []
    with open(path, mode="r", encoding="utf-8-sig") as f:
        # Đọc 1 dòng đầu tiên để lấy header
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return []
        
        headers = _normalize_columns(headers)
        
        # Quay lại dùng DictReader với header đã normalize
        f.seek(0)
        dict_reader = csv.DictReader(f)
        dict_reader.fieldnames = headers
        
        # Bỏ qua dòng header thực tế (do đã đọc lúc nãy)
        next(dict_reader, None)

        for r in dict_reader:
            rid   = _pick_first(r, COL_MAP["id"])
            desc  = _pick_first(r, COL_MAP["description"])
            check = _pick_first(r, COL_MAP["check"])
            fix   = _pick_first(r, COL_MAP["fix"])
            sev   = (_pick_first(r, COL_MAP["severity"]) or "").lower()
            title = _pick_first(r, COL_MAP.get("title", [])) or _pick_first(r, COL_MAP.get("name", []))
            
            # lấy Assessment Status nếu có
            assess = (_pick_first(r, COL_MAP.get("assessment_status", [])) or "").strip().lower()
            
            # validate theo REQ_FIELDS
            vals = {"id": rid, "description": desc, "check": check, "fix": fix, "severity": sev}
            missing = [f for f in REQ_FIELDS if not vals.get(f)]
            if missing:
                raise Exception(f"Missing {missing} in CSV row (tentative id={rid or '(unknown)'})")
    
            rules.append(Rule(
                id=rid, description=desc, check=check, fix=fix, severity=sev, title=title, assessment_status=assess or ""
            ))
            
    return rules