# security_app/config.py
"""
Cấu hình/hằng số dùng chung toàn dự án.
Có thể mở rộng thêm khi cần (timeout, allowlist, marker, ...).
"""

# Dấu nhận diện dòng lệnh trong phần "check"
CMD_MARKER = "$ "

# Giới hạn số rule fail in phần "Top failing rules" khi in ra terminal
TOP_FAIL_LIMIT = 10

# Thư mục mặc định chứa logs theo phiên chạy
DEFAULT_LOGS_DIR = "logs"

# (dành cho tương lai) Timeout mặc định khi chạy lệnh shell (giây)
DEFAULT_SHELL_TIMEOUT = 0  # 0 = không áp timeout ở run_command hiện tại
