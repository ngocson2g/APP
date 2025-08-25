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
