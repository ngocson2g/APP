from __future__ import annotations
import os, datetime, shutil
from typing import List
from security_app.models import Rule, CmdResult
from security_app.utils.text import _safe_name
from security_app.policy.secrets import mask_secrets
import security_app.config as cfg

class RunLogger:
    """
    Ghi log theo từng rule (1 file/1 rule) và KHÔNG ghi summary JSONL/CSV.
    - logs/<run>/rule-XXX_<safe_title>.log

    Kèm log rotation ở cấp độ "run": chỉ giữ lại N run gần nhất trong base_dir (mặc định 20).
    """

    def __init__(self, base_dir: str = "logs", run_name: str | None = None, keep_runs: int | None = None):
        self.base_dir = base_dir
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.run_dir = os.path.join(base_dir, run_name or ts)
        os.makedirs(self.run_dir, exist_ok=True)

        # enforce log rotation (giữ lại N run gần nhất)
        keep = cfg.LOG_ROTATE_KEEP if keep_runs is None else int(keep_runs)
        self._rotate_old_runs(keep)

    def _rotate_old_runs(self, keep: int):
        """
        Xoá các thư mục run cũ trong self.base_dir, chỉ giữ lại 'keep' run mới nhất.
        Sắp xếp theo mtime (gần nhất trước). Bỏ qua file lẻ, chỉ xét thư mục.
        """
        try:
            if keep is None or keep <= 0:
                return
            if not os.path.isdir(self.base_dir):
                return

            items: list[tuple[float, str]] = []
            for name in os.listdir(self.base_dir):
                path = os.path.join(self.base_dir, name)
                if not os.path.isdir(path):
                    continue
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    mtime = 0.0
                items.append((mtime, path))

            # mới nhất → cũ nhất
            items.sort(key=lambda t: t[0], reverse=True)

            # các run cần xoá (bỏ qua 'keep' cái đầu)
            to_delete = [p for _, p in items[keep:]]
            for p in to_delete:
                # không xoá nhầm run hiện tại
                if os.path.abspath(p) == os.path.abspath(self.run_dir):
                    continue
                try:
                    shutil.rmtree(p)
                except Exception:
                    # im lặng bỏ qua nếu không xoá được (quyền, đang mở, v.v.)
                    pass
        except Exception:
            # an toàn: không để rotation làm gãy chương trình chính
            pass

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
