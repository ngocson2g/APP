import subprocess, time, re
from typing import Optional
from security_app.models import CmdResult
from security_app.config import (
    DEFAULT_SHELL_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY_SEC, RETRY_ON_TIMEOUT,
    CMD_DENYLIST,
)

_DENY_RE = [re.compile(p, re.IGNORECASE) for p in CMD_DENYLIST]

def _deny_reason(cmd: str) -> Optional[str]:
    s = cmd.strip()
    for rx in _DENY_RE:
        if rx.search(s):
            return f"DENIED by safety policy: matched /{rx.pattern}/"
    return None

def run_command(cmd: str) -> CmdResult:
    # Chặn lệnh nguy hiểm
    reason = _deny_reason(cmd)
    if reason:
        return CmdResult(
            cmd=cmd, returncode=None, stdout="", stderr=reason,
            duration_sec=0.0, ok=False
        )

    attempts = 0
    max_attempts = 1 + max(0, int(RETRY_ATTEMPTS))
    timeout = None if not DEFAULT_SHELL_TIMEOUT else float(DEFAULT_SHELL_TIMEOUT)

    last_exc = None
    started_all = time.time()

    while attempts < max_attempts:
        attempts += 1
        started = time.time()
        try:
            res = subprocess.run(
                cmd, shell=True, text=True, capture_output=True, timeout=timeout
            )
            dur = time.time() - started
            ok = (res.returncode == 0)
            if ok or attempts >= max_attempts:
                return CmdResult(
                    cmd=cmd,
                    returncode=res.returncode,
                    stdout=res.stdout,
                    stderr=res.stderr,
                    duration_sec=round(time.time() - started_all, 4),
                    ok=ok,
                )
            # retry on non-zero
            time.sleep(RETRY_DELAY_SEC)
        except subprocess.TimeoutExpired as te:
            last_exc = te
            if not RETRY_ON_TIMEOUT or attempts >= max_attempts:
                dur = time.time() - started
                return CmdResult(
                    cmd=cmd, returncode=None, stdout=te.stdout or "",
                    stderr=f"TIMEOUT after {timeout}s", duration_sec=round(time.time() - started_all, 4), ok=False
                )
            time.sleep(RETRY_DELAY_SEC)
        except Exception as e:
            last_exc = e
            if attempts >= max_attempts:
                return CmdResult(
                    cmd=cmd, returncode=None, stdout="", stderr=str(e),
                    duration_sec=round(time.time() - started_all, 4), ok=False
                )
            time.sleep(RETRY_DELAY_SEC)

    # Fallback (hiếm khi tới đây)
    return CmdResult(
        cmd=cmd, returncode=None, stdout="", stderr=str(last_exc or "Unknown error"),
        duration_sec=round(time.time() - started_all, 4), ok=False
    )
