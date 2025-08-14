from security_app.core.command import run_command
from security_app.core.logger import RunLogger
from security_app.core.extract import extract_all_commands

def run_all_rules(rules, log_base_dir="logs"):
    """
    Chạy toàn bộ rule, lưu log, và trả về danh sách kết quả:
    [
      {
        "rule_index": int,
        "rule": dict,
        "cmd_results": [
           {"cmd": str, "returncode": int|None, "stdout": str, "stderr": str, "duration_sec": float, "ok": bool}
        ],
        "per_rule_log": "rule-001_xxx.log",
        "num_cmds": int, "num_ok": int, "num_fail": int
      }, ...
    ]
    """
    logger = RunLogger(base_dir=log_base_dir)
    results = []

    for idx, rule in enumerate(rules, start=1):
        cmds = extract_all_commands(rule.get('check', ''))
        cmd_results = [run_command(cmd) for cmd in cmds]

        # Lưu log theo từng rule
        logger.log_rule_result(idx, rule, cmd_results)

        num_cmds = len(cmd_results)
        num_ok   = sum(1 for r in cmd_results if r.get("ok"))
        num_fail = num_cmds - num_ok

        results.append({
            "rule_index": idx,
            "rule": rule,
            "cmd_results": cmd_results,
            "per_rule_log": f"rule-{idx:03d}_",
            "num_cmds": num_cmds,
            "num_ok": num_ok,
            "num_fail": num_fail
        })

    return results
