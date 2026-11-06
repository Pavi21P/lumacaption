"""Local recovery storage with one writer per OS user; no model or UI work."""

from __future__ import annotations

import os
from pathlib import Path

from .sessions import Session, load_session, save_session


def default_recovery_directory() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base and Path(base).is_absolute():
        return Path(base) / "LumaCaption" / "recovery"
    return Path.home() / "AppData" / "Local" / "LumaCaption" / "recovery"


class RecoveryStore:
    """Hold an OS lock until close; process exit releases it after a crash."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / "autosave.lumacaption.json"
        directory.mkdir(parents=True, exist_ok=True)
        self._lock = (directory / "recovery.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self._lock.seek(0)
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._lock.close()
            raise OSError("Recovery is in use by another window or cannot be locked.") from exc

    def _require_open(self) -> None:
        if self._lock.closed:
            raise OSError("Recovery storage is closed.")

    def load(self) -> Session | None:
        self._require_open()
        try:
            return load_session(self.path)
        except FileNotFoundError:
            return None

    def save(self, session: Session) -> None:
        self._require_open()
        save_session(session, self.path, overwrite=True)

    def discard(self) -> None:
        self._require_open()
        self.path.unlink(missing_ok=True)

    def close(self) -> None:
        # Closing the descriptor releases the OS lock. Keep the lock file itself:
        # deleting it could let separate processes lock different file objects.
        self._lock.close()
