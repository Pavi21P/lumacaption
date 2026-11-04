"""Integration tests exercise our Tk widgets with a synthetic model, without downloads."""

import time
import tkinter as tk

import pytest
from PIL import Image

from lumacaption.batch import CaptionResult
from lumacaption.desktop import CaptionApp


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    root = tk.Tk()
    root.withdraw()
    app = CaptionApp(root)
    monkeypatch.setattr("lumacaption.desktop.messagebox.showerror", lambda *a, **k: None)
    monkeypatch.setattr("lumacaption.desktop.messagebox.askyesno", lambda *a, **k: True)
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
    assert app.dirty is False
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
