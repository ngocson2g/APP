# security_app/policy/safety.py
"""
Safety policy (denylist): compile một lần & dùng chung cho runner/command.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from security_app import settings
from security_app.config import CMD_DENYLIST
from security_app.utils.text import ellipsis_middle

# ===== Denylist =====
# dùng DOTALL để match cả lệnh nhiều dòng
COMPILED_DENY_RE = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in CMD_DENYLIST]

# NEW: danh sách trạng thái assessment bị chặn (theo yêu cầu trước đó)
RULE_DENY_ASSESSMENT_STATUS = {"manual", "na", "not_applicable"}  # có thể mở rộng qua config nếu muốn

def deny_reason(cmd: str) -> str | None:
    s = (cmd or "").strip()
    if not s:
        return "DENIED: empty command"
    for rx in COMPILED_DENY_RE:
        if rx.search(s):
            return f"DENIED by safety policy: matched /{rx.pattern}/i"
    return None

class SafetyError(ValueError):
    pass


# ===== Counters: pipe & redirect chính xác hơn =====
# Đếm '|' đơn (không tính '||')
_SINGLE_PIPE_RX = re.compile(r"(?<!\|)\|(?!\|)")
# Đếm redirect phổ biến: '>', '>>', '<', '1>', '2>', '&>', '2>&1', ...
_REDIRECT_RX = re.compile(r"(?:>>|[<>]|(?:\d>){1}|&>|2>&1)")

def _count_pipes(cmd: str) -> int:
    return len(_SINGLE_PIPE_RX.findall(cmd or ""))

def _count_redirects(cmd: str) -> int:
    return len(_REDIRECT_RX.findall(cmd or ""))


# ===== Metrics & Limits =====
@dataclass
class CmdMetrics:
    chars: int
    bytes: int
    argc: int
    pipes: int
    redirects: int
    lines: int
    max_line_len: int

@dataclass
class CmdLimits:
    # giữ nguyên hệ settings để không phá tương thích
    max_chars: int = settings.MAX_CMD_CHARS
    max_bytes: int = settings.MAX_CMD_BYTES
    max_args: int = settings.MAX_CMD_ARGS
    max_pipes: int = settings.MAX_CMD_PIPES
    max_redirects: int = settings.MAX_CMD_REDIRECTS
    max_lines: int = settings.MAX_CMD_LINES
    max_line_chars: int = settings.MAX_CMD_LINE_CHARS


def _calc_metrics(cmd: str) -> CmdMetrics:
    s = cmd or ""
    chars = len(s)
    b = len(s.encode("utf-8", errors="ignore"))
    try:
        argc = len(shlex.split(s, posix=True))
    except Exception:
        # Nếu lệnh hỏng quote -> coi như args nhiều để chặn sớm
        argc = settings.MAX_CMD_ARGS + 1
    pipes = _count_pipes(s)
    redirects = _count_redirects(s)
    lines_list = s.splitlines() or [s]
    lines = len(lines_list)
    max_line_len = max((len(l) for l in lines_list), default=0)
    return CmdMetrics(chars, b, argc, pipes, redirects, lines, max_line_len)


def check_cmd_length(cmd: str, limits: CmdLimits | None = None):
    """
    Trả về (ok: bool, reason: str, metrics: CmdMetrics).
    Dùng để chặn lệnh quá dài/trải rộng (pipes/redirects/dòng) gây nghẽn IO/log/stdin.
    """
    limits = limits or CmdLimits()
    m = _calc_metrics(cmd)

    reasons: list[str] = []
    if m.chars > limits.max_chars:
        reasons.append(f"chars {m.chars}>{limits.max_chars}")
    if m.bytes > limits.max_bytes:
        reasons.append(f"bytes {m.bytes}>{limits.max_bytes}")
    if m.argc > limits.max_args:
        reasons.append(f"argc {m.argc}>{limits.max_args}")
    if m.pipes > limits.max_pipes:
        reasons.append(f"pipes {m.pipes}>{limits.max_pipes}")
    if m.redirects > limits.max_redirects:
        reasons.append(f"redirects {m.redirects}>{limits.max_redirects}")
    if m.lines > limits.max_lines:
        reasons.append(f"lines {m.lines}>{limits.max_lines}")
    if m.max_line_len > limits.max_line_chars:
        reasons.append(f"line_len {m.max_line_len}>{limits.max_line_chars}")

    if reasons:
        reason = "too-long/complex: " + ", ".join(reasons)
        return False, reason, m
    return True, "ok", m


def assert_cmd_length_safe(cmd: str, limits: CmdLimits | None = None):
    ok, reason, metrics = check_cmd_length(cmd, limits)
    if not ok:
        short = ellipsis_middle(cmd or "", 200)
        raise SafetyError(f"{reason} :: {short}")
    return metrics
