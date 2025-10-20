# security_app/runtime/ownership.py
from __future__ import annotations
import os, os.path

def original_user_ids() -> tuple[int, int]:
    """Lấy UID/GID của user thật nếu chạy dưới sudo; fallback về UID/GID hiện tại."""
    uid = int(os.getenv("SUDO_UID", str(os.getuid())))
    gid = int(os.getenv("SUDO_GID", str(os.getgid())))
    return uid, gid

def chown_path(path: str, recursive: bool = False) -> None:
    """Đổi sở hữu path về user thật; an toàn nếu thiếu quyền hoặc file biến mất."""
    try:
        uid, gid = original_user_ids()
        if recursive and os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                os.chown(root, uid, gid)
                for d in dirs:  os.chown(os.path.join(root, d), uid, gid)
                for f in files: os.chown(os.path.join(root, f), uid, gid)
        else:
            os.chown(path, uid, gid)
    except Exception:
        # im lặng bỏ qua (không để việc đổi quyền làm gãy luồng chính)
        pass
