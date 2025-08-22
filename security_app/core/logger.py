from __future__ import annotations
import os, json, csv, datetime
from typing import List
from security_app.models import Rule, CmdResult
from security_app.utils.text import _safe_name
from security_app.policy.secrets import mask_secrets

class RunLogger:
    """
    Tạo cấu trúc logs/<run>/..., có summary.jsonl/csv
    """
    def __init__(self, base_dir: str = "logs", run_name: str | None = None):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = os.path.join(base_dir, run_name or ts)
        os.makedirs(self.run_dir, exist_ok=True)

        self.summary_jsonl_path = os.path.join(self.run_dir, "summary.jsonl")
        self.summary_csv_path   = os.path.join(self.run_dir, "summary.csv")
        self.meta_path          = os.path.join(self.run_dir, "meta.json")

        if not os.path.exists(self.meta_path):
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({"created_at": ts, "version": 1}, f, ensure_ascii=False, indent=2)

        self._ensure_csv_header()

    def _ensure_csv_header(self):
        if not os.path.exists(self.summary_csv_path):
            with open(self.summary_csv_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "rule_index","rule_id","title","severity","num_cmds","num_ok","num_fail"
                ])

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
            f.write(f"ID       : {rule_id}\n")
            f.write(f"Title    : {title}\n")
            f.write(f"Severity : {severity}\n")
            f.write("-" * 60 + "\n")
            f.write("Check (raw):\n")
            f.write(check_masked + "\n")
            f.write("-" * 60 + "\n\n")

            for i, r in enumerate(cmd_results, 1):
                f.write(f"[{i}] $ {mask_secrets(r.cmd)}\n")
                f.write(f"Return code : {r.returncode}\n")
                f.write(f"Duration(s) : {r.duration_sec}\n")
                f.write("---- STDOUT ----\n")
                f.write((mask_secrets(r.stdout or "")).rstrip() + "\n")
                f.write("---- STDERR ----\n")
                f.write((mask_secrets(r.stderr or "")).rstrip() + "\n")
                f.write("=" * 60 + "\n\n")

        num_cmds = len(cmd_results)
        num_ok   = sum(1 for r in cmd_results if r.ok)
        num_fail = num_cmds - num_ok

        summary_row = {
            "rule_index": rule_index, "rule_id": rule_id, "title": title, "severity": severity,
            "num_cmds": num_cmds, "num_ok": num_ok, "num_fail": num_fail,
            "per_rule_log": os.path.basename(per_rule_path)
        }
        with open(self.summary_jsonl_path, "a", encoding="utf-8") as jf:
            jf.write(json.dumps(summary_row, ensure_ascii=False) + "\n")

        with open(self.summary_csv_path, "a", newline="", encoding="utf-8") as cf:
            csv.writer(cf).writerow([rule_index, rule_id, title, severity, num_cmds, num_ok, num_fail])
