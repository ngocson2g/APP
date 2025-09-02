#security_app/reporting/terminal.py
from security_app.models import Rule
from security_app.utils.text import _term_width, _bar, _table
from security_app.config import TOP_FAIL_LIMIT

def _get(rule, key, default=""):
    if isinstance(rule, Rule):
        return getattr(rule, key, default)
    if isinstance(rule, dict):
        return rule.get(key, default)
    return default

def print_report(stats, limit_top=TOP_FAIL_LIMIT):
    W = _term_width()
    print("=" * W)
    print("CHECKLIST EXECUTION SUMMARY".center(W))
    print("=" * W)

    # ----- Totals -----
    t = stats["totals"]
    kv = [
        ("Total rules", t["total_rules"]),
        ("All OK", t["rules_all_ok"]),
        ("With failures", t["rules_with_fail"]),
        ("Pass rate", f"{t['pass_rate']:.2f}%"),
        ("Total commands", t["total_cmds"]),
        ("Commands OK", t["total_ok"]),
        ("Commands failed", t["total_fail"]),
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
    for sev in sev_order + sorted([s for s in by_sev.keys() if s not in sev_order]):
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
        cmds = x.get("cmd_results") or []
        nd = sum(1 for r in cmds if "DENIED" in (getattr(r, "stderr", "") or "").upper())
        if nd > 0:
            rid = _get(x["rule"], "id", x["rule_index"])
            sev = _get(x["rule"], "severity", "")
            title = _get(x["rule"], "title", "")
            denied_rows.append([rid, sev, nd, title])

    if denied_rows:
        print("Denied by safety policy:")
        _table(denied_rows, headers=["Rule ID","Sev","#Denied","Title"])
        print()


    # ----- Danh sách ID -----
    all_results = stats["all_results"]
    fail_ids = [str(_get(r["rule"], "id", r["rule_index"])) for r in all_results if r["num_fail"] > 0]
    ok_ids   = [str(_get(r["rule"], "id", r["rule_index"])) for r in all_results if r["num_fail"] == 0]

    print(f"Failing Rule IDs ({len(fail_ids)}):")
    print(", ".join(fail_ids))
    print()
    print(f"OK Rule IDs ({len(ok_ids)}):")
    print(", ".join(ok_ids))
    print()

