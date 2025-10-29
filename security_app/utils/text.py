# security_app/utils/text.py
import re
import shutil


def ellipsis_middle(s: str, max_chars: int = 180) -> str:
    """Rút gọn chuỗi ở giữa để in log ngắn gọn."""
    # FIX: Use <= to handle exact length correctly
    if len(s) <= max_chars or max_chars < 6: # Need at least ~6 chars for "a...b"
        return s
    keep = max(0, max_chars // 2 - 3)
    if keep == 0:
        return s[:max_chars-3] + "..."
    return s[:keep] + "..." + s[-keep:]

def _term_width():
    return shutil.get_terminal_size((120, 20)).columns

def _safe_name(s: str, maxlen: int = 60) -> str:
    """
    Biến tiêu đề thành tên file an toàn, cắt độ dài vừa phải.
    """
    s = re.sub(r"[^\w\-.]+", "_", s.strip())
    if len(s) <= maxlen:
        return s
    return s[: maxlen - 3] + "..."

def _bar(done: int, total: int, width: int | str = 20) -> str: # Allow str for width input type hint
    """
    Thanh tiến độ ASCII đơn giản (dùng cho CLI).
    Ví dụ: [██████████          ]
    """
    try:
        total = int(total)
        done = int(done)
        # FIX: Move width processing inside try block
        # Use default 20 if width is None or empty string BEFORE int conversion
        width_val = width if width else 20
        width = max(4, int(width_val))
    except (ValueError, TypeError): # Catch more potential errors
        return ""
    if total <= 0:
        return ""
    # width = max(4, int(width or 20)) # <-- MOVE THIS LINE UP
    frac = max(0.0, min(1.0, (done / total)))
    filled = int(frac * width)
    return ("█" * filled) + (" " * (width - filled))

def _table(rows, headers, max_width=None):
    if max_width is None:
        max_width = _term_width()
    cols = len(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            widths[i] = max(widths[i], len(str(r[i])))

    total_width = sum(widths) + 3 * (cols - 1)
    if total_width > max_width:
        overflow = total_width - max_width
        i = cols - 1
        widths[i] = max(8, widths[i] - overflow)

    def cut(s, w):
        s = str(s)
        return (s[: w - 1] + "…") if len(s) > w else s

    print(" | ".join(cut(headers[i], widths[i]).ljust(widths[i]) for i in range(cols)))
    print("-+-".join("-" * widths[i] for i in range(cols)))
    for r in rows:
        print(" | ".join(cut(r[i], widths[i]).ljust(widths[i]) for i in range(cols)))
