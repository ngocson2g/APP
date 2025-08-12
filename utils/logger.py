import os, json, csv, re, datetime
from typing import List, Dict, Any, Optional

def _safe_name(s: str, maxlen: int = 60) -> str:
    if not s:
        return "rule"
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())
    return (s[:maxlen]).strip("_") or "rule"

class RunLogger:
    """
    Tạo cấu trúc:
      logs/
        2025-08-12_14-05-33/
          rule-001_<name>.log         # log chi tiết của rule
          summary.jsonl               # mỗi dòng 1 rule (tổng hợp)
          summary.csv                 # tổng hợp dạng CSV
          meta.json                   # thông tin phiên chạy
    """
    def __init__(self, base_dir: str = "logs", run_name: Optional[str] = None):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = os.path.join(base_dir, run_name or ts)
        os.makedirs(self.run_dir, exist_ok=True)

        self.summary_jsonl_path = os.path.join(self.run_dir, "summary.jsonl")
        self.summary_csv_path   = os.path.join(self.run_dir, "summary.csv")
        self.meta_path          = os.path.join(self.run_dir, "meta.json")

        # Ghi meta lần đầu
        if not os.path.exists(self.meta_path):
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "created_at": ts,
                    "version": 1
                }, f, ensure_ascii=False, indent=2)

        # Chuẩn bị CSV header
        self._ensure_csv_header()

    def _ensure_csv_header(self):
        if not os.path.exists(self.summary_csv_path):
            with open(self.summary_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "rule_index", "rule_id", "title", "severity",
                    "num_cmds", "num_ok", "num_fail"
                ])

    def log_rule_result(
        self,
        rule_index: int,
        rule: Dict[str, Any],
        cmd_results: List[Dict[str, Any]]
    ):
        # Lấy thông tin rule (tùy cấu trúc của bạn, đặt mặc định an toàn)
        rule_id   = str(rule.get("id", rule_index))
        title     = str(rule.get("title", "")) or str(rule.get("name", ""))
        severity  = str(rule.get("severity", rule.get("impact", "")))
        check_raw = str(rule.get("check", ""))

        # Tên file per-rule
        short = _safe_name(title or rule_id)
        per_rule_path = os.path.join(
            self.run_dir,
            f"rule-{rule_index:03d}_{short}.log"
        )

        # Ghi file chi tiết cho rule
        with open(per_rule_path, "w", encoding="utf-8") as f:
            f.write(f"Rule #{rule_index}\n")
            f.write(f"ID       : {rule_id}\n")
            f.write(f"Title    : {title}\n")
            f.write(f"Severity : {severity}\n")
            f.write("-" * 60 + "\n")
            f.write("Check (raw):\n")
            f.write(check_raw + "\n")
            f.write("-" * 60 + "\n\n")

            for i, r in enumerate(cmd_results, 1):
                f.write(f"[{i}] $ {r['cmd']}\n")
                f.write(f"Return code : {r['returncode']}\n")
                f.write(f"Duration(s) : {r['duration_sec']}\n")
                f.write("---- STDOUT ----\n")
                f.write((r['stdout'] or "").rstrip() + "\n")
                f.write("---- STDERR ----\n")
                f.write((r['stderr'] or "").rstrip() + "\n")
                f.write("=" * 60 + "\n\n")

        # Ghi summary JSONL (1 dòng/rule)
        num_cmds = len(cmd_results)
        num_ok   = sum(1 for r in cmd_results if r.get("ok"))
        num_fail = num_cmds - num_ok

        summary_row = {
            "rule_index": rule_index,
            "rule_id": rule_id,
            "title": title,
            "severity": severity,
            "num_cmds": num_cmds,
            "num_ok": num_ok,
            "num_fail": num_fail,
            "per_rule_log": os.path.basename(per_rule_path)
        }
        with open(self.summary_jsonl_path, "a", encoding="utf-8") as jf:
            jf.write(json.dumps(summary_row, ensure_ascii=False) + "\n")

        # Ghi summary CSV
        with open(self.summary_csv_path, "a", newline="", encoding="utf-8") as cf:
            writer = csv.writer(cf)
            writer.writerow([
                rule_index, rule_id, title, severity, num_cmds, num_ok, num_fail
            ])
