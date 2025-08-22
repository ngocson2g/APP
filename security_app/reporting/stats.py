from collections import defaultdict

def _get(obj, attr, default=""):
    return getattr(obj, attr, default) if obj is not None else default

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
        sev = str(_get(rule, "severity") or _get(rule, "impact") or "unknown").lower()
        by_sev[sev]["rules"] += 1
        by_sev[sev]["cmds"]  += x["num_cmds"]
        by_sev[sev]["ok"]    += x["num_ok"]
        by_sev[sev]["fail"]  += x["num_fail"]
        if x["num_fail"] > 0:
            by_sev[sev]["rules_fail"] += 1

    top_fail = sorted(
        [
            (x["rule_index"], _get(x["rule"], "id") or str(x["rule_index"]),
             _get(x["rule"], "severity") or "", x["num_fail"], _get(x["rule"], "title") or "")
            for x in run_results if x["num_fail"] > 0
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
        },
        "by_severity": by_sev,
        "top_failing_rules": top_fail,
        "all_results": run_results
    }
