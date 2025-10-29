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

# ---- LPT / Chunking / Waves (mặc định) ----
# Ngưỡng nhận diện lệnh "ngắn"
CHUNK_SHORT_THRESHOLD = 0.15   # giây
# Kích thước chunk mặc định cho lệnh ngắn
CHUNK_SIZE_DEFAULT = 4
# Kích thước sóng (wave) để auto-tuning giữa các đợt submit
LPT_WAVE_MIN = 200
LPT_WAVE_MAX = 500


# Danh sách mẫu lệnh bị chặn (regex, không phân biệt hoa thường)
CMD_DENYLIST = [
    # Xóa hệ thống & dữ liệu
    r"rm\s+-(?:rf|fr)\s+/(?:$|\s)",               # rm -rf /
    r"dd\s+if=.*\s+of=/dev/(?:sd|hd)",            # dd if=... of=/dev/sdX|hdX
    r"(?:^|\s)(?:mkfs\.[A-Za-z0-9]+|fdisk\s+/dev/)",   # mkfs.* hoặc fdisk /dev/...
    r">\s*/(?:etc|boot|root|home)(?:/|\s|$)",       # redirect ghi đè vào đường dẫn trọng yếu

    # Fork bomb & tấn công tài nguyên
    r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*(?:&|;)\s*\}\s*;?\s*:", # bash fork bomb ::(){ :|:& };: or ::(){ :|:; };:
    r"python\d?\s+-c\s+.*os\.fork",               # python -c '...os.fork...'

    # Quản trị hệ thống & khởi động lại
    r"\bshutdown\b\s+(?:-h|-P|-r|\bnow\b|\bhalt\b)\b",
    r"\b(?:reboot|poweroff)\b",
    r"\binit\s+[06]\b",
    r"\bservice\s+\S+\s+(?:stop|restart)\b", 
    r"\bsystemctl\s+(?:stop|restart|mask)\s+\S+", 

    # Cài đặt hoặc gỡ phần mềm
    r"\bapt(?:[- ]get)?\s+(?:install|remove|purge|upgrade)\b",
    r"\bsnap\s+install\b",
    r"\bdpkg\s+-i\b",

    # Mã động & tải về (pipe vào interpreter)
    r"\b(?:curl|wget)\b[^|]*\|\s*(?:sh|bash|python3?|perl|ruby)\b",
    r"\becho\b.+\|\s*base64\s+-d(?:\s+\S+)*\s*\|\s*(?:sh|bash|python3?)\b",

    # Thao tác mạng & thiết bị
    r"\biptables\b[^\n]*\s--flush\b",
    r"\bmount\b\s+.*\s+/(?:etc|var|usr)\b",
    r"\bchmod\s+[0-7]{3,4}\s+/(?:etc|bin|sbin|usr)\b",

    # (Giữ/ghép các mẫu cũ nếu bạn đang dùng)
    # r"\bcurl\b\s+.*\|\s*sh\b",
    # r"\bwget\b\s+.*\|\s*sh\b",
]

# Mẫu secret để mask trong log (regex → replacement)
SECRET_REPLACERS = [
    (r"(?i)\b(password|passwd)\s*[:=]\s*([^\s'\"\\]+)", r"\1=******"),
    (r"(?i)\b(token|apikey|api_key|secret)\s*[:=]\s*([A-Za-z0-9._-]{6,})", r"\1=******"),
    (r"(?i)bearer\s+([A-Za-z0-9._-]+)", "Bearer ******"),
    (r"(?i)sshpass\s+-p\s+(\S+)", "sshpass -p ******"),
    (r"(?i)--password\s+(\S+)", "--password ******"),
]

