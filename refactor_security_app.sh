#!/usr/bin/env bash
set -euo pipefail

# 1) Kiểm tra vị trí
if [ ! -d "security_app" ]; then
  echo "❌ Hãy chạy script tại thư mục gốc dự án (nơi có folder security_app/)"
  exit 1
fi

# 2) Tạo utils/ và config.py
mkdir -p security_app/utils

cat > security_app/config.py <<'PY'
# security_app/config.py
"""
Cấu hình/hằng số dùng chung toàn dự án.
Có thể mở rộng thêm khi cần (timeout, allowlist, marker, ...).
"""

# Dấu nhận diện dòng lệnh trong phần "check"
CMD_MARKER = "$ "

# Giới hạn số rule fail in phần "Top failing rules" khi in ra terminal
TOP_FAIL_LIMIT = 10

# Thư mục mặc định chứa logs theo phiên chạy
DEFAULT_LOGS_DIR = "logs"

# (dành cho tương lai) Timeout mặc định khi chạy lệnh shell (giây)
DEFAULT_SHELL_TIMEOUT = 0  # 0 = không áp timeout ở run_command hiện tại
PY

cat > security_app/utils/__init__.py <<'PY'
# security_app/utils/__init__.py
# Để trống (đánh dấu package).
PY

cat > security_app/utils/text.py <<'PY'
# security_app/utils/text.py
import shutil
import re

def _term_width():
    return shutil.get_terminal_size((120, 20)).columns

def _safe_name(s: str, maxlen: int = 60) -> str:
    if not s:
        return "rule"
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())
    return (s[:maxlen]).strip("_") or "rule"

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
PY

# 3) Đổi tên core/extract.py -> core/command_extractor.py (nếu tồn tại extract.py)
if [ -f "security_app/core/extract.py" ]; then
  git mv security_app/core/extract.py security_app/core/command_extractor.py 2>/dev/null || mv security_app/core/extract.py security_app/core/command_extractor.py
fi

# 4) Ghi lại file core/command_extractor.py (idempotent – đảm bảo nội dung đúng)
cat > security_app/core/command_extractor.py <<'PY'
# security_app/core/command_extractor.py
from security_app.config import CMD_MARKER

def extract_all_commands(checktext: str):
    """
    Trích xuất các lệnh shell bắt đầu bằng marker (mặc định "$ ").
    Hỗ trợ dòng tiếp tục bằng dấu "\".
    Trả về danh sách lệnh (không kèm tiền tố marker).
    """
    if not checktext:
        return []

    lines = checktext.splitlines()
    i = 0
    cmds = []
    current = None  # accumulating command string or None
    marker = CMD_MARKER

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        # start of a new command
        if line.startswith(marker):
            # flush cái trước (nếu có)
            if current:
                cmds.append(current.strip())
                current = None

            # bắt đầu mới (strip marker)
            current = line[len(marker):].strip()

            # consume continuation lines
            while current.endswith("\\"):
                current = current[:-1].rstrip() + " "
                i += 1
                if i >= len(lines):
                    break
                next_line = lines[i].strip()
                if next_line.startswith(marker):
                    next_line = next_line[len(marker):].strip()
                current += next_line
        else:
            # không phải dòng lệnh; nếu đang có current thì chốt
            if current:
                cmds.append(current.strip())
                current = None

        i += 1

    if current:
        cmds.append(current.strip())

    return cmds
PY

# 5) Cập nhật runner.py để import từ command_extractor
cat > security_app/core/runner.py <<'PY'
from typing import List, Dict, Any
from security_app.models import Rule, CmdResult
from security_app.core.command import run_command
from security_app.core.command_extractor import extract_all_commands
from security_app.core.logger import RunLogger

def run_all_rules(rules: List[Rule], log_base_dir: str = "logs"):
    """
    Trả về danh sách dict để giữ tương thích với reporting:
      - rule: Rule
      - cmd_results: list[CmdResult]
    """
    logger = RunLogger(base_dir=log_base_dir)
    results: list[Dict[str, Any]] = []

    for idx, rule in enumerate(rules, start=1):
        cmds: List[str] = extract_all_commands(rule.check)
        cmd_results: List[CmdResult] = [run_command(cmd) for cmd in cmds]

        logger.log_rule_result(idx, rule, cmd_results)

        num_cmds = len(cmd_results)
        num_ok   = sum(1 for r in cmd_results if r.ok)
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
PY

# 6) Cập nhật logger.py để dùng _safe_name từ utils.text
cat > security_app/core/logger.py <<'PY'
from __future__ import annotations
import os, json, csv, datetime
from typing import List
from security_app.models import Rule, CmdResult
from security_app.utils.text import _safe_name

class RunLogger:
    """
    Tạo cấu trúc:
      logs/
        YYYY-MM-DD_HH-MM-SS/
          rule-001_<name>.log
          summary.jsonl
          summary.csv
          meta.json
    """
    def __init__(self, base_dir: str = "logs", run_name: str | None = None):
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

    def log_rule_result(self, rule_index: int, rule: Rule, cmd_results: List[CmdResult]):
        rule_id   = rule.id or str(rule_index)
        title     = rule.title or ""
        severity  = rule.severity or ""
        check_raw = rule.check or ""

        short = _safe_name(title or rule_id)
        per_rule_path = os.path.join(self.run_dir, f"rule-{rule_index:03d}_{short}.log")

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
                f.write(f"[{i}] $ {r.cmd}\n")
                f.write(f"Return code : {r.returncode}\n")
                f.write(f"Duration(s) : {r.duration_sec}\n")
                f.write("---- STDOUT ----\n")
                f.write((r.stdout or "").rstrip() + "\n")
                f.write("---- STDERR ----\n")
                f.write((r.stderr or "").rstrip() + "\n")
                f.write("=" * 60 + "\n\n")

        num_cmds = len(cmd_results)
        num_ok   = sum(1 for r in cmd_results if r.ok)
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

        with open(self.summary_csv_path, "a", newline="", encoding="utf-8") as cf:
            csv.writer(cf).writerow([rule_index, rule_id, title, severity, num_cmds, num_ok, num_fail])
PY

# 7) Cập nhật reporting/terminal.py để dùng utils.text
cat > security_app/reporting/terminal.py <<'PY'
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

    top_fail = sorted([x for x in run_results if x["num_fail"] > 0],
                      key=lambda r: (-r["num_fail"], r["rule_index"]))

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
PY

# 8) Cập nhật app/cli.py để dùng default từ config (không bắt buộc nhưng nhất quán)
cat > security_app/app/cli.py <<'PY'
import argparse
import os
from security_app.parsers.dispatch import parse_file
from security_app.core.runner import run_all_rules
from security_app.reporting.terminal import compute_stats, print_report
from security_app.config import DEFAULT_LOGS_DIR, TOP_FAIL_LIMIT

def main():
    parser = argparse.ArgumentParser(
        prog="security-app",
        description="Run STIG/Checklist and report results."
    )
    parser.add_argument(
        "input",
        help="Path to checklist file (CSV/JSON/XML)."
    )
    parser.add_argument(
        "--logs-dir", default=DEFAULT_LOGS_DIR,
        help=f"Base directory to store run logs (default: {DEFAULT_LOGS_DIR})"
    )
    parser.add_argument(
        "--top", type=int, default=TOP_FAIL_LIMIT,
        help=f"Show at most N failing rules in 'Top failing rules' (default: {TOP_FAIL_LIMIT})"
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        parser.error(f"Input not found: {args.input}")

    rules = parse_file(args.input)  # list[Rule]
    run_results = run_all_rules(rules, log_base_dir=args.logs_dir)
    stats = compute_stats(run_results)
    print_report(stats, limit_top=args.top)

if __name__ == "__main__":
    main()
PY

echo "✅ Refactor hoàn tất."
echo "👉 Gợi ý tiếp theo:"
echo "   1) pip install -e ."
echo "   2) security-app data/canonical_ubuntu_24.04_lts.csv --logs-dir logs"
echo "      (hoặc dùng --top 15 nếu muốn hiển thị nhiều rule fail hơn)"
