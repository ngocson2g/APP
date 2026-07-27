# security_app/core/runner/command_port.py
from __future__ import annotations

from typing import Protocol

from security_app.core.command import run_command as _default_run_command
from security_app.models import CmdResult
from security_app.settings import Settings


class CommandRunner(Protocol):
    """Port: triển khai thực thi lệnh. Chỉ 1 trách nhiệm."""
    def __call__(self, cmd: str, settings: Settings, rule_id : str) -> CmdResult: ...

def default_command_runner(cmd: str, settings: Settings, rule_id: str) -> CmdResult:
    """Triển khai mặc định: gọi core.command.run_command."""
    return _default_run_command(cmd, settings, rule_id)
