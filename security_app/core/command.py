# security_app/core/command.py
import subprocess
import time
from typing import Optional
from security_app.models import CmdResult
from security_app.policy.safety import deny_reason
from security_app.settings import Settings

def _run_once(cmd: str, timeout: Optional[float]) -> subprocess.CompletedProcess:
    """
    Chạy 1 lần, trả về CompletedProcess; để Exception (TimeoutExpired, ...) nổi lên cho caller xử lý.
    """
    return subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout if timeout and timeout > 0 else None,
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
    reason = deny_reason(cmd)
    if reason:
        return _to_result(cmd, None, "", reason, time.time())

    max_attempts = 1 + max(0, int(settings.retry_attempts))
    timeout = float(settings.shell_timeout) if settings.shell_timeout else None

    attempts = 0
    last_exc: Optional[BaseException] = None
    started_all = time.time()

    while attempts < max_attempts:
        attempts += 1
        try:
            res = _run_once(cmd, timeout)
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

