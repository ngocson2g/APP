# security_app/models.py
from dataclasses import dataclass


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