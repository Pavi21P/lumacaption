"""Opt-in real-model smoke test. Requires downloaded weights and local input images.

Run from the project root:
  .venv/Scripts/python.exe scripts/verify_offline.py IMAGE [IMAGE ...] --desktop
This never downloads weights. HTTP requests and network connections are blocked.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import socket
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from lumacaption.batch import run_batch
from lumacaption.engine import CaptionEngine, CaptionOptions, default_cache
from lumacaption.exporting import export_results
from lumacaption.images import collect_images


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, nargs="+")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--desktop", action="store_true", help="Also test the real Tk worker")
    parser.add_argument("--report", type=Path, help="Write a local JSON verification report")
    args = parser.parse_args()
    paths = collect_images(args.images)
    if args.report and args.report.exists():
        parser.error("Report already exists; choose a new filename.")
    before = {path: digest(path) for path in paths}
    attempts: list[str] = []

    def block_http(*_args, **_kwargs):
        attempts.append("http")
        raise AssertionError("Offline verification attempted an HTTP request.")

    original_connect = socket.socket.connect

    def block_network(sock, address):
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            attempts.append("socket")
            raise AssertionError("Offline verification attempted a network connection.")
        return original_connect(sock, address)

    started = time.perf_counter()
    with (
        patch("requests.sessions.Session.request", block_http),
        patch("socket.socket.connect", block_network),
    ):
        engine = CaptionEngine(offline=True, device=args.device)
        results = list(run_batch(paths, engine, CaptionOptions(), status=print))
        assert len(results) == len(paths)
        assert all(row.status == "done" and row.caption.strip() for row in results), results
        model = engine._model
        engine.prepare()
        assert engine._model is model, "The loaded model should be reused."

        with tempfile.TemporaryDirectory(prefix="lumacaption-verify-") as directory:
            json_path = Path(directory) / "captions.json"
            csv_path = Path(directory) / "captions.csv"
            export_results(results, json_path)
            export_results(results, csv_path)
            document = json.loads(json_path.read_text(encoding="utf-8"))
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            assert len(document["results"]) == len(csv_rows) == len(paths)
            assert document["results"][0]["caption"] == results[0].caption

        desktop_ok = False
        if args.desktop:
            import tkinter as tk

            from lumacaption.desktop import CaptionApp

            root = tk.Tk()
            root.withdraw()
            app = CaptionApp(root, offline=True, device=args.device, autosave=False)
            app.engine = engine
            errors: list[str] = []
            try:
                with patch(
                    "lumacaption.desktop.messagebox.showerror",
                    lambda title, message, **kwargs: errors.append(message),
                ):
                    app.add_paths([paths[0]])
                    app._start()
                    deadline = time.monotonic() + 120
                    while app.busy and time.monotonic() < deadline:
                        root.update()
                        time.sleep(0.02)
                    assert not app.busy, "Desktop worker timed out."
                    assert not errors, errors
                    row = app.rows[str(paths[0])]
                    assert row.status == "done"
                    assert row.caption == results[0].caption
                    assert app.progress["value"] == 1
                    desktop_ok = True
            finally:
                app.closed = True
                app.cancel_event.set()
                if app.preview_source:
                    app.preview_source.close()
                for callback in root.tk.call("after", "info"):
                    root.after_cancel(callback)
                root.destroy()

    assert not attempts, attempts
    assert before == {path: digest(path) for path in paths}, "An input image changed."
    report = {
        "offline_verified": True,
        "requested_device": engine.requested_device,
        "actual_device": engine.device,
        "fallback_reason": engine.fallback_reason,
        "network_attempts": len(attempts),
        "source_files_unchanged": True,
        "desktop_worker_verified": desktop_ok,
        "json_csv_exports_verified": True,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "cache_present": default_cache().is_dir(),
        "results": [
            {
                "filename": Path(row.path).name,
                "caption": row.caption,
                "elapsed_seconds": row.elapsed_seconds,
            }
            for row in results
        ],
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
