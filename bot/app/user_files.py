"""Per-user, per-job filesystem isolation for downloads and uploads.

Every transfer owns a private directory under DOWNLOAD_DIR/u<user_id>/<job_id>/.
Two users can never share a path, file handle, or leftover temp file.
"""

from __future__ import annotations

import logging
import re
import secrets
import shutil
import time
from pathlib import Path

from app.settings import settings

log = logging.getLogger("teradrop.files")
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(filename: str) -> str:
    cleaned = _SAFE.sub("_", filename or "").strip("._")[:80]
    return cleaned or "download"


class UserJobDir:
    def __init__(self, user_id: int, job_id: str | None = None) -> None:
        self.user_id = int(user_id)
        self.job_id = job_id or secrets.token_hex(8)
        self.root = settings.download_dir / f"u{self.user_id}" / self.job_id
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, filename: str) -> Path:
        return self.root / f"{secrets.token_hex(4)}_{_safe_name(filename)}"

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        parent = self.root.parent
        try:
            if parent.is_dir() and next(parent.iterdir(), None) is None:
                parent.rmdir()
        except OSError:
            pass

    @staticmethod
    def reap_stale(max_age: int = 7200) -> int:
        root = settings.download_dir
        if not root.is_dir():
            return 0
        cutoff = time.time() - max_age
        removed = 0
        for user_dir in root.glob("u*"):
            if not user_dir.is_dir():
                continue
            for job_dir in list(user_dir.iterdir()):
                try:
                    if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
                        shutil.rmtree(job_dir, ignore_errors=True)
                        removed += 1
                except OSError:
                    continue
            try:
                if next(user_dir.iterdir(), None) is None:
                    user_dir.rmdir()
            except OSError:
                pass
        return removed
