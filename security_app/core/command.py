# security_app/core/command.py
import subprocess
import time
from typing import Optional
from security_app.models import CmdResult
from security_app.config import (
    DEFAULT_SHELL_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY_SEC, RETRY_ON_TIMEOUT,
)
from security_app.policy.safety import deny_reason


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


def _to_result(cmd: str,
               rc: Optional[int],
               stdout: str,
               stderr: str,
               started_all: float) -> CmdResult:
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


def run_command(cmd: str) -> CmdResult:
    """
    Giữ vòng lặp retry & backoff. Dùng _run_once và _to_result.
    """
    # Chặn lệnh nguy hiểm (nguồn sự thật)
    reason = deny_reason(cmd)
    if reason:
        return _to_result(cmd, None, "", reason, time.time())

    max_attempts = 1 + max(0, int(RETRY_ATTEMPTS))
    timeout = float(DEFAULT_SHELL_TIMEOUT) if DEFAULT_SHELL_TIMEOUT else None

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
            time.sleep(RETRY_DELAY_SEC)
        except subprocess.TimeoutExpired as te:
            last_exc = te
            if not RETRY_ON_TIMEOUT or attempts >= max_attempts:
                return _to_result(cmd, None, te.stdout or "", f"TIMEOUT after {timeout}s", started_all)
            time.sleep(RETRY_DELAY_SEC)
        except Exception as e:
            last_exc = e
            if attempts >= max_attempts:
                return _to_result(cmd, None, "", str(e), started_all)
            time.sleep(RETRY_DELAY_SEC)

    # Phòng hờ (không nên tới đây)
    return _to_result(cmd, None, "", str(last_exc or "Unknown error"), started_all)
