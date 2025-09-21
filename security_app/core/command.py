# security_app/core/command.py
from collections.abc import Mapping
import os, subprocess, time, random
from security_app.models import CmdResult
from security_app.policy.risk import compute_risk
from security_app.policy.safety import deny_reason, assert_cmd_length_safe
from security_app.utils.text import ellipsis_middle
from security_app.settings import Settings

_SAFE_ENV_BASE = {
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "HOME": "/nonexistent",
    "TZ": "UTC",
}
_BAD_ENV_PREFIXES = ("LD_", "DYLD_", "PYTHON", "GEM_", "BUNDLE_", "NODE_", "RUBY", "PERL", "JAVA_TOOL_OPTIONS")
_BAD_ENV_KEYS = {"SSH_AUTH_SOCK","HTTP_PROXY","HTTPS_PROXY","NO_PROXY","FTP_PROXY","ALL_PROXY","TMPDIR","TMP","TEMP"}

def _build_clean_env(parent: Mapping[str, str] | None) -> dict[str, str]:
    return dict(_SAFE_ENV_BASE)

def _run_once(cmd: str, timeout: float | None, settings: Settings) -> subprocess.CompletedProcess:
    cwd = settings.exec_cwd or "/"
    env = _build_clean_env(os.environ) if settings.clean_env else dict(os.environ)
    return subprocess.run(
        cmd, shell=True, text=True, capture_output=True,
        timeout=timeout if timeout and timeout > 0 else None,
        cwd=cwd, env=env, close_fds=True, start_new_session=True
    )

def _to_result(cmd: str, rc: int | None, stdout: str, stderr: str, started_all: float) -> CmdResult:
    return CmdResult(cmd=cmd, returncode=rc, stdout=stdout or "", stderr=stderr or "",
                     duration_sec=round(time.time() - started_all, 4), ok=(rc == 0))

def run_command(cmd: str, settings: Settings) -> CmdResult:
    risk = compute_risk(cmd)
    try:
        assert_cmd_length_safe(cmd)
    except Exception as e:
        return _to_result(cmd, None, "", f"DENIED length-check: {e} | RISK={risk.level}({risk.score}) {','.join(risk.factors)}", time.time())

    reason = deny_reason(cmd)
    if reason:
        return _to_result(cmd, None, "", f"{reason} | RISK={risk.level}({risk.score}) {','.join(risk.factors)}", time.time())

    max_attempts = 1 + max(0, int(settings.retry_attempts))
    timeout = float(settings.shell_timeout) if settings.shell_timeout else None

    attempts = 0
    started_all = time.time()
    base_delay = max(0.05, float(getattr(settings, "retry_delay_sec", 0.25)))

    while attempts < max_attempts:
        attempts += 1
        try:
            res = _run_once(cmd, timeout, settings)
            if res.returncode == 0 or attempts >= max_attempts:
                return _to_result(cmd, res.returncode, res.stdout, res.stderr, started_all)
            # backoff mũ + jitter
            sleep_s = min(2.0, base_delay * (2 ** (attempts - 1))) + random.uniform(0.0, 0.2)
            time.sleep(sleep_s)
        except subprocess.TimeoutExpired as te:
            if (not settings.retry_on_timeout) or attempts >= max_attempts:
                return _to_result(cmd, None, te.stdout or "", f"TIMEOUT after {timeout}s", started_all)
            sleep_s = min(2.5, base_delay * (2 ** (attempts - 1))) + random.uniform(0.0, 0.3)
            time.sleep(sleep_s)
        except Exception as e:
            if attempts >= max_attempts:
                return _to_result(cmd, None, "", str(e), started_all)
            sleep_s = min(1.5, base_delay * (2 ** (attempts - 1))) + random.uniform(0.0, 0.2)
            time.sleep(sleep_s)

    return _to_result(cmd, None, "", "Unknown error", started_all)
