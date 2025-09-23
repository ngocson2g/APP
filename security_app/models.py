# security_app/models.py
"""
Data models cho ứng dụng
- Rule: Biểu diễn một security rule
- CmdResult: Kết quả thực thi command
- RuleLogRecord: Record log cho rule
- Settings: Cấu hình runtime
"""
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Rule:
    """
    Mô hình 1 rule đã chuẩn hoá sau khi parse.
    """
    id: str
    description: str
    check: str
    fix: str
    severity: str
    title: str = "" 
    assessment_status: str = ""   # NEW: metadata để deny theo trạng thái

@dataclass
class CmdResult:
    """
    Kết quả thực thi 1 lệnh shell.
    """
    cmd: str
    returncode: int | None
    stdout: str
    stderr: str
    duration_sec: float
    ok: bool

@dataclass(frozen=True)
class RuleLogRecord:
    """
    Bản ghi log cho 1 rule (đã mask secret).
    Dùng để định dạng/ghi ra file per-rule.
    """
    index: int
    rule_id: str
    title: str
    severity: str
    check_masked: str
    cmds: list[CmdResult]

@dataclass(frozen=True)
class Settings:
    shell_timeout: float | None
    retry_attempts: int
    retry_delay_sec: float
    retry_on_timeout: bool
    exec_cwd: str | None = None          # CWD cho subprocess; None -> dùng "/"
    clean_env: bool = True               # bật môi trường sạch tối thiểu cho subprocess
    
# ---------- NEW: LSP helper ----------
def as_rule(rule_like: Any) -> Rule:
    """
    Chuẩn hoá mọi 'rule-like' (Rule | dict | obj có thuộc tính) về dataclass Rule.
    Trường thiếu → "" (an toàn cho báo cáo); severity luôn lower().
    """
    if isinstance(rule_like, Rule):
        return rule_like

    def _pick(d: Mapping[str, Any], *keys: str) -> str:
        for k in keys:
            if k in d and d[k] is not None:
                v = str(d[k]).strip()
                if v:
                    return v
        return ""

    # Mapping (dict/TypedDict…)
    if isinstance(rule_like, Mapping):
        d = rule_like  # type: ignore[assignment]
        return Rule(
            id=_pick(d, "id", "rule_id", "vuln_id", "control", "ref_id", "vuln_num"),
            description=_pick(d, "description", "desc", "discussion", "rationale", "summary", "details"),
            check=_pick(d, "check", "checktext", "check_text", "check-content", "audit", "command", "commands"),
            fix=_pick(d, "fix", "fixtext", "fix_text", "remediation", "solution"),
            severity=(_pick(d, "severity", "impact", "level") or "").lower(),
            title=_pick(d, "title", "name", "rule_title"),
            assessment_status=(_pick(d, "assessment_status", "status") or "").lower(),
        )

    # Bất kỳ object có thuộc tính id/… (SimpleNamespace, ORM…)
    return Rule(
        id=str(getattr(rule_like, "id", "") or ""),
        description=str(getattr(rule_like, "description", "") or ""),
        check=str(getattr(rule_like, "check", "") or ""),
        fix=str(getattr(rule_like, "fix", "") or ""),
        severity=str(getattr(rule_like, "severity", "") or "").lower(),
        title=str(getattr(rule_like, "title", "") or ""),
        assessment_status=str(getattr(rule_like, "assessment_status", "") or "").lower(),
    )
# ---------- /NEW ----------