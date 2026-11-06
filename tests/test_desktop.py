"""Integration tests exercise our Tk widgets with a synthetic model, without downloads."""

import time
import tkinter as tk
from dataclasses import replace

import pytest
from PIL import Image

from lumacaption.batch import CaptionResult
from lumacaption.desktop import CaptionApp
from lumacaption.engine import CaptionOptions
from lumacaption.sessions import Session, load_session, save_session


@pytest.fixture(scope="session")
def tk_runtime():
    # One Tcl interpreter with an isolated window per test, matching the app's
    # single-interpreter runtime and avoiding repeated Windows Tk reloads.
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def desktop(tmp_path, monkeypatch, tk_runtime):
    root = tk.Toplevel(tk_runtime)
    root.withdraw()
    app = CaptionApp(root, recovery_dir=tmp_path / "recovery")
    monkeypatch.setattr("lumacaption.desktop.messagebox.showerror", lambda *a, **k: None)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **k: False)
    path = tmp_path / "my picture.png"
    Image.new("RGB", (40, 20), "blue").save(path)
    yield root, app, path
    app.closed = True
    app._release_recovery()
    # Cancel scheduled callbacks before destroying this test's window.
    for callback in root.tk.call("after", "info"):
        root.after_cancel(callback)
    root.destroy()


def pump_until(root, condition, timeout=5):
    deadline = time.monotonic() + timeout
    while not condition() and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert condition()


def test_selection_and_caption_edits_survive_export(desktop, tmp_path, monkeypatch):
    import json

    root, app, path = desktop
    app.add_paths([path])
    root.update()
    key = str(path.resolve())
    app.rows[key] = CaptionResult(
        key, caption="A blue rectangle", status="done", generated_caption="A blue rectangle"
    )
    app.current = key
    app._show_caption()
    app.editor.delete("1.0", "end")
    app.editor.insert("1.0", "My edited caption")
    destination = tmp_path / "result.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kwargs: str(destination)
    )
    app._export()
    doc = json.loads(destination.read_text())
    assert doc["results"][0]["caption"] == "My edited caption"
    assert doc["results"][0]["edited"] is True
    assert app.dirty is True  # Export does not save the workspace/settings.
    app._restore()
    assert app.editor.get("1.0", "end-1c") == "A blue rectangle"


def test_background_batch_updates_ui(desktop):
    root, app, path = desktop

    class Stub:
        offline = False

        def prepare(self, status):
            status("Testing")

        def caption(self, image, options):
            return "A blue rectangle"

    app.engine = Stub()
    app.add_paths([path])
    app._start()
    assert app.busy
    pump_until(root, lambda: not app.busy)
    assert app.rows[str(path.resolve())].status == "done"
    assert app.batch_finished == 1
    assert "Finished" in app.status.get()
    assert app.dirty


def test_error_status_survives_separate_poll_cycles(desktop):
    _, app, _ = desktop
    app.busy = True
    app.events.put(("error", "Model unavailable"))
    app._poll()
    app.events.put(("finished", None))
    app._poll()
    assert app.status.get() == "Model unavailable"
    assert not app.busy


def test_clear_resets_results_and_preview(desktop):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    app.dirty = True
    app._clear()
    assert not app.rows
    assert app.current is None
    assert app.preview_source is None
    assert not app.tree.get_children()
    assert not app.dirty


def test_failed_row_can_be_retried(desktop):
    root, app, path = desktop

    class Stub:
        offline = False

        def prepare(self, status):
            pass

        def caption(self, image, options):
            return "Recovered"

    app.engine = Stub()
    app.add_paths([path])
    row = app.rows[str(path.resolve())]
    row.status = "error"
    row.error = "Transient failure"
    app._retry()
    pump_until(root, lambda: not app.busy)
    assert app.rows[str(path.resolve())].caption == "Recovered"


def import_file(app, monkeypatch, destination):
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.askopenfilename", lambda **kw: str(destination)
    )
    app._open_session()


def test_session_roundtrip_includes_live_editor_and_settings(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    row = app.rows[str(path.resolve())]
    row.caption = row.generated_caption = "Original"
    row.status = "done"
    app._show_caption()
    app.editor.delete("1.0", "end")
    app.editor.insert("1.0", "Edited but not yet blurred")
    app.length.set("Long")
    app.beams = 5
    app.offline.set(True)
    app.recursive.set(True)
    destination = tmp_path / "saved.lumacaption.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(destination)
    )
    assert app._save_session()
    assert not app.dirty
    saved = load_session(destination)
    assert saved.results[0].caption == "Edited but not yet blurred"
    assert saved.results[0].generated_caption == "Original"
    assert saved.results[0].edited
    app._clear()
    app.length.set("Short")
    import_file(app, monkeypatch, destination)
    root.update()
    assert app.rows[row.path] == saved.results[0]
    assert app.editor.get("1.0", "end-1c") == saved.results[0].caption
    assert app.length.get() == "Long" and app.beams == 5
    assert app.offline.get() and app.recursive.get()
    assert app.session_path == destination
    assert not app.dirty and not app.busy and app.engine is None


@pytest.mark.parametrize("contents", ['{"schema_version": 99}', "not JSON"])
def test_invalid_open_preserves_workspace_and_uncommitted_editor(
    desktop, tmp_path, monkeypatch, contents
):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    row = app.rows[str(path.resolve())]
    row.status = "done"
    row.caption = "Original"
    app._show_caption()
    app.editor.delete("1.0", "end")
    app.editor.insert("1.0", "Unsaved typing")
    preview = app.preview_source
    destination = tmp_path / "broken.json"
    destination.write_text(contents)
    errors = []
    monkeypatch.setattr(
        "lumacaption.desktop.messagebox.showerror", lambda *a, **kw: errors.append(a)
    )
    monkeypatch.setattr(
        "lumacaption.desktop.messagebox.askyesnocancel",
        lambda *a, **kw: pytest.fail("Invalid import must not prompt to discard work"),
    )
    import_file(app, monkeypatch, destination)
    assert app.rows[row.path] is row and row.caption == "Original"
    assert app.current == row.path and app.preview_source is preview
    assert app.editor.get("1.0", "end-1c") == "Unsaved typing"
    assert errors and app.dirty


@pytest.mark.parametrize("action", ["open", "clear", "close"])
def test_cancel_unsaved_prompt_preserves_workspace(desktop, tmp_path, monkeypatch, action):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    destination = tmp_path / "empty.json"
    save_session(Session(), destination)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **kw: None)
    if action == "open":
        import_file(app, monkeypatch, destination)
    else:
        getattr(app, "_" + action)()
    assert str(path.resolve()) in app.rows
    assert app.dirty and not app.closed


@pytest.mark.parametrize("failure", ["cancel", "write"])
def test_cancelled_or_failed_save_blocks_replacement(desktop, tmp_path, monkeypatch, failure):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    incoming = tmp_path / "empty.json"
    save_session(Session(), incoming)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **kw: True)
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename",
        lambda **kw: "" if failure == "cancel" else str(tmp_path / "save.json"),
    )
    if failure == "write":

        def fail(*args, **kwargs):
            raise OSError("Disk full")

        monkeypatch.setattr("lumacaption.desktop.save_session", fail)
    import_file(app, monkeypatch, incoming)
    assert str(path.resolve()) in app.rows and app.dirty
    assert app.session_path is None


def test_save_before_open_keeps_latest_if_same_destination(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    destination = tmp_path / "workspace.json"
    save_session(Session(), destination)
    app.add_paths([path])
    root.update()
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **kw: True)
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(destination)
    )
    import_file(app, monkeypatch, destination)
    assert list(app.rows) == [str(path.resolve())]
    assert not app.dirty


def test_missing_images_preserve_edits_provenance_and_can_export(desktop, tmp_path, monkeypatch):
    root, app, _ = desktop
    missing = str(tmp_path / "moved.png")
    row = CaptionResult(
        missing,
        caption="Reviewed caption",
        generated_caption="AI caption",
        edited=True,
        status="done",
        elapsed_seconds=1.25,
    )
    pending = CaptionResult(str(tmp_path / "pending.png"))
    destination = tmp_path / "missing.json"
    save_session(Session(results=[row, pending]), destination)
    import_file(app, monkeypatch, destination)
    root.update()
    assert app.rows[missing] == row
    assert app.tree.set(missing, "state") == "Missing"
    assert "error" in app.tree.item(missing, "tags")
    assert "missing" in app.detail.cget("text").lower()
    assert app.editor.get("1.0", "end-1c") == row.caption
    assert app.preview_source is None
    assert str(app.generate_button["state"]) == "disabled"
    app._retry()
    assert not app.busy and app.rows[missing] == row
    exported = tmp_path / "export.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(exported)
    )
    app._export()
    import json

    assert json.loads(exported.read_text())["results"][0]["caption"] == row.caption
    assert app._save_session()
    saved = load_session(exported)
    assert saved.results == [row, pending]


def test_empty_import_clears_old_preview_editor_and_queue(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    destination = tmp_path / "empty.json"
    save_session(Session(options=CaptionOptions(length="Short")), destination)
    import_file(app, monkeypatch, destination)
    root.update()
    assert not app.rows and not app.tree.get_children()
    assert app.current is None and app.preview_source is None and app.preview_photo is None
    assert not app.editor.get("1.0", "end-1c")
    assert app.length.get() == "Short" and not app.dirty


@pytest.mark.parametrize(
    "variable,value", [("length", "Long"), ("offline", True), ("recursive", True)]
)
def test_settings_changes_need_saving(desktop, variable, value):
    _, app, _ = desktop
    assert not app.dirty
    getattr(app, variable).set(value)
    assert app.dirty


def test_session_controls_do_not_replace_running_batch(desktop, monkeypatch):
    _, app, _ = desktop
    app.busy = True
    app._update_controls()
    for name in ("askopenfilename", "asksaveasfilename"):
        monkeypatch.setattr(
            "lumacaption.desktop.filedialog." + name,
            lambda **kw: pytest.fail("Must not show dialogs during generation"),
        )
    assert str(app.save_session_button["state"]) == "disabled"
    assert str(app.open_session_button["state"]) == "disabled"
    app._open_session()
    assert app._save_session() is False


def test_restored_pending_options_reach_worker_only_on_generate(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    options = CaptionOptions(length="Short", beams=1)
    destination = tmp_path / "pending.json"
    save_session(
        Session(results=[CaptionResult(str(path.resolve()))], options=options), destination
    )
    seen = []

    class Stub:
        offline = False

        def prepare(self, status):
            pass

        def caption(self, image, options):
            seen.append(options)
            return "Caption"

    app.engine = Stub()
    import_file(app, monkeypatch, destination)
    root.update()
    assert not seen and not app.busy
    app._start()
    pump_until(root, lambda: not app.busy)
    assert seen == [options]
    assert app.dirty


def test_cancel_open_dialog_leaves_workspace(desktop, monkeypatch):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    monkeypatch.setattr("lumacaption.desktop.filedialog.askopenfilename", lambda **kw: "")
    app._open_session()
    assert list(app.rows) == [str(path.resolve())] and app.dirty


def test_autosave_debounces_queue_settings_and_pasted_text(desktop, monkeypatch):
    root, app, path = desktop
    monkeypatch.setattr("lumacaption.desktop.AUTOSAVE_DELAY_MS", 60)
    app.add_paths([path])
    root.update()
    row = app.rows[str(path.resolve())]
    row.status = "done"
    row.caption = row.generated_caption = "Generated"
    app._show_caption()
    writes = []
    save = app.recovery.save

    def recording_save(session):
        writes.append(session)
        save(session)

    monkeypatch.setattr(app.recovery, "save", recording_save)
    app.length.set("Long")
    app.offline.set(True)
    app.recursive.set(True)
    app.editor.delete("1.0", "end")
    app.editor.insert("1.0", "Pasted edit")
    # A real <<Modified>> event captures edits even without key release/focus change.
    root.update()
    assert not app.recovery.path.exists()
    pump_until(root, lambda: app.recovery.path.exists())
    assert len(writes) == 1
    saved = app.recovery.load()
    assert saved.results[0].caption == "Pasted edit"
    assert saved.results[0].generated_caption == "Generated"
    assert saved.results[0].edited
    assert saved.offline and saved.recursive and saved.options.length == "Long"
    assert app.dirty


def test_startup_recovers_completed_and_interrupted_rows_without_inference(
    desktop, tmp_path, monkeypatch
):
    from lumacaption.recovery import RecoveryStore

    root, app, path = desktop
    app._release_recovery()
    directory = tmp_path / "interrupted"
    finished = CaptionResult(
        str(path.resolve()),
        caption="Edited",
        generated_caption="Original",
        edited=True,
        status="done",
    )
    pending = CaptionResult(str(tmp_path / "missing.png"))
    store = RecoveryStore(directory)
    store.save(
        Session(results=[finished, pending], options=CaptionOptions("Long", 5), offline=True)
    )
    store.close()
    monkeypatch.setattr(app, "_start", lambda: pytest.fail("Recovery must not start generation"))
    app._initialize_recovery(directory)
    root.update()
    assert app.rows[finished.path] == finished
    assert app.rows[pending.path].status == "pending"
    assert pending.path in app.image_errors
    assert app.beams == 5 and app.length.get() == "Long" and app.offline.get()
    assert app.dirty and app.session_path is None
    assert not app.busy and app.engine is None
    assert app.editor.get("1.0", "end-1c") == "Edited"


def test_declining_recovery_removes_only_the_recovery_copy(desktop, tmp_path, monkeypatch):
    from lumacaption.recovery import RecoveryStore

    _, app, path = desktop
    app._release_recovery()
    store = RecoveryStore(tmp_path / "declined")
    store.save(Session(results=[CaptionResult(str(path.resolve()))]))
    store.close()
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesno", lambda *a, **kw: False)
    app._initialize_recovery(tmp_path / "declined")
    assert not app.rows and not app.dirty
    assert app.recovery.load() is None
    assert path.exists()


def test_corrupt_startup_copy_is_preserved_and_autosave_disabled(desktop, tmp_path):
    _, app, path = desktop
    app._release_recovery()
    directory = tmp_path / "corrupt"
    directory.mkdir()
    damaged = directory / "autosave.lumacaption.json"
    damaged.write_text("bad json")
    app._initialize_recovery(directory)
    app.add_paths([path])
    app._autosave_now()
    assert damaged.read_text() == "bad json"
    assert app.recovery is None and app.dirty
    assert "unavailable" in app.autosave_status.get().lower()


def test_second_window_preserves_first_windows_recovery(desktop):
    from lumacaption.recovery import RecoveryStore

    _, app, path = desktop
    app._release_recovery()
    directory = path.parent / "other-window"
    first = RecoveryStore(directory)
    first.save(Session(offline=True))
    try:
        app._initialize_recovery(directory)
        app.add_paths([path])
        app._autosave_now()
        assert app.recovery is None and first.load().offline
        assert "another window" in app.autosave_status.get()
    finally:
        first.close()


def test_autosave_failure_keeps_dirty_previous_copy_and_allows_retry(desktop, monkeypatch):
    _, app, path = desktop
    app.add_paths([path])
    app._autosave_now()
    original = app.recovery.path.read_bytes()
    save = app.recovery.save

    def fail(session):
        raise OSError("disk full")

    monkeypatch.setattr(app.recovery, "save", fail)
    app.offline.set(True)
    app._autosave_now()
    assert app.recovery.path.read_bytes() == original and app.dirty
    assert "disk full" in app.autosave_status.get()
    monkeypatch.setattr(app.recovery, "save", save)
    app._mark_dirty()
    app._autosave_now()
    assert app.recovery.load().offline and app.dirty


@pytest.mark.parametrize("action", ["clear", "save", "open"])
def test_explicit_save_or_replace_cleans_recovery_and_cancels_timer(
    desktop, tmp_path, monkeypatch, action
):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    app._autosave_now()
    recovery_path = app.recovery.path
    app.offline.set(True)
    if action == "clear":
        app._clear()
    elif action == "save":
        destination = tmp_path / "manual.json"
        monkeypatch.setattr(
            "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(destination)
        )
        assert app._save_session()
        assert load_session(destination).offline
    else:
        destination = tmp_path / "empty.json"
        save_session(Session(), destination)
        import_file(app, monkeypatch, destination)
    root.update()
    assert not recovery_path.exists() and app.autosave_after is None
    assert not app.dirty


@pytest.mark.parametrize("action", ["clear", "open", "close"])
def test_cancel_replacement_keeps_recovery(desktop, tmp_path, monkeypatch, action):
    _, app, path = desktop
    app.add_paths([path])
    app._autosave_now()
    original = app.recovery.path.read_bytes()
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **kw: None)
    if action == "open":
        destination = tmp_path / "empty.json"
        save_session(Session(), destination)
        import_file(app, monkeypatch, destination)
    else:
        getattr(app, "_" + action)()
    assert app.recovery.path.read_bytes() == original and app.dirty and not app.closed


def test_batch_pending_and_completed_results_are_recoverable(desktop, monkeypatch):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    # Hold thread creation without changing the real UI/event processing.
    monkeypatch.setattr("lumacaption.desktop.threading.Thread.start", lambda self: None)
    app._start()
    assert app.recovery.load().results[0].status == "pending"
    app.events.put(("result", CaptionResult(str(path.resolve()), caption="Done", status="done")))
    app.events.put(("finished", None))
    app._poll()
    app._autosave_now()
    assert app.recovery.load().results[0].caption == "Done"
    assert not app.busy and app.dirty


def test_cleanup_failure_stops_clear_without_losing_workspace(desktop, monkeypatch):
    _, app, path = desktop
    app.add_paths([path])
    app._autosave_now()

    def fail():
        raise PermissionError("locked")

    monkeypatch.setattr(app.recovery, "discard", fail)
    app._clear()
    assert str(path.resolve()) in app.rows
    assert app.recovery.path.exists() and app.dirty


def test_manual_save_cannot_target_the_internal_recovery_file(desktop, monkeypatch):
    _, app, path = desktop
    app.add_paths([path])
    app._autosave_now()
    original = app.recovery.path.read_bytes()
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(app.recovery.path)
    )
    assert not app._save_session()
    assert app.recovery.path.read_bytes() == original and app.dirty


@pytest.mark.parametrize("busy", [False, True])
def test_confirmed_close_discards_recovery_and_releases_lock(desktop, monkeypatch, busy):
    from lumacaption.recovery import RecoveryStore

    root, app, path = desktop
    app.add_paths([path])
    app._autosave_now()
    directory = app.recovery.path.parent
    app.busy = busy
    with monkeypatch.context() as context:
        context.setattr(root, "destroy", lambda: None)
        app._close()
    assert app.closed and app.recovery is None and app.autosave_after is None
    reopened = RecoveryStore(directory)
    try:
        assert reopened.load() is None
    finally:
        reopened.close()


def test_storage_unavailable_still_allows_manual_session_save(desktop, tmp_path, monkeypatch):
    _, app, path = desktop
    app._release_recovery()

    def unavailable(directory):
        raise PermissionError("Access denied")

    monkeypatch.setattr("lumacaption.desktop.RecoveryStore", unavailable)
    app._initialize_recovery(tmp_path / "blocked")
    app.add_paths([path])
    destination = tmp_path / "manual.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(destination)
    )
    assert app._save_session()
    assert load_session(destination).results[0].path == str(path.resolve())
    assert app.recovery is None


def test_bad_import_preserves_recovery_copy(desktop, tmp_path, monkeypatch):
    _, app, path = desktop
    app.add_paths([path])
    app._autosave_now()
    original = app.recovery.path.read_bytes()
    broken = tmp_path / "broken.json"
    broken.write_text("bad")
    import_file(app, monkeypatch, broken)
    assert app.recovery.path.read_bytes() == original and app.dirty


def test_failed_manual_save_keeps_recovery_copy(desktop, tmp_path, monkeypatch):
    _, app, path = desktop
    app.add_paths([path])
    app._autosave_now()
    original = app.recovery.path.read_bytes()
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename",
        lambda **kw: str(tmp_path / "nonexistent" / "manual.json"),
    )
    assert not app._save_session()
    assert app.recovery.path.read_bytes() == original and app.dirty


def missing_workspace(root, app, tmp_path, *, status="done"):
    row = CaptionResult(
        str(tmp_path / "old folder" / "missing photo.png"),
        caption="Reviewed caption",
        generated_caption="Original AI caption",
        edited=True,
        status=status,
        error="Earlier failure" if status == "error" else "",
        elapsed_seconds=2.5,
        model="saved-model",
        model_revision="saved-revision",
        created_at="2026-11-01T12:00:00+00:00",
    )
    app._apply_session(Session(results=[row]))
    root.update()
    assert row.path in app.image_errors
    return row


def choose_replacement(app, monkeypatch, path):
    monkeypatch.setattr("lumacaption.desktop.filedialog.askopenfilename", lambda **kw: str(path))
    app._relink()


@pytest.mark.parametrize("status", ["pending", "done", "error"])
def test_relink_preserves_all_result_fields_and_never_generates(
    desktop, tmp_path, monkeypatch, status
):
    root, app, path = desktop
    row = missing_workspace(root, app, tmp_path, status=status)
    original_path = row.path
    expected = replace(row, path=str(path.resolve()))
    monkeypatch.setattr(app, "_start", lambda: pytest.fail("Relink must not generate"))
    choose_replacement(app, monkeypatch, path)
    root.update()
    assert app.rows == {expected.path: expected}
    assert not app.image_errors
    assert app.current == expected.path and app.tree.selection() == (expected.path,)
    assert not app.tree.exists(original_path)
    assert app.preview_source is not None
    assert app.preview_source.getpixel((0, 0)) == (0, 0, 255)
    assert app.editor.get("1.0", "end-1c") == expected.caption
    assert app.dirty and app.autosave_after is not None
    assert not app.busy and app.engine is None
    assert str(app.relink_button["state"]) == "disabled"
    assert (
        app.tree.set(expected.path, "state")
        == {
            "pending": "Ready",
            "done": "Edited",
            "error": "Error",
        }[status]
    )


def test_relink_keeps_uncommitted_edits_in_recovery_and_manual_session(
    desktop, tmp_path, monkeypatch
):
    root, app, path = desktop
    row = missing_workspace(root, app, tmp_path)
    old_path = row.path
    app.editor.delete("1.0", "end")
    app.editor.insert("1.0", "Latest edit")
    choose_replacement(app, monkeypatch, path)
    root.update()
    app._autosave_now()
    recovered = app.recovery.load()
    assert recovered.results[0].caption == "Latest edit"
    assert recovered.results[0].generated_caption == "Original AI caption"
    assert recovered.results[0].path == str(path.resolve())
    assert recovered.results[0].edited
    destination = tmp_path / "relinked.lumacaption.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(destination)
    )
    assert app._save_session()
    app._clear()
    import_file(app, monkeypatch, destination)
    root.update()
    assert old_path not in app.rows
    assert app.rows[str(path.resolve())] == recovered.results[0]
    assert not app.image_errors and not app.dirty


@pytest.mark.parametrize(
    "kind", ["cancel", "missing", "damaged", "unsupported", "directory", "load"]
)
def test_invalid_or_cancelled_relink_preserves_workspace_and_recovery(
    desktop, tmp_path, monkeypatch, kind
):
    from lumacaption.images import ImageInputError

    root, app, path = desktop
    row = missing_workspace(root, app, tmp_path)
    original = replace(row)
    app._mark_dirty()
    app._autosave_now()
    recovery = app.recovery.path.read_bytes()
    app.dirty = False
    errors = []
    monkeypatch.setattr(
        "lumacaption.desktop.messagebox.showerror", lambda *a, **kw: errors.append(a)
    )
    if kind == "cancel":
        candidate = ""
    elif kind == "load":
        candidate = path

        def fail(path):
            raise ImageInputError("Permission denied")

        monkeypatch.setattr("lumacaption.desktop.load_image", fail)
    else:
        candidate = tmp_path / ("invalid.txt" if kind == "unsupported" else "invalid.png")
        if kind == "directory":
            candidate.mkdir()
        elif kind in {"damaged", "unsupported"}:
            candidate.write_text("not an image")
    choose_replacement(app, monkeypatch, candidate)
    assert app.rows == {original.path: original}
    assert app.current == original.path and app.tree.selection() == (original.path,)
    assert original.path in app.image_errors and not app.dirty
    assert app.preview_source is None
    assert app.editor.get("1.0", "end-1c") == original.caption
    assert app.recovery.path.read_bytes() == recovery
    assert bool(errors) == (kind != "cancel")


@pytest.mark.parametrize("kind", ["exact", "case_slashes", "hardlink"])
def test_relink_rejects_duplicate_images(desktop, tmp_path, monkeypatch, kind):
    root, app, path = desktop
    missing = missing_workspace(root, app, tmp_path)
    existing = str(path.resolve())
    if kind == "case_slashes":
        existing = existing.upper().replace("\\", "/")
    app.rows[existing] = CaptionResult(existing)
    app.tree.insert("", "end", iid=existing, values=(path.name, "Ready"))
    candidate = path
    if kind == "hardlink":
        candidate = tmp_path / "alias.png"
        candidate.hardlink_to(path)
    errors = []
    monkeypatch.setattr(
        "lumacaption.desktop.messagebox.showerror", lambda *a, **kw: errors.append(a)
    )
    choose_replacement(app, monkeypatch, candidate)
    assert list(app.rows) == [missing.path, existing] and app.current == missing.path
    assert not app.dirty and missing.path in app.image_errors
    assert errors and "already in" in errors[0][1]


def test_relink_keeps_queue_order_and_other_rows(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    target = missing_workspace(root, app, tmp_path)
    before = CaptionResult(str(tmp_path / "before.png"))
    after = CaptionResult(str(tmp_path / "after.png"))
    app._apply_session(Session(results=[before, target, after]))
    app.tree.selection_set(target.path)
    root.update()
    choose_replacement(app, monkeypatch, path)
    root.update()
    expected_order = [before.path, str(path.resolve()), after.path]
    assert list(app.rows) == expected_order
    assert list(app.tree.get_children()) == expected_order
    assert app.rows[before.path] is before and app.rows[after.path] is after
    assert app.current == str(path.resolve())


def test_restored_original_path_can_be_relinked_in_place(desktop, tmp_path, monkeypatch):
    root, app, _ = desktop
    row = missing_workspace(root, app, tmp_path)
    original = replace(row)
    restored = tmp_path / "old folder" / "missing photo.png"
    restored.parent.mkdir()
    Image.new("RGB", (20, 10), "green").save(restored)
    choose_replacement(app, monkeypatch, restored)
    root.update()
    assert app.rows[row.path] == original
    assert list(app.tree.get_children()) == [row.path]
    assert row.path not in app.image_errors and app.dirty


def test_relink_button_tracks_missing_selection_and_busy_state(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    missing = missing_workspace(root, app, tmp_path)
    assert str(app.relink_button["state"]) == "normal"
    app.busy = True
    app._update_controls()
    assert str(app.relink_button["state"]) == "disabled"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.askopenfilename",
        lambda **kw: pytest.fail("No relink dialog while busy or on a healthy row"),
    )
    app._relink()
    app.busy = False
    app.add_paths([path])
    app.tree.selection_set(str(path.resolve()))
    root.update()
    assert str(app.relink_button["state"]) == "disabled"
    app._relink()
    app.tree.selection_set(missing.path)
    root.update()
    assert str(app.relink_button["state"]) == "normal"
    app.tree.selection_remove(missing.path)
    root.update()
    assert str(app.relink_button["state"]) == "disabled"


def test_image_moved_during_session_becomes_relinkable(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    app.add_paths([path])
    root.update()
    original = str(path.resolve())
    moved = path.rename(tmp_path / "renamed photo.png")
    app._select()
    assert original in app.image_errors
    assert app.tree.set(original, "state") == "Missing"
    assert str(app.relink_button["state"]) == "normal"
    choose_replacement(app, monkeypatch, moved)
    root.update()
    assert str(moved.resolve()) in app.rows and original not in app.rows


def test_reselecting_restored_image_clears_missing_warning(desktop, tmp_path):
    root, app, _ = desktop
    row = missing_workspace(root, app, tmp_path)
    restored = tmp_path / "old folder" / "missing photo.png"
    restored.parent.mkdir()
    Image.new("RGB", (20, 10), "green").save(restored)
    app._select()
    assert row.path not in app.image_errors and not app.dirty
    assert app.tree.set(row.path, "state") == "Edited"
    assert str(app.relink_button["state"]) == "disabled"


def test_relinked_pending_row_generates_from_replacement_only_when_requested(
    desktop, tmp_path, monkeypatch
):
    root, app, path = desktop
    missing_workspace(root, app, tmp_path, status="pending")
    seen = []

    class Stub:
        offline = False

        def prepare(self, status):
            pass

        def caption(self, image, options):
            seen.append(image.getpixel((0, 0)))
            return "A blue replacement"

    app.engine = Stub()
    choose_replacement(app, monkeypatch, path)
    root.update()
    assert not seen and str(app.generate_button["state"]) == "normal"
    app._start()
    pump_until(root, lambda: not app.busy)
    assert seen == [(0, 0, 255)]
    assert app.rows[str(path.resolve())].caption == "A blue replacement"
    assert app.rows[str(path.resolve())].status == "done"


def keyboard_window(root, app):
    """Map a real Tk window so generated keys use the actual binding/focus chain."""
    root.deiconify()
    root.update()
    app.add_button.focus_force()
    root.update()


def press(root, sequence):
    target = root.focus_get()
    assert target is not None
    target.event_generate(sequence)
    root.update()


def test_keyboard_add_generate_edit_export_save_and_open(desktop, tmp_path, monkeypatch):
    import json

    root, app, path = desktop

    class Stub:
        offline = False

        def prepare(self, status):
            pass

        def caption(self, image, options):
            return "A blue rectangle"

    app.engine = Stub()
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.askopenfilenames", lambda **kw: (str(path),)
    )
    keyboard_window(root, app)
    press(root, "<Control-i>")
    assert root.focus_get() == app.tree
    assert app.tree.focus() == str(path.resolve())
    press(root, "<Control-Return>")
    pump_until(root, lambda: not app.busy)
    assert root.focus_get() == app.tree
    press(root, "<Return>")
    assert root.focus_get() == app.editor
    app.editor.tag_add("sel", "1.0", "end-1c")
    # Replace through Tk's real text key binding, rather than calling _save_edit.
    press(root, "<Key-x>")
    assert app.rows[str(path.resolve())].caption == "x"

    destination = tmp_path / "keyboard.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(destination)
    )
    press(root, "<Control-e>")
    assert json.loads(destination.read_text())["results"][0]["caption"] == "x"
    assert app.editor.get("1.0", "end-1c") == "x"
    session = tmp_path / "keyboard.lumacaption.json"
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.asksaveasfilename", lambda **kw: str(session)
    )
    press(root, "<Control-s>")
    assert load_session(session).results[0].caption == "x" and not app.dirty
    monkeypatch.setattr("lumacaption.desktop.filedialog.askopenfilename", lambda **kw: str(session))
    press(root, "<Control-o>")
    assert root.focus_get() == app.tree
    assert app.rows[str(path.resolve())].caption == "x"
    press(root, "<F6>")
    assert root.focus_get() == app.editor
    press(root, "<Shift-F6>")
    assert root.focus_get() == app.tree


def test_editor_tab_traversal_never_inserts_tabs(desktop):
    root, app, path = desktop
    app._apply_session(Session(results=[CaptionResult(str(path), caption="Draft", status="done")]))
    keyboard_window(root, app)
    press(root, "<F6>")
    assert root.focus_get() == app.editor
    press(root, "<Tab>")
    assert root.focus_get() == app.copy_button
    press(root, "<Shift-Tab>")
    assert root.focus_get() == app.editor
    press(root, "<Shift-Tab>")
    assert root.focus_get() == app.offline_check
    assert app.editor.get("1.0", "end-1c") == "Draft"
    assert not app.dirty


def test_keyboard_queue_arrows_select_matching_caption(desktop, tmp_path):
    root, app, path = desktop
    second = tmp_path / "second.png"
    Image.new("RGB", (20, 20), "green").save(second)
    app._apply_session(
        Session(
            results=[
                CaptionResult(str(path), caption="Blue", status="done"),
                CaptionResult(str(second), caption="Green", status="done"),
            ]
        )
    )
    keyboard_window(root, app)
    app._focus_queue()
    press(root, "<Down>")
    assert app.current == str(second)
    assert app.editor.get("1.0", "end-1c") == "Green"
    press(root, "<Return>")
    assert root.focus_get() == app.editor


def test_busy_shortcuts_respect_disabled_controls_and_escape(desktop, monkeypatch):
    root, app, path = desktop
    app.add_paths([path])
    monkeypatch.setattr("lumacaption.desktop.threading.Thread.start", lambda self: None)
    keyboard_window(root, app)
    app.generate_button.focus_set()
    press(root, "<Control-Return>")
    assert app.busy and root.focus_get() == app.cancel_button
    for name in ("askopenfilenames", "askopenfilename", "asksaveasfilename", "askdirectory"):
        monkeypatch.setattr(
            "lumacaption.desktop.filedialog." + name,
            lambda **kw: pytest.fail("A disabled shortcut opened a dialog"),
        )
    for sequence in ("<Control-i>", "<Control-Shift-I>", "<Control-o>", "<Control-s>"):
        press(root, sequence)
    press(root, "<Escape>")
    assert app.cancel_event.is_set()
    assert root.focus_get() == app.tree
    app.events.put(("finished", None))
    app._poll()
    status = app.status.get()
    press(root, "<Escape>")
    assert app.status.get() == status and not app.busy


def test_open_shortcut_keeps_edits_when_replacement_cancelled(desktop, tmp_path, monkeypatch):
    root, app, path = desktop
    app._apply_session(Session(results=[CaptionResult(str(path), caption="Draft", status="done")]))
    other = tmp_path / "empty.lumacaption.json"
    save_session(Session(), other)
    monkeypatch.setattr("lumacaption.desktop.filedialog.askopenfilename", lambda **kw: str(other))
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **kw: None)
    keyboard_window(root, app)
    press(root, "<F6>")
    app.editor.insert("end", " changed")
    root.update()
    press(root, "<Control-o>")
    assert root.focus_get() == app.editor
    assert app.editor.get("1.0", "end-1c") == "Draft changed"
    assert app.dirty and str(path) in app.rows


def test_folder_and_help_shortcuts_and_modal_isolation(desktop, monkeypatch):
    root, app, path = desktop
    monkeypatch.setattr(
        "lumacaption.desktop.filedialog.askdirectory", lambda **kw: str(path.parent)
    )
    help_calls = []
    monkeypatch.setattr(
        "lumacaption.desktop.messagebox.showinfo", lambda *a, **kw: help_calls.append(a)
    )
    keyboard_window(root, app)
    press(root, "<Control-Shift-I>")
    assert str(path.resolve()) in app.rows
    press(root, "<F1>")
    assert len(help_calls) == 1 and "Ctrl+Enter" in help_calls[0][1]
    modal = tk.Toplevel(root)
    modal.update()
    modal.grab_set()
    try:
        # Even a queued key for the workspace cannot act during a dialog grab.
        app.tree.event_generate("<F1>")
        root.update()
        assert len(help_calls) == 1
    finally:
        modal.grab_release()
        modal.destroy()


def test_tab_order_reaches_all_enabled_controls_and_skips_disabled_editor(desktop):
    root, app, _ = desktop
    keyboard_window(root, app)
    seen = []
    for _ in range(len(app.keyboard_controls) + 1):
        current = root.focus_get()
        if current in seen:
            break
        seen.append(current)
        press(root, "<Tab>")
    assert root.focus_get() == app.add_button
    assert app.editor not in seen
    assert app.generate_button not in seen
    assert app.help_button in seen and app.tree in seen and app.length_box in seen
    enabled = [
        widget
        for widget in app.keyboard_controls
        if widget != app.editor and not widget.instate(["disabled"])
    ]
    assert seen == enabled


def test_controls_remain_visible_at_minimum_window_size(desktop):
    root, app, _ = desktop
    keyboard_window(root, app)
    root.geometry("960x680")
    root.update()
    for widget in app.keyboard_controls:
        assert widget.winfo_viewable(), widget
        assert widget.winfo_width() > 1 and widget.winfo_height() > 1, widget
        assert widget.winfo_rooty() >= root.winfo_rooty(), widget
        assert (
            widget.winfo_rooty() + widget.winfo_height() <= root.winfo_rooty() + root.winfo_height()
        ), widget


def test_cancelled_add_shortcut_and_undo_preserve_editor_text(desktop, monkeypatch):
    root, app, path = desktop
    app._apply_session(Session(results=[CaptionResult(str(path), caption="Draft", status="done")]))
    monkeypatch.setattr("lumacaption.desktop.filedialog.askopenfilenames", lambda **kw: ())
    keyboard_window(root, app)
    press(root, "<F6>")
    press(root, "<Control-i>")
    assert app.editor.get("1.0", "end-1c") == "Draft"
    assert not app.dirty
    app.editor.mark_set("insert", "end-1c")
    press(root, "<Key-x>")
    assert app.editor.get("1.0", "end-1c") == "Draftx"
    press(root, "<Control-z>")
    assert app.editor.get("1.0", "end-1c") == "Draft"


def test_batch_completion_does_not_steal_focus_from_editor(desktop):
    root, app, path = desktop
    app._apply_session(Session(results=[CaptionResult(str(path), caption="Draft", status="done")]))
    keyboard_window(root, app)
    press(root, "<F6>")
    app.busy = True
    app._update_controls()
    app.events.put(("finished", None))
    app._poll()
    root.update()
    assert root.focus_get() == app.editor
