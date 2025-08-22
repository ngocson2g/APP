# security_app/policy/secrets.py
"""
Secret masker: compile SECRET_REPLACERS một lần, mask nhanh hơn.
"""
from __future__ import annotations
import re
from typing import List, Tuple
from security_app.config import SECRET_REPLACERS

# Danh sách (pattern đã compile, replacement)
_COMPILED: List[Tuple[re.Pattern, str]] = [
    (re.compile(p, re.IGNORECASE), repl) for p, repl in SECRET_REPLACERS
]

def mask_secrets(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    for rx, repl in _COMPILED:
        s = rx.sub(repl, s)
    return s
