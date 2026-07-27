# security_app/runtime/netinfo.py
from __future__ import annotations

import socket
import subprocess


def primary_ipv4() -> str:
    """Lấy IPv4 chính (không loopback). Không cần internet, không gửi gói ra ngoài."""
    try:
        # Cách phổ biến, không thực sự gửi dữ liệu
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))      # chỉ dùng để OS chọn interface/source IP
        ip = s.getsockname()[0]
        s.close()
        if ip and ip != "127.0.0.1":
            return ip
    except OSError as e:
        from security_app.utils.log import internal_logger
        internal_logger.debug(f"Socket connection failed: {e}")
    # Fallback khi không có route mặc định / offline
    try:
        out = subprocess.check_output(
            ["sh", "-lc", "hostname -I | awk '{print $1}'"], text=True
        ).strip()
        if out and out.split()[0] != "127.0.0.1":
            return out.split()[0]
    except (OSError, subprocess.CalledProcessError) as e:
        from security_app.utils.log import internal_logger
        internal_logger.debug(f"Fallback hostname command failed: {e}")
    return "unknown"
