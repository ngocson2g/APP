# security_app/utils/normalize.py
from __future__ import annotations

def _strip_comments_outside_quotes(s: str) -> str:
    """
    Loại bỏ phần comment bắt đầu bằng '#' cho tới hết dòng,
    nhưng chỉ khi '#' nằm ngoài các vùng trích dẫn ('…"…' hoặc `…`)
    và không bị escape bằng backslash (\\#).
    Giữ lại newline để không dính hai dòng vào nhau.
    """
    if not s:
        return ""
    out = []
    in_s = in_d = in_bt = False  # '..."...`...`
    i = 0
    while i < len(s):
        ch = s[i]

        # chuyển trạng thái quote
        if ch == "'" and not in_d and not in_bt:
            in_s = not in_s
            out.append(ch); i += 1; continue
        if ch == '"' and not in_s and not in_bt:
            in_d = not in_d
            out.append(ch); i += 1; continue
        if ch == '`' and not in_s and not in_d:
            in_bt = not in_bt
            out.append(ch); i += 1; continue

        # '#' ngoài mọi quote & không phải \#
        if ch == '#' and not (in_s or in_d or in_bt):
            prev = s[i-1] if i > 0 else ''
            if prev != '\\':
                # bỏ tới hết dòng (giữ lại newline nếu có)
                j = s.find('\n', i)
                if j == -1:
                    break
                # tiêu thụ tới newline, thêm đúng 1 newline
                i = j
                out.append('\n')
                continue

        out.append(ch)
        i += 1

    return "".join(out)


def _collapse_ws_outside_quotes(s: str) -> str:
    """
    Gộp mọi chuỗi whitespace (space/tab/newline) ngoài quote thành đúng 1 space.
    Không đụng tới whitespace bên trong quote.
    """
    if not s:
        return ""
    out = []
    in_s = in_d = in_bt = False
    ws_run = False

    for ch in s:
        if ch == "'" and not in_d and not in_bt:
            in_s = not in_s
            out.append(ch); ws_run = False; continue
        if ch == '"' and not in_s and not in_bt:
            in_d = not in_d
            out.append(ch); ws_run = False; continue
        if ch == '`' and not in_s and not in_d:
            in_bt = not in_bt
            out.append(ch); ws_run = False; continue

        if (ch in " \t\r\n") and not (in_s or in_d or in_bt):
            if not ws_run and out:
                out.append(' ')
            ws_run = True
        else:
            out.append(ch)
            ws_run = False
    # trim đầu/cuối
    s2 = "".join(out).strip()
    return s2


def _strip_trailing_connectors(s: str) -> str:
    """
    Bỏ ;, &&, || ở cuối lệnh (sau khi đã gộp whitespace & cắt comment).
    """
    if not s:
        return ""
    # bỏ dấu cách cuối cùng để kiểm tra
    s = s.rstrip()
    for tok in ("&&", "||", ";"):
        if s.endswith(tok):
            s = s[: -len(tok)].rstrip()
    return s


def normalize_command(cmd: str) -> str:
    """
    Chuẩn hoá 'cmd' an toàn về ngữ nghĩa:
      - Cắt comment # (ngoài quote, không phải \\#)
      - Gộp whitespace (ngoài quote) → 1 space, trim
      - Bỏ ; / && / || thừa ở cuối
    Không động chạm nội dung bên trong '...' / "..." / `...`.
    r"""
    if not cmd:
        return ""
    s = _strip_comments_outside_quotes(cmd)
    s = _collapse_ws_outside_quotes(s)
    s = _strip_trailing_connectors(s)
    return s
