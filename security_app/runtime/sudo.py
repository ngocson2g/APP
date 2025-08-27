#security_app/runtime/sudo.py
from __future__ import annotations
import os, sys, shutil

def _needs_root() -> bool:
    # chỉ POSIX mới có geteuid; nếu đã là root thì bỏ qua
    return os.name == "posix" and hasattr(os, "geteuid") and os.geteuid() != 0

def _preserve_env_flags() -> list[str]:
    keep = [v for v in ("PATH", "LOGS_DIR") if os.getenv(v)]
    return [f"--preserve-env={','.join(keep)}"] if keep else []

def _resolve_entrypoint(argv0: str) -> str:
    # ưu tiên entrypoint trong venv (nếu có), fallback argv[0]
    return shutil.which("security-app") or argv0

def reexec_with_sudo(argv: list[str] | None = None) -> "NoReturn":  # type: ignore[name-defined]
    args = list(sys.argv if argv is None else argv)
    script = _resolve_entrypoint(args[0])
    flags = _preserve_env_flags()
    os.execvp("sudo", ["sudo", *flags, script, *args[1:]])

def ensure_root(required: bool = True) -> None:
    if required and _needs_root():
        reexec_with_sudo()
