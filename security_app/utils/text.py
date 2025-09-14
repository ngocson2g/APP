# security_app/utils/text.py
import re
import shutil

def ellipsis_middle(s: str, max_chars: int = 180) -> str:
    """Rút gọn chuỗi ở giữa để in log ngắn gọn."""
    if len(s) <= max_chars:
        return s
    keep = max_chars // 2 - 3
    return s[:keep] + "..." + s[-keep:]

def _term_width():
    return shutil.get_terminal_size((120, 20)).columns

def _safe_name(s: str, maxlen: int = 60) -> str:
    if not s:
        return "rule"
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())
    return (s[:maxlen]).strip("_") or "rule"

def _bar(value, total, width=20, ch="█"):
    if total <= 0: return ""
    n = max(0, min(width, round(value * width / total)))
    return ch * n + " " * (width - n)

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

    def cut(s, w): s = str(s); return (s[:w-1] + "…") if len(s) > w else s

    print(" | ".join(cut(headers[i], widths[i]).ljust(widths[i]) for i in range(cols)))
    print("-+-".join("-"*widths[i] for i in range(cols)))
    for r in rows:
        print(" | ".join(cut(r[i], widths[i]).ljust(widths[i]) for i in range(cols)))
