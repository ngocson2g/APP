#security_app/reporting/terminal.py
import re

from security_app.config import TOP_FAIL_LIMIT
from security_app.models import as_rule
from security_app.reporting.scoring import compute_compliance_score, score_grade
from security_app.utils.text import _bar, _table, _term_width


def print_report(stats, limit_top=TOP_FAIL_LIMIT, list_all_rules: bool = False):
    W = _term_width()
    print("=" * W)
    print("CHECKLIST EXECUTION SUMMARY".center(W))
    print("=" * W)

    # ----- Totals -----
    t = stats["totals"]
    c_score = compute_compliance_score(stats)
    c_grade = score_grade(c_score)
    kv = [
        ("Total rules", t["total_rules"]),
        ("    All OK", t["rules_all_ok"]),
        ("    With failures", t["rules_with_fail"]),
        ("    With denied", t.get("total_rules_denied", 0)),
        ("Pass rate", f"{t['pass_rate']:.2f}%"),
        ("Compliance score", f"{c_score:.1f}/100  ({c_grade})"),
        ("Total commands", t["total_cmds"]),
        ("    Commands OK", t["total_ok"]),
        ("    Commands failed", t["total_fail"]),
        ("    Commands denied", t.get("total_cmds_denied", 0)),
    ]
    width_key = max(len(k) for k, _ in kv) + 2
    for k, v in kv:
        print(f"{k.rjust(width_key)}: {v}")
    print()

    # ----- By severity -----
    print("By severity:")
    headers = ["Severity", "Rules", "#Rules OK/Fail", "Cmd OK/Cmds", "#Cmd Fail", "OK bar"]
    sev_order = ["low","medium","high","critical","unknown"]
    rows = []
    by_sev = stats["by_severity"]
    for sev in sev_order + sorted([s for s in by_sev if s not in sev_order]):
        if sev not in by_sev:
            continue
        d = by_sev[sev]
        ok_rules = d.get("rules",0) - d.get("rules_fail",0)
        fail_rules = d.get("rules_fail",0)
        cmds = d.get("cmds",0)
        ok = d.get("ok",0)
        fail = d.get("fail",0)
        rows.append([
            sev,
            d.get("rules",0),
            f"{ok_rules} ok / {fail_rules} fail",
            f"{ok}/{cmds}",
            fail,
            _bar(ok, cmds, 20),
        ])
    _table(rows, headers)
    print()

    # ----- Top failing rules -----
    print(f"Top failing rules (max {limit_top}):")
    top = stats.get("top_failing_rules", [])
    if top:
        headers = ["#", "Rule ID", "Sev", "#CmdFail", "Title"]
        rows = []
        for i, entry in enumerate(top[:limit_top], start=1):
            idx, rid, sev, num_fail, title = entry  # tuple from compute_stats()
            rows.append([i, str(rid), str(sev), str(num_fail), str(title)])
        _table(rows, headers, max_width=W)
    else:
        print("(Không có rule lỗi)")
    print()

    # ----- Denied by safety policy -----
    all_results = stats["all_results"]
    denied_rows = []
    for x in all_results:
        # Dùng số liệu đã tính sẵn từ stats.py
        nd = x.get("num_denied_cmds", 0) 
        
        if nd > 0:
            r = as_rule(x["rule"])
            denied_rows.append([r.id or x["rule_index"], r.severity, nd, r.title or ""])

    if denied_rows:
        print("Denied by safety policy:")
        _table(denied_rows, headers=["Rule ID","Sev","#Denied","Title"])
        print()

    # ----- Danh sách ID -----
    fail_ids = [as_rule(r["rule"]).id or str(r["rule_index"]) for r in all_results if r["num_fail"] > 0]  # NEW
    ok_ids   = [as_rule(r["rule"]).id or str(r["rule_index"]) for r in all_results if r["num_fail"] == 0] # NEW

    print(f"Failing Rule IDs ({len(fail_ids)}):")
    print(", ".join(fail_ids))
    print()
    print(f"OK Rule IDs ({len(ok_ids)}):")
    print(", ".join(ok_ids))
    print()
    
    if list_all_rules:
        print("=" * W)
        print("ALL RULES STATUS LIST (id title_safe status)".center(W))
        print("=" * W)
        
        rule_strings = []
        all_results = stats.get("all_results", []) # [cite: 251]
        
        for x in all_results:
            rule = as_rule(x.get("rule")) # [cite: 248, 260]
            # Xác định trạng thái true/false
            status = "true" if x.get("num_fail", 0) == 0 else "false"
            
            # Chuẩn hóa tiêu đề: thay mọi khoảng trắng (space, tab, newline) bằng 1 dấu '_'
            clean_title = re.sub(r"\s+", "_", (rule.title or "No-Title").strip())
            
            # Định dạng: ID tieu_de_rule trang_thai
            rule_strings.append(f"{rule.id} | {status} | {clean_title}  \n")
            
        
        # In tất cả ra trên một dòng, cách nhau bằng 1 dấu cách
        print(" ".join(rule_strings))
        print()
    # ===============================================

