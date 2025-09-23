# apps/dashboard/backend/reader/run_reader.py
import glob
import os
from typing import Any, Dict, List

from .config import LOGS_BASE


def _list_run_dirs(base: str = LOGS_BASE) -> List[Dict[str, Any]]:
    if not os.path.isdir(base):
        return []
    items = []
    for name in os.listdir(base):
        p = os.path.join(base, name)
        if not os.path.isdir(p):
            continue
        try:
            mtime = os.path.getmtime(p)
        except OSError:
            mtime = 0.0
        files = len(glob.glob(os.path.join(p, "rule-*.log")))
        items.append({"id": name, "title": f"Run {name}", "mtime": mtime, "files": files})
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items

def list_runs() -> List[Dict[str, Any]]:
    return _list_run_dirs(LOGS_BASE)