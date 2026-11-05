"""Integration tests exercise our Tk widgets with a synthetic model, without downloads."""

import time
import tkinter as tk

import pytest
from PIL import Image

from lumacaption.batch import CaptionResult
from lumacaption.desktop import CaptionApp
from lumacaption.engine import CaptionOptions
from lumacaption.sessions import Session, load_session, save_session


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    root = tk.Tk()
    root.withdraw()
    app = CaptionApp(root)
    monkeypatch.setattr("lumacaption.desktop.messagebox.showerror", lambda *a, **k: None)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesno", lambda *a, **k: True)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesnocancel", lambda *a, **k: False)
    path = tmp_path / "my picture.png"
    Image.new("RGB", (40, 20), "blue").save(path)
    yield root, app, path
    app.closed = True
    # Cancel scheduled callbacks before destroying the Tcl interpreter.
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
