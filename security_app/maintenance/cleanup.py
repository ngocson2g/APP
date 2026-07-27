# security_app/maintenance/cleanup.py
from __future__ import annotations

import contextlib
import os
import shutil
import tarfile
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ----------------------------
# Helpers
# ----------------------------

def _is_run_dir(p: Path) -> bool:
    try:
        return p.is_dir()
    except FileNotFoundError:
        return False

def _sorted_by_mtime_desc(paths: Iterable[Path]) -> list[Path]:
    def _mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except FileNotFoundError:
            return 0.0
    return sorted(paths, key=_mtime, reverse=True)

def _human(nbytes: int) -> str:
    units = ["B","KB","MB","GB","TB"]
    i = 0
    x = float(nbytes)
    while x >= 1024 and i < len(units)-1:
        x /= 1024.0
        i += 1
    return f"{x:.1f} {units[i]}"

def _folder_size(p: Path) -> int:
    total = 0
    for root, _, files in os.walk(p, followlinks=False):
        for f in files:
            fp = Path(root) / f
            with contextlib.suppress(FileNotFoundError):
                total += fp.stat().st_size
    return total

# ----------------------------
# Core cleanup routines
# ----------------------------

def prune_runs(
    logs_dir: Path,
    keep_latest: int = 50,
    older_than_days: int | None = None,
    compress_older_days: int | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Dọn dẹp thư mục run trong logs_dir:
    - Giữ lại N run mới nhất (keep_latest).
    - Nếu older_than_days: xoá mọi run cũ hơn số ngày này.
    - Nếu compress_older_days: nén .tar.gz các run cũ hơn số ngày này (nếu chưa nén).
    """
    logs_dir = Path(logs_dir).resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)
    entries = [p for p in logs_dir.iterdir() if _is_run_dir(p)]
    ordered = _sorted_by_mtime_desc(entries)

    now = datetime.now()
    delete_cut = now - timedelta(days=older_than_days) if older_than_days is not None else None
    compress_cut = now - timedelta(days=compress_older_days) if compress_older_days is not None else None

    to_delete: list[Path] = []
    to_compress: list[Path] = []

    for i, p in enumerate(ordered):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
        except FileNotFoundError:
            continue

        # compress candidates
        if compress_cut and mtime < compress_cut and p.is_dir():
            arc = p.with_suffix(p.suffix + ".tar.gz") if p.suffix else Path(str(p) + ".tar.gz")
            if not arc.exists():
                to_compress.append(p)

        # delete by quota or age
        if i >= keep_latest or (delete_cut and mtime < delete_cut):
            to_delete.append(p)

    report = {"deleted": [], "compressed": [], "kept": [str(p) for p in ordered[:keep_latest]]}

    # compress first (if not in delete list)
    for p in to_compress:
        if p in to_delete:
            continue
        arc = p.with_suffix(p.suffix + ".tar.gz") if p.suffix else Path(str(p) + ".tar.gz")
        if dry_run:
            report["compressed"].append(f"DRY-RUN {p.name} -> {arc.name}")
        else:
            with tarfile.open(arc, "w:gz") as tf:
                tf.add(p, arcname=p.name, recursive=True)
            report["compressed"].append(f"{p.name} -> {arc.name}")

    # delete
    for p in to_delete:
        try:
            size = _human(_folder_size(p)) if p.is_dir() else _human(p.stat().st_size)
        except FileNotFoundError:
            size = "unknown"
        if dry_run:
            report["deleted"].append(f"DRY-RUN {p.name} ({size})")
        else:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                with contextlib.suppress(FileNotFoundError):
                    p.unlink()
            report["deleted"].append(f"{p.name} ({size})")

    return report

def prune_tmp(tmp_dir: Path = Path("/tmp"), prefix: str = "security_app_", older_than_hours: int = 12, dry_run: bool = True) -> dict[str, Any]:
    """
    Xoá các file/thư mục tạm trong tmp_dir khớp prefix và cũ hơn X giờ.
    """
    now = datetime.now()
    cut = now - timedelta(hours=older_than_hours)
    removed = []

    for p in tmp_dir.glob(prefix + "*"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
        except FileNotFoundError:
            continue
        if mtime < cut:
            if dry_run:
                removed.append(f"DRY-RUN {p}")
            else:
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    with contextlib.suppress(FileNotFoundError):
                        p.unlink()
                removed.append(str(p))

    return {"tmp_removed": removed}

def prune_reports(report_root: Path, keep_days: int = 30, dry_run: bool = True) -> dict[str, Any]:
    """
    Dọn dẹp reportAPP:
    - Xoá thư mục báo cáo cũ hơn keep_days.
    - Sửa lại symlink 'latest' nếu trỏ tới thư mục không còn tồn tại.
    """
    report_root = Path(report_root).resolve()
    if not report_root.exists():
        return {"reports_deleted": [], "latest": None}

    now = datetime.now()
    cut = now - timedelta(days=keep_days)
    deleted: list[str] = []

    runs = _sorted_by_mtime_desc([p for p in report_root.iterdir() if p.is_dir()])

    for p in runs:
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
        except FileNotFoundError:
            continue
        if mtime < cut:
            if dry_run:
                deleted.append(f"DRY-RUN {p.name}")
            else:
                shutil.rmtree(p, ignore_errors=True)
                deleted.append(p.name)

    # fix latest symlink
    latest_link = report_root / "latest"
    latest_target = None

    def _pick_latest() -> Path | None:
        remaining = _sorted_by_mtime_desc([q for q in report_root.iterdir() if q.is_dir()])
        return remaining[0] if remaining else None

    if latest_link.is_symlink():
        try:
            tgt = latest_link.resolve()
            if not tgt.exists():
                pick = _pick_latest()
                if pick:
                    if not dry_run:
                        with contextlib.suppress(FileNotFoundError):
                            latest_link.unlink()
                        latest_link.symlink_to(pick.name)
                    latest_target = pick.name
        except FileNotFoundError:
            pass
    else:
        pick = _pick_latest()
        if pick:
            if not dry_run:
                with contextlib.suppress(FileNotFoundError):
                    latest_link.unlink()
                latest_link.symlink_to(pick.name)
            latest_target = pick.name

    return {"reports_deleted": deleted, "latest": latest_target}

def run_cleanup(
    logs_dir: Path,
    report_dir: Path | None = None,
    keep_runs: int = 50,
    runs_older_than_days: int | None = None,
    compress_runs_older_than_days: int | None = None,
    keep_reports_days: int = 30,
    tmp_prefix: str = "security_app_",
    tmp_older_than_hours: int = 12,
    dry_run: bool = True,
) -> dict[str, Any]:
    report: dict[str, Any] = {}
    report["runs"] = prune_runs(
        logs_dir=Path(logs_dir),
        keep_latest=keep_runs,
        older_than_days=runs_older_than_days,
        compress_older_days=compress_runs_older_than_days,
        dry_run=dry_run,
    )
    if report_dir:
        report["reports"] = prune_reports(
            report_root=Path(report_dir),
            keep_days=keep_reports_days,
            dry_run=dry_run,
        )
    report["tmp"] = prune_tmp(prefix=tmp_prefix, older_than_hours=tmp_older_than_hours, dry_run=dry_run)
    return report
