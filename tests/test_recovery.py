"""Recovery storage never overwrites another live window or the last good copy."""

import subprocess
import sys

import pytest

from lumacaption.batch import CaptionResult
from lumacaption.recovery import RecoveryStore, default_recovery_directory
from lumacaption.sessions import Session, SessionError


def test_default_location_uses_local_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_recovery_directory() == tmp_path / "LumaCaption" / "recovery"


def test_relative_environment_path_never_uses_working_directory(monkeypatch):
    from pathlib import Path

    monkeypatch.setenv("LOCALAPPDATA", "relative")
    assert default_recovery_directory() == (
        Path.home() / "AppData" / "Local" / "LumaCaption" / "recovery"
    )


def test_roundtrip_and_explicit_discard(tmp_path):
    store = RecoveryStore(tmp_path / "local")
    session = Session(results=[CaptionResult(str(tmp_path / "missing.png"))], offline=True)
    try:
        assert store.load() is None
        store.save(session)
        assert store.load() == session
        store.discard()
        assert store.load() is None
        store.discard()
    finally:
        store.close()


def test_only_one_live_owner_and_reopening_releases_lock(tmp_path):
    first = RecoveryStore(tmp_path)
    try:
        first.save(Session(offline=True))
        with pytest.raises(OSError, match="in use"):
            RecoveryStore(tmp_path)
        assert first.load().offline
    finally:
        first.close()
    second = RecoveryStore(tmp_path)
    try:
        assert second.load().offline
    finally:
        second.close()
    with pytest.raises(OSError, match="closed"):
        first.save(Session())


def test_corrupt_copy_preserved_when_read_fails(tmp_path):
    store = RecoveryStore(tmp_path)
    try:
        store.path.write_bytes(b"broken JSON")
        with pytest.raises(SessionError):
            store.load()
        assert store.path.read_bytes() == b"broken JSON"
    finally:
        store.close()


def test_failed_atomic_write_preserves_previous_copy(tmp_path, monkeypatch):
    store = RecoveryStore(tmp_path)
    try:
        store.save(Session(offline=True))
        original = store.path.read_bytes()

        def fail(*args):
            raise OSError("disk full")

        monkeypatch.setattr("lumacaption.sessions.os.replace", fail)
        with pytest.raises(OSError, match="disk full"):
            store.save(Session(offline=False))
        assert store.path.read_bytes() == original
        assert not list(tmp_path.glob(".lumacaption-session-*"))
    finally:
        store.close()


def test_process_exit_releases_lock_and_leaves_recoverable_data(tmp_path):
    script = """
import os, sys
from pathlib import Path
from lumacaption.recovery import RecoveryStore
from lumacaption.sessions import Session
store = RecoveryStore(Path(sys.argv[1]))
store.save(Session(offline=True))
os._exit(7)
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], timeout=30)
    assert result.returncode == 7
    store = RecoveryStore(tmp_path)
    try:
        assert store.load().offline
    finally:
        store.close()


def test_live_other_process_cannot_acquire_lock(tmp_path):
    store = RecoveryStore(tmp_path)
    try:
        script = """
import sys
from pathlib import Path
from lumacaption.recovery import RecoveryStore
try:
    store = RecoveryStore(Path(sys.argv[1]))
except OSError:
    sys.exit(3)
store.close()
"""
        result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], timeout=30)
        assert result.returncode == 3
    finally:
        store.close()
