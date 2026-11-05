import copy
import json
from dataclasses import asdict

import pytest

from lumacaption import sessions
from lumacaption.batch import CaptionResult
from lumacaption.engine import CaptionOptions
from lumacaption.sessions import Session, SessionError, load_session, save_session


@pytest.fixture
def workspace(tmp_path):
    return Session(
        results=[
            CaptionResult(
                str(tmp_path / "missing ü photo.png"),
                caption="Edited café ✨",
                generated_caption="Original caption",
                status="done",
                edited=True,
                elapsed_seconds=1.25,
            ),
            CaptionResult(str(tmp_path / "pending.png")),
            CaptionResult(str(tmp_path / "bad.png"), status="error", error="Damaged image"),
        ],
        options=CaptionOptions(length="Long", beams=4),
        offline=True,
        recursive=True,
    )


@pytest.fixture
def saved(workspace, tmp_path):
    path = tmp_path / "workspace.lumacaption.json"
    save_session(workspace, path)
    return path


def test_round_trip_preserves_missing_images_and_edits(workspace, saved):
    restored = load_session(saved)
    assert asdict(restored) == asdict(workspace)
    assert restored is not workspace
    restored.results[0].caption = "Changed later"
    assert workspace.results[0].caption == "Edited café ✨"


def test_empty_workspace_round_trip(tmp_path):
    path = tmp_path / "empty.json"
    save_session(Session(), path)
    assert load_session(path) == Session()


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("root", "format", "export"),
        ("root", "schema_version", 2),
        ("root", "schema_version", True),
        ("root", "app_version", None),
        ("root", "settings", []),
        ("root", "results", {}),
        ("settings", "length", "unknown"),
        ("settings", "length", []),
        ("settings", "beams", True),
        ("settings", "beams", 0),
        ("settings", "offline", 1),
        ("settings", "recursive", "false"),
        ("row", "caption", {}),
        ("row", "caption", "x" * (sessions.MAX_TEXT_LENGTH + 1)),
        ("row", "caption", "\ud800"),
        ("row", "path", "relative/image.png"),
        ("row", "path", "C:\\bad\x00.png"),
        ("row", "status", "running"),
        ("row", "edited", "yes"),
        ("row", "elapsed_seconds", -1),
        ("row", "elapsed_seconds", True),
        ("row", "elapsed_seconds", float("nan")),
        ("row", "elapsed_seconds", float("inf")),
        ("row", "created_at", "yesterday"),
        ("row", "created_at", "2026-11-04T12:00:00"),
    ],
)
def test_reject_invalid_fields(saved, section, key, value):
    document = json.loads(saved.read_text(encoding="utf-8"))
    target = (
        document
        if section == "root"
        else (document["settings"] if section == "settings" else document["results"][0])
    )
    target[key] = value
    saved.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SessionError):
        load_session(saved)


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "[]",
        "null",
        '{"format": 1, "format": 2}',
        '{"settings": {"beams": 1, "beams": 2}}',
    ],
)
def test_malformed_or_duplicate_json_rejected(saved, text):
    saved.write_text(text, encoding="utf-8")
    with pytest.raises(SessionError):
        load_session(saved)


@pytest.mark.parametrize("change", ["missing", "unknown", "row_not_object", "duplicate_path"])
def test_reject_incomplete_or_ambiguous_rows(saved, change):
    document = json.loads(saved.read_text(encoding="utf-8"))
    row = document["results"][0]
    if change == "missing":
        del row["caption"]
    elif change == "unknown":
        row["unexpected"] = "ignored?"
    elif change == "row_not_object":
        document["results"][0] = []
    else:
        duplicate = copy.deepcopy(row)
        duplicate["path"] = row["path"].upper().replace("\\", "/")
        document["results"].append(duplicate)
    saved.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SessionError):
        load_session(saved)


def test_file_size_bound_on_read_and_write(saved, workspace, monkeypatch, tmp_path):
    monkeypatch.setattr(sessions, "MAX_SESSION_BYTES", 10)
    with pytest.raises(SessionError, match="limit"):
        load_session(saved)
    target = tmp_path / "large.json"
    with pytest.raises(SessionError, match="limit"):
        save_session(workspace, target)
    assert not target.exists()


def test_image_count_bound(saved, workspace, monkeypatch, tmp_path):
    monkeypatch.setattr(sessions, "MAX_BATCH", 2)
    with pytest.raises(SessionError, match="at most"):
        load_session(saved)
    with pytest.raises(SessionError, match="at most"):
        save_session(workspace, tmp_path / "many.json")


def test_existing_session_requires_opt_in(workspace, saved):
    original = saved.read_bytes()
    workspace.results[0].caption = "New caption"
    with pytest.raises(FileExistsError):
        save_session(workspace, saved)
    assert saved.read_bytes() == original
    save_session(workspace, saved, overwrite=True)
    assert load_session(saved).results[0].caption == "New caption"


def test_failed_replace_preserves_previous_session(workspace, saved, monkeypatch):
    original = saved.read_bytes()
    workspace.results[0].caption = "New caption"

    def fail(*args):
        raise OSError("disk error")

    monkeypatch.setattr(sessions.os, "replace", fail)
    with pytest.raises(OSError, match="disk error"):
        save_session(workspace, saved, overwrite=True)
    assert saved.read_bytes() == original
    assert not list(saved.parent.glob(".lumacaption-session-*"))


def test_failed_flush_does_not_publish(workspace, tmp_path, monkeypatch):
    target = tmp_path / "new.json"

    def fail(*args):
        raise OSError("flush error")

    monkeypatch.setattr(sessions.os, "fsync", fail)
    with pytest.raises(OSError):
        save_session(workspace, target)
    assert not target.exists()
    assert not list(tmp_path.glob(".lumacaption-session-*"))


def test_racing_writer_is_not_overwritten(workspace, tmp_path, monkeypatch):
    target = tmp_path / "race.json"
    original_link = sessions.os.link

    def race(source, destination):
        destination.write_text("other writer")
        original_link(source, destination)

    monkeypatch.setattr(sessions.os, "link", race)
    with pytest.raises(FileExistsError):
        save_session(workspace, target)
    assert target.read_text() == "other writer"
    assert not list(tmp_path.glob(".lumacaption-session-*"))


def test_save_revalidates_mutable_state(workspace, saved):
    original = saved.read_bytes()
    workspace.results[0].status = "invented"
    with pytest.raises(SessionError):
        save_session(workspace, saved, overwrite=True)
    assert saved.read_bytes() == original


def test_input_file_cannot_be_replaced(tmp_path):
    source = tmp_path / "source.json"
    source.write_text("keep image bytes")
    workspace = Session(results=[CaptionResult(str(source))])
    with pytest.raises(SessionError, match="input image"):
        save_session(workspace, source, overwrite=True)
    alias = tmp_path / "alias.json"
    sessions.os.link(source, alias)
    with pytest.raises(SessionError, match="input image"):
        save_session(workspace, alias, overwrite=True)
    assert source.read_text() == "keep image bytes"


def test_caption_export_is_not_a_session(saved):
    from lumacaption.exporting import export_results

    export_results([CaptionResult("C:/images/photo.jpg")], saved, overwrite=True)
    with pytest.raises(SessionError):
        load_session(saved)


def test_invalid_utf8_and_bom(saved):
    original = saved.read_bytes()
    saved.write_bytes(b"\xff\xff")
    with pytest.raises(SessionError):
        load_session(saved)
    saved.write_bytes(b"\xef\xbb\xbf" + original)
    assert load_session(saved).results


def test_deep_json_rejected(saved):
    saved.write_text("[" * 2000 + "]" * 2000)
    with pytest.raises(SessionError):
        load_session(saved)


def test_save_rejects_non_json_destination(workspace, tmp_path):
    with pytest.raises(SessionError, match=".json"):
        save_session(workspace, tmp_path / "image.png")
