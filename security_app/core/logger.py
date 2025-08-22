from __future__ import annotations
import os, datetime
from typing import List
from security_app.models import Rule, CmdResult
from security_app.utils.text import _safe_name
from security_app.policy.secrets import mask_secrets

class RunLogger:
    """
    Ghi log theo từng rule (1 file/1 rule) và KHÔNG ghi summary JSONL/CSV.
    - logs/<run>/rule-XXX_<safe_title>.log
    """
    def __init__(self, base_dir: str = "logs", run_name: str | None = None):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = os.path.join(base_dir, run_name or ts)
        os.makedirs(self.run_dir, exist_ok=True)

    def log_rule_result(self, rule_index: int, rule: Rule, cmd_results: List[CmdResult]):
        rule_id   = rule.id or str(rule_index)
        title     = rule.title or ""
        severity  = rule.severity or ""
        check_raw = rule.check or ""

        short = _safe_name(title or rule_id)
        per_rule_path = os.path.join(self.run_dir, f"rule-{rule_index:03d}_{short}.log")

        # Mask check trước khi ghi
        check_masked = mask_secrets(check_raw)

        with open(per_rule_path, "w", encoding="utf-8") as f:
            f.write(f"Rule #{rule_index}\n")
            f.write(f"ID     : {rule_id}\n")
            f.write(f"Title  : {title}\n")
            f.write(f"Severity: {severity}\n")
            f.write("---- Check ----\n")
            f.write(check_masked + "\n\n")
            f.write("---- Command Results ----\n")

            for r in cmd_results:
                f.write(f"$ {r.cmd}\n")
                f.write(f"RC={r.returncode} | OK={r.ok} | {r.duration_sec:.3f}s\n")
                if r.stdout:
                    f.write("-- stdout --\n")
                    f.write(str(r.stdout).rstrip() + "\n")
                if r.stderr:
                    f.write("-- stderr --\n")
                    f.write(str(r.stderr).rstrip() + "\n")
                f.write("\n")