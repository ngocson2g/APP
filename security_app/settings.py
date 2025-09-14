# security_app/settings.py
"""
Quản lý application settings và overrides
"""
from security_app.models import Settings

# --- Command length guard (IO-safety) ---
import os

MAX_CMD_CHARS = int(os.getenv("SECAPP_MAX_CMD_CHARS", "1200"))          # tổng ký tự
MAX_CMD_BYTES = int(os.getenv("SECAPP_MAX_CMD_BYTES", "4096"))          # tổng bytes UTF-8
MAX_CMD_ARGS = int(os.getenv("SECAPP_MAX_CMD_ARGS", "64"))              # số args sau shlex.split()
MAX_CMD_PIPES = int(os.getenv("SECAPP_MAX_CMD_PIPES", "8"))             # số '|' trong lệnh
MAX_CMD_REDIRECTS = int(os.getenv("SECAPP_MAX_CMD_REDIRECTS", "4"))     # '>' '<' tổng
MAX_CMD_LINES = int(os.getenv("SECAPP_MAX_CMD_LINES", "20"))            # tổng dòng
MAX_CMD_LINE_CHARS = int(os.getenv("SECAPP_MAX_CMD_LINE_CHARS", "800")) # độ dài 1 dòng


def default_settings() -> "Settings":
    import security_app.config as cfg
    return Settings(
        shell_timeout=float(cfg.DEFAULT_SHELL_TIMEOUT) if cfg.DEFAULT_SHELL_TIMEOUT else None,
        retry_attempts=int(cfg.RETRY_ATTEMPTS),
        retry_delay_sec=float(cfg.RETRY_DELAY_SEC),
        retry_on_timeout=bool(cfg.RETRY_ON_TIMEOUT),
        # NEW defaults:
        exec_cwd="/",
        clean_env=True,
    )

def with_overrides(base: "Settings",
                   shell_timeout: float | None = None,
                   retry_attempts: int | None = None,
                   # NEW:
                   exec_cwd: str | None = None,
                   clean_env: bool | None = None) -> "Settings":
    return Settings(
        shell_timeout=base.shell_timeout if shell_timeout is None else (float(shell_timeout) if shell_timeout else None),
        retry_attempts=base.retry_attempts if retry_attempts is None else max(0, int(retry_attempts)),
        retry_delay_sec=base.retry_delay_sec,
        retry_on_timeout=base.retry_on_timeout,
        exec_cwd=base.exec_cwd if exec_cwd is None else exec_cwd or "/",
        clean_env=base.clean_env if clean_env is None else bool(clean_env),
    )

# --- SUDO default policy ---
def require_sudo_by_default() -> bool:
    """
    Trả về True nếu mặc định yêu cầu sudo khi chạy CLI.
    - Ưu tiên ENV SECURITY_APP_REQUIRE_SUDO (1/true/yes vs 0/false/no)
    - Nếu không đặt ENV -> mặc định True (bật).
    """
    import os
    val = os.getenv("SECURITY_APP_REQUIRE_SUDO")
    if val is None:
        return True
    v = val.strip().lower()
    return v not in ("0", "false", "no", "off")

