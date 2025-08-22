import shutil
from collections import defaultdict
from security_app.models import Rule
from security_app.utils.text import _term_width, _bar, _table
from security_app.config import TOP_FAIL_LIMIT

def _get(rule, key, default=""):
    # hỗ trợ cả dataclass Rule và dict cũ
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
    maxk = max(len(k) for k,_ in kv) + 2
    for k, v in kv:
        print(f"{k:>{maxk}}: {v}")
    print()

    if t["total_cmds"] == 0:
        print("⚠️  Không tìm thấy lệnh nào để thực thi (các dòng check phải bắt đầu bằng '$ ').\n")

    # ----- By severity -----
    print("By severity:")
    order = ["low","medium","moderate","high","critical","unknown"]
    rows, seen = [], set()
    for key in order:
        if key in stats["by_severity"]:
            v = stats["by_severity"][key]
            rows.append([
                key,
                str(v["rules"]),
                f"{v['rules']-v['rules_fail']} ok / {v['rules_fail']} fail",
                f"{v['ok']}/{v['cmds']}",
                str(v["fail"]),
                _bar(v["ok"], max(1, v["cmds"]))
            ])
            seen.add(key)
    for k, v in stats["by_severity"].items():
        if k in seen:
            continue
        rows.append([
            k,
            str(v["rules"]),
            f"{v['rules']-v['rules_fail']} ok / {v['rules_fail']} fail",
            f"{v['ok']}/{v['cmds']}",
            str(v["fail"]),
            _bar(v["ok"], max(1, v["cmds"]))
        ])
    _table(rows, headers=["Severity","Rules","#Rules OK/Fail","Cmd OK/Cmds","#Cmd Fail","OK bar"])
    print()

    # ----- Top failing rules -----
    print(f"Top failing rules (max {limit_top}):")
    top = stats["top_failing_rules"][:limit_top]
    tr = []
    for x in top:
        rule = x["rule"]
        tr.append([
            f"{x['rule_index']}",
            str(_get(rule, "id", "")),
            str(_get(rule, "severity") or _get(rule, "impact") or "unknown"),
            str(x["num_fail"]),
            (str(_get(rule, "title") or _get(rule, "name") or "") or "(no title)").strip()
        ])
    if tr:
        _table(tr, headers=["#","Rule ID","Sev","#CmdFail","Title"])
    else:
        print("(Không có rule lỗi)")
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