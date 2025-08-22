# security_app/policy/safety.py
"""
Safety policy (denylist): compile một lần & dùng chung cho runner/command.
"""
from __future__ import annotations
import re
from typing import Optional
from security_app.config import CMD_DENYLIST

# Compile 1 lần (mỗi process)
COMPILED_DENY_RE = [re.compile(p, re.IGNORECASE) for p in CMD_DENYLIST]

def deny_reason(cmd: str) -> Optional[str]:
    """
    Trả về lý do bị chặn nếu 'cmd' match denylist; ngược lại None.
    """
    s = (cmd or "").strip()
    if not s:
        return "DENIED: empty command"
    for rx in COMPILED_DENY_RE:
        if rx.search(s):
            return f"DENIED by safety policy: matched /{rx.pattern}/"
    return None
