#secirity_app/reporting/stats.py
from collections import defaultdict

from security_app.models import Rule, as_rule  # NEW


def compute_stats(run_results):
    # NEW: ép về Rule một lần cho toàn pipeline reporting
    normalized = []
    for x in run_results:
        r = dict(x)
        r["rule"] = as_rule(x.get("rule"))
        normalized.append(r)

    total_rules = len(normalized)
    total_cmds  = sum(x["num_cmds"] for x in normalized)
    total_ok    = sum(x["num_ok"] for x in normalized)
    total_fail  = sum(x["num_fail"] for x in normalized)
    rules_all_ok = sum(1 for x in normalized if x["num_fail"] == 0)
    rules_with_fail = total_rules - rules_all_ok
    pass_rate = (rules_all_ok / total_rules * 100.0) if total_rules else 0.0

    by_sev = defaultdict(lambda: {"rules":0,"rules_fail":0,"cmds":0,"ok":0,"fail":0})
    
    total_cmds_denied = 0
    total_rules_denied = 0
    
    for x in normalized:
        rule: Rule = x["rule"]
        sev = (rule.severity or "unknown").lower()
        by_sev[sev]["rules"] += 1
        by_sev[sev]["cmds"]  += x["num_cmds"]
        by_sev[sev]["ok"]    += x["num_ok"]
        by_sev[sev]["fail"]  += x["num_fail"]
        if x["num_fail"] > 0:
            by_sev[sev]["rules_fail"] += 1
            
        
        # Tính toán số lệnh bị DENIED cho rule này
        cmds_denied_in_this_rule = 0
        cmds = x.get("cmd_results") or []
        for r in cmds:
            # Dùng logic chuẩn đã sửa ở lần trước
            if (getattr(r, "stderr", "") or "").strip().upper().startswith("DENIED"):
                cmds_denied_in_this_rule += 1
                
        # Thêm vào tổng
        total_cmds_denied += cmds_denied_in_this_rule
        if cmds_denied_in_this_rule > 0:
            total_rules_denied += 1
            
        # Lưu lại để bảng "Denied" ở terminal.py dùng (tối ưu)
        x["num_denied_cmds"] = cmds_denied_in_this_rule

    top_fail = sorted(
        [
            (x["rule_index"], x["rule"].id or str(x["rule_index"]),
             x["rule"].severity or "", x["num_fail"], x["rule"].title or "")
            for x in normalized if x["num_fail"] > 0
        ],
        key=lambda t: (-t[3], t[0])
    )

    return {
        "totals": {
            "total_rules": total_rules,
            "rules_all_ok": rules_all_ok,
            "rules_with_fail": rules_with_fail,
            "pass_rate": pass_rate,
            "total_cmds": total_cmds,
            "total_ok": total_ok,
            "total_fail": total_fail,
            "total_cmds_denied": total_cmds_denied,
            "total_rules_denied": total_rules_denied,
        },
        "by_severity": by_sev,
        "top_failing_rules": top_fail,
        "all_results": normalized,  # NEW: đã là Rule
    }