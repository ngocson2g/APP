# security_app/models.py
from dataclasses import dataclass
from typing import Optional

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
    # Một số nguồn có 'title'/'name' — không bắt buộc
    title: str = ""

@dataclass
class CmdResult:
    """
    Kết quả thực thi 1 lệnh shell.
    """
    cmd: str
    returncode: Optional[int]
    stdout: str
    stderr: str
    duration_sec: float
    ok: bool
