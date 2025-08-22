# security_app/policy/secrets.py
"""
Secret masker – single source of truth.
Compile pattern một lần để tăng hiệu năng.
"""
from __future__ import annotations
import re
from typing import List, Tuple
from security_app.config import SECRET_REPLACERS

# compile: List[Tuple[Pattern, str]]
_COMPILED: List[Tuple[re.Pattern, str]] = [
    (re.compile(p, re.IGNORECASE), repl) for p, repl in SECRET_REPLACERS
]

def mask_secrets(text: str) -> str:
    if not text:
        return text
    s = str(text)
    for rx, repl in _COMPILED:
        s = rx.sub(repl, s)
    return s