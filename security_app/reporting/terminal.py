import shutil
from collections import defaultdict

def _term_width():
    return shutil.get_terminal_size((120, 20)).columns

def _bar(value, total, width=20, ch="█"):
    if total <= 0: return ""
    n = max(0, min(width, int(round(value * width / total))))
    return ch * n + " " * (width - n)

def _table(rows, headers, max_width=None):
    if max_width is None:
        max_width = _term_width()
    cols = len(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            widths[i] = max(widths[i], len(str(r[i])))

    total_width = sum(widths) + 3 * (cols - 1)
    if total_width > max_width:
        overflow = total_width - max_width
        i = cols - 1
        widths[i] = max(8, widths[i] - overflow)

    def cut(s, w): s = str(s); return (s[:w-1] + "…") if len(s) > w else s

    print(" | ".join(cut(headers[i], widths[i]).ljust(widths[i]) for i in range(cols)))
    print("-+-".join("-"*widths[i] for i in range(cols)))
    for r in rows:
        print(" | ".join(cut(r[i], widths[i]).ljust(widths[i]) for i in range(cols)))

def compute_stats(run_results):
    total_rules = len(run_results)
    total_cmds  = sum(x["num_cmds"] for x in run_results)
    total_ok    = sum(x["num_ok"] for x in run_results)
    total_fail  = sum(x["num_fail"] for x in run_results)
    rules_all_ok = sum(1 for x in run_results if x["num_fail"] == 0)
    rules_with_fail = total_rules - rules_all_ok
    pass_rate = (rules_all_ok / total_rules * 100.0) if total_rules else 0.0

    by_sev = defaultdict(lambda: {"rules":0,"rules_fail":0,"cmds":0,"ok":0,"fail":0})
    for x in run_results:
        rule = x["rule"]
        sev = str(rule.get("severity") or rule.get("impact") or "unknown").lower()
        by_sev[sev]["rules"] += 1
        by_sev[sev]["cmds"]  += x["num_cmds"]
        by_sev[sev]["ok"]    += x["num_ok"]
        by_sev[sev]["fail"]  += x["num_fail"]
        if x["num_fail"] > 0:
            by_sev[sev]["rules_fail"] += 1

    top_fail = sorted(
        [x for x in run_results if x["num_fail"] > 0],
        key=lambda r: (-r["num_fail"], r["rule_index"])
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
        },
        "by_severity": by_sev,
        "top_failing_rules": top_fail,
        "all_results": run_results  # giữ lại để in danh sách ID
    }


def print_report(stats, limit_top=10):
    W = _term_width()
    print("=" * W)
    print("CHECKLIST EXECUTION SUMMARY".center(W))
    print("=" * W)

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

    # By severity
    print("By severity:")
    order = ["low","medium","moderate","high","critical","unknown"]
    rows = []
    seen = set()
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
        if k in seen: continue
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

    # Top failing rules
    print(f"Top failing rules (max {limit_top}):")
    top = stats["top_failing_rules"][:limit_top]
    tr = []
    for x in top:
        rule = x["rule"]
        tr.append([
            f"{x['rule_index']}",
            str(rule.get("id", "")),
            str(rule.get("severity") or rule.get("impact") or "unknown"),
            str(x["num_fail"]),
            (str(rule.get("title") or rule.get("name") or "") or "(no title)").strip()
        ])
    if tr:
        _table(tr, headers=["#","Rule ID","Sev","#CmdFail","Title"])
    else:
        print("(Không có rule lỗi)")
    print()

    # ==== Thêm phần liệt kê Rule ID ====
    all_results = stats["all_results"]  # danh sách run_results từ compute_stats
    fail_ids = [str(r["rule"].get("id", r["rule_index"])) for r in all_results if r["num_fail"] > 0]
    ok_ids   = [str(r["rule"].get("id", r["rule_index"])) for r in all_results if r["num_fail"] == 0]

    print(f"Failing Rule IDs ({len(fail_ids)}):")
    print(", ".join(fail_ids))
    print()
    print(f"OK Rule IDs ({len(ok_ids)}):")
    print(", ".join(ok_ids))
    print()
