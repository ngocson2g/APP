# security_app/config.py
"""
Cấu hình/hằng số toàn cục cho ứng dụng
- Các hằng số hệ thống
- Cấu hình mặc định
- Denylist và security patterns
"""
# Dấu nhận diện dòng lệnh trong phần "check"
CMD_MARKER = "$ "

# Giới hạn số rule fail in phần "Top failing rules" khi in ra terminal
TOP_FAIL_LIMIT = 10

# Thư mục mặc định chứa logs theo phiên chạy
DEFAULT_LOGS_DIR = "logs"

# Số thư mục run gần nhất cần giữ lại trong DEFAULT_LOGS_DIR
LOG_ROTATE_KEEP = 50

# Timeout mặc định khi chạy lệnh shell (giây). 0 = không timeout.
DEFAULT_SHELL_TIMEOUT = 10

# Retry cơ bản
RETRY_ATTEMPTS   = 1         # số lần thử lại (không tính lần đầu)
RETRY_DELAY_SEC  = 0.5       # backoff cố định giữa các lần thử
RETRY_ON_TIMEOUT = True      # có retry khi timeout không

# Danh sách mẫu lệnh bị chặn (regex, không phân biệt hoa thường)
CMD_DENYLIST = [
    r"\brm\s+-rf\s+/\b",
    r":\(\)\s*{\s*:\|\:&\s*};\s*:",       # fork bomb
    r"\bshutdown\b", r"\breboot\b",
    r"\bmkfs\.", r"\bdd\s+if=", r"\bdd\s+of=/dev/",
    r"\bchown\s+-R\s+root\b",
    r"\bpasswd\b", r"\buseradd\b\s+.*\s+-p\b",
    r"\bmount\b\s+.*",
    r"\bnohup\b\s+.*&",
    r"\bcurl\b\s+.*\|\s*sh\b",
    r"\bwget\b\s+.*\|\s*sh\b",
]

# Mẫu secret để mask trong log (regex → replacement)
SECRET_REPLACERS = [
    (r"(?i)\b(password|passwd)\s*[:=]\s*([^\s'\"\\]+)", r"\1=******"),
    (r"(?i)\b(token|apikey|api_key|secret)\s*[:=]\s*([A-Za-z0-9._-]{6,})", r"\1=******"),
    (r"(?i)bearer\s+([A-Za-z0-9._-]+)", "Bearer ******"),
    (r"(?i)sshpass\s+-p\s+(\S+)", "sshpass -p ******"),
    (r"(?i)--password\s+(\S+)", "--password ******"),
]

