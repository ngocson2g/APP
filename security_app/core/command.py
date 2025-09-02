# security_app/core/command.py
import subprocess, time, os
from typing import Optional, Mapping
from security_app.models import CmdResult
from security_app.policy.safety import deny_reason
from security_app.policy.risk import compute_risk
from security_app.settings import Settings

_SAFE_ENV_BASE = {
    "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "HOME": "/nonexistent",
    "TZ": "UTC",
}


# Các prefix/key env nên loại bỏ để tránh can thiệp runtime/lib/toolchain/agent
_BAD_ENV_PREFIXES = ("LD_", "DYLD_", "PYTHON", "GEM_", "BUNDLE_", "NODE_", "RUBY", "PERL", "JAVA_TOOL_OPTIONS")
_BAD_ENV_KEYS = {
    "SSH_AUTH_SOCK", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "FTP_PROXY", "ALL_PROXY",
    "TMPDIR", "TMP", "TEMP",
}
def _build_clean_env(parent: Mapping[str, str] | None) -> dict[str, str]:
    # Bắt đầu từ base cố định; KHÔNG copy toàn bộ os.environ
    env = dict(_SAFE_ENV_BASE)
    # Nếu muốn giữ lại một vài biến whitelisted từ parent, có thể bổ sung tại đây (tuỳ policy)
    # Ví dụ: không giữ gì thêm để "sạch" đúng nghĩa.
    return env

def _run_once(cmd: str, timeout: Optional[float], settings: Settings) -> subprocess.CompletedProcess:
    cwd = settings.exec_cwd or "/"
    # env: sạch tối thiểu (mặc định). Nếu tắt clean_env -> thừa kế nguyên os.environ.
    env = _build_clean_env(os.environ) if settings.clean_env else dict(os.environ)

    return subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout if timeout and timeout > 0 else None,
        cwd=cwd,
        env=env,
        close_fds=True,
        start_new_session=True,  # tách session; tương tự setsid()
    )

def _to_result(
    cmd: str,
    rc: Optional[int],
    stdout: str,
    stderr: str,
    started_all: float,
) -> CmdResult:
    """
    Đóng gói về CmdResult, duration là tổng thời gian từ lần đầu tới lúc kết thúc (kể cả retry).
    """
    return CmdResult(
        cmd=cmd,
        returncode=rc,
        stdout=stdout or "",
        stderr=stderr or "",
        duration_sec=round(time.time() - started_all, 4),
        ok=(rc == 0),
    )

def run_command(cmd: str, settings: Settings) -> CmdResult:
    """
    Giữ vòng lặp retry & backoff dựa trên Settings (không đọc/mutate globals).
    """
    # Chặn lệnh nguy hiểm (nguồn sự thật)
    reason = deny_reason(cmd)          # nguồn sự thật cho block
    risk = compute_risk(cmd)           # vẫn chấm để log Risk
    if reason:
        return _to_result(cmd, None, "", f"{reason} | RISK={risk.level}({risk.score}) {','.join(risk.factors)}",
                          time.time())

    max_attempts = 1 + max(0, int(settings.retry_attempts))
    timeout = float(settings.shell_timeout) if settings.shell_timeout else None

    attempts = 0
    last_exc: Optional[BaseException] = None
    started_all = time.time()

    while attempts < max_attempts:
        attempts += 1
        try:
            res = _run_once(cmd, timeout, settings)
            # Thành công hoặc hết lượt retry -> trả kết quả luôn
            if res.returncode == 0 or attempts >= max_attempts:
                return _to_result(cmd, res.returncode, res.stdout, res.stderr, started_all)
            # Thất bại nhưng còn lượt -> backoff rồi thử lại
            time.sleep(settings.retry_delay_sec)
        except subprocess.TimeoutExpired as te:
            last_exc = te
            if (not settings.retry_on_timeout) or attempts >= max_attempts:
                return _to_result(cmd, None, te.stdout or "", f"TIMEOUT after {timeout}s", started_all)
            time.sleep(settings.retry_delay_sec)
        except Exception as e:
            last_exc = e
            if attempts >= max_attempts:
                return _to_result(cmd, None, "", str(e), started_all)
            time.sleep(settings.retry_delay_sec)

    # Phòng hờ (không nên tới đây)
    return _to_result(cmd, None, "", str(last_exc or "Unknown error"), started_all)

