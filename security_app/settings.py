# security_app/settings.py
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    shell_timeout: float | None
    retry_attempts: int
    retry_delay_sec: float
    retry_on_timeout: bool

def default_settings() -> "Settings":
    import security_app.config as cfg
    return Settings(
        shell_timeout=float(cfg.DEFAULT_SHELL_TIMEOUT) if cfg.DEFAULT_SHELL_TIMEOUT else None,
        retry_attempts=int(cfg.RETRY_ATTEMPTS),
        retry_delay_sec=float(cfg.RETRY_DELAY_SEC),
        retry_on_timeout=bool(cfg.RETRY_ON_TIMEOUT),
    )

def with_overrides(base: "Settings",
                   shell_timeout: float | None = None,
                   retry_attempts: int | None = None) -> "Settings":
    return Settings(
        shell_timeout=base.shell_timeout if shell_timeout is None else (float(shell_timeout) if shell_timeout else None),
        retry_attempts=base.retry_attempts if retry_attempts is None else max(0, int(retry_attempts)),
        retry_delay_sec=base.retry_delay_sec,
        retry_on_timeout=base.retry_on_timeout,
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

