"""Native Windows caption workspace; all Tk operations stay on the UI thread."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from .batch import CaptionResult, run_batch
from .engine import LENGTHS, CaptionEngine, CaptionOptions
from .exporting import export_results
from .images import MAX_BATCH, ImageInputError, collect_images, load_image

BG = "#f3f5f7"
INK = "#152a36"
MUTED = "#576b78"
ACCENT = "#087f75"
PANEL = "#ffffff"


class CaptionApp:
    def __init__(self, root: tk.Tk, *, offline: bool = False) -> None:
        self.root = root
        self.rows: dict[str, CaptionResult] = {}
        self.current: str | None = None
        self.preview_photo = None
        self.preview_source: Image.Image | None = None
        self.events: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.engine: CaptionEngine | None = None
        self.busy = False
        self.dirty = False
        self.closed = False
        self.batch_finished = 0
        self.batch_total = 0
        self.batch_error = False
        self.status = tk.StringVar(value="Add photos to begin. Your images stay on this computer.")
        self.summary = tk.StringVar(value="0 images")
        self.length = tk.StringVar(value="Standard")
        self.offline = tk.BooleanVar(value=offline)
        self.recursive = tk.BooleanVar(value=False)
        self._build()
        self.root.after(100, self._poll)

    def _build(self) -> None:
        self.root.title("LumaCaption")
        self.root.geometry("1160x780")
        self.root.minsize(960, 680)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.option_add("*Font", ("Segoe UI", 10))
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Card.TLabel", background=PANEL, foreground=INK)
        style.configure("TButton", padding=(13, 9), background="#e4ebee", foreground=INK)
        style.map("TButton", background=[("active", "#d5e2e6")])
        style.configure("Primary.TButton", background=ACCENT, foreground="white")
        style.map("Primary.TButton", background=[("disabled", "#9caeb1"), ("active", "#05655d")])
        style.configure("TCheckbutton", background=BG, foreground=INK)
        style.configure(
            "Treeview",
            rowheight=36,
            background=PANEL,
            fieldbackground=PANEL,
            foreground=INK,
            borderwidth=0,
        )
        style.configure("Treeview.Heading", background="#e7edf0", foreground=INK, padding=8)
        style.map("Treeview", background=[("selected", "#d9efea")], foreground=[("selected", INK)])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor="#dfe7ea")

        header = tk.Frame(self.root, bg=INK, padx=28, pady=20)
        header.pack(fill="x")
        tk.Label(
            header, text="LumaCaption", bg=INK, fg="white", font=("Segoe UI Semibold", 24)
        ).pack(side="left")
        tk.Label(
            header, text="YOUR PHOTOS, PUT INTO WORDS", bg=INK, fg="#a5d4cd", font=("Segoe UI", 10)
        ).pack(side="left", padx=24)
        tk.Label(
            header,
            text="LOCAL AI  /  CPU",
            bg="#23424b",
            fg="#bde8d9",
            padx=12,
            pady=6,
            font=("Segoe UI Semibold", 9),
        ).pack(side="right")

        toolbar = ttk.Frame(self.root, padding=(24, 16))
        toolbar.pack(fill="x")
        self.add_button = ttk.Button(toolbar, text="+ Add images", command=self._add_files)
        self.add_button.pack(side="left")
        self.folder_button = ttk.Button(toolbar, text="Open folder", command=self._add_folder)
        self.folder_button.pack(side="left", padx=8)
        self.recursive_check = ttk.Checkbutton(
            toolbar, text="Include subfolders", variable=self.recursive
        )
        self.recursive_check.pack(side="left", padx=8)
        self.clear_button = ttk.Button(toolbar, text="Clear workspace", command=self._clear)
        self.clear_button.pack(side="right")

        body = ttk.Frame(self.root, padding=(24, 0, 24, 10))
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, minsize=300)
        body.columnconfigure(1, weight=3, minsize=430)
        body.rowconfigure(0, weight=1)
        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        ttk.Label(left, text="IMAGE QUEUE", font=("Segoe UI Semibold", 10)).pack(anchor="w")
        ttk.Label(left, textvariable=self.summary, style="Muted.TLabel").pack(
            anchor="w", pady=(4, 10)
        )

        tree_frame = ttk.Frame(left)
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_frame, columns=("image", "state"), show="headings", selectmode="browse", height=11
        )
        self.tree.heading("image", text="Image")
        self.tree.heading("state", text="Status")
        self.tree.column("image", width=230, minwidth=120)
        self.tree.column("state", width=80, minwidth=75, stretch=False)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._select)
        self.tree.tag_configure("error", foreground="#b03928")
        self.tree.tag_configure("done", foreground="#087468")

        options = ttk.Frame(left, padding=(0, 14, 0, 0))
        options.pack(fill="x")
        ttk.Label(options, text="Caption length").pack(side="left")
        self.length_box = ttk.Combobox(
            options, textvariable=self.length, values=list(LENGTHS), state="readonly", width=12
        )
        self.length_box.pack(side="right")
        self.offline_check = ttk.Checkbutton(
            left, text="Offline — use downloaded model only", variable=self.offline
        )
        self.offline_check.pack(anchor="w", pady=(12, 6))
        ttk.Label(
            left,
            text="First use downloads about 1 GB. No API key needed.",
            style="Muted.TLabel",
            wraplength=340,
        ).pack(anchor="w", pady=(0, 10))
        self.generate_button = ttk.Button(
            left, text="Generate captions", style="Primary.TButton", command=self._start
        )
        self.generate_button.pack(fill="x")
        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(8, 0))
        self.retry_button = ttk.Button(actions, text="Retry errors", command=self._retry)
        self.retry_button.pack(side="left")
        self.cancel_button = ttk.Button(
            actions, text="Cancel batch", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="right")

        right = ttk.Frame(body, style="Card.TFrame", padding=18)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(
            right, text="PREVIEW & CAPTION", style="Card.TLabel", font=("Segoe UI Semibold", 10)
        ).pack(anchor="w", pady=(0, 10))
        self.preview = tk.Label(
            right,
            text="A little context for every photo.\n\nAdd images to start.",
            bg="#eaf0f1",
            fg=MUTED,
            font=("Segoe UI", 13),
        )
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _: self._draw_preview())
        self.filename = ttk.Label(
            right,
            text="No image selected",
            style="Card.TLabel",
            wraplength=460,
            font=("Segoe UI Semibold", 11),
        )
        self.filename.pack(anchor="w", pady=(12, 4))
        self.detail = ttk.Label(
            right,
            text="Review and edit generated text before sharing.",
            style="Card.TLabel",
            wraplength=460,
        )
        self.detail.pack(anchor="w", pady=(0, 8))
        self.editor = tk.Text(
            right,
            height=4,
            wrap="word",
            bg="#f6f8f9",
            fg=INK,
            insertbackground=ACCENT,
            relief="flat",
            padx=12,
            pady=10,
            font=("Segoe UI", 12),
            undo=True,
            state="disabled",
        )
        self.editor.pack(fill="x")
        self.editor.bind("<FocusOut>", lambda _: self._save_edit())
        self.editor.bind("<KeyRelease>", lambda _: self._save_edit())
        caption_actions = ttk.Frame(right, style="Card.TFrame")
        caption_actions.pack(fill="x", pady=(10, 0))
        ttk.Button(caption_actions, text="Copy caption", command=self._copy).pack(side="left")
        ttk.Button(caption_actions, text="Restore AI text", command=self._restore).pack(
            side="left", padx=8
        )
        self.export_button = ttk.Button(
            caption_actions, text="Export results", command=self._export
        )
        self.export_button.pack(side="right")

        footer = ttk.Frame(self.root, padding=(24, 0, 24, 14))
        footer.pack(fill="x")
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 7))
        ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=1060).pack(
            anchor="w"
        )
        self._update_controls()

    def add_paths(self, paths: list[Path]) -> None:
        try:
            discovered = collect_images(paths, recursive=self.recursive.get())
            new = [path for path in discovered if str(path) not in self.rows]
            if len(self.rows) + len(new) > MAX_BATCH:
                raise ImageInputError(f"Keep at most {MAX_BATCH} images in the workspace.")
            for path in new:
                key = str(path)
                self.rows[key] = CaptionResult(path=key)
                self.tree.insert("", "end", iid=key, values=(path.name, "Ready"))
            if not self.tree.selection() and self.rows:
                self.tree.selection_set(next(iter(self.rows)))
            self.status.set(f"Added {len(new)} image(s). Select Generate captions when ready.")
            self._update_controls()
        except (ImageInputError, OSError) as exc:
            messagebox.showerror("Could not add images", str(exc), parent=self.root)

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title="Choose images",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff")],
        )
        if paths:
            self.add_paths([Path(path) for path in paths])

    def _add_folder(self) -> None:
        path = filedialog.askdirectory(parent=self.root, title="Choose an image folder")
        if path:
            self.add_paths([Path(path)])

    def _select(self, _event=None) -> None:
        self._save_edit()
        selected = self.tree.selection()
        self.current = selected[0] if selected else None
        if self.preview_source:
            self.preview_source.close()
            self.preview_source = None
        if not self.current:
            return
        row = self.rows[self.current]
        self.filename.configure(text=Path(row.path).name)
        try:
            self.preview_source = load_image(Path(row.path))
            self.preview_source.thumbnail((1400, 1000), Image.Resampling.LANCZOS)
            self._draw_preview()
        except ImageInputError as exc:
            self.preview.configure(image="", text=str(exc))
        self._show_caption()

    def _draw_preview(self) -> None:
        if self.preview_source is None:
            return
        image = self.preview_source.copy()
        image.thumbnail(
            (max(40, self.preview.winfo_width() - 16), max(40, self.preview.winfo_height() - 16)),
            Image.Resampling.LANCZOS,
        )
        self.preview_photo = ImageTk.PhotoImage(image, master=self.root)
        self.preview.configure(image=self.preview_photo, text="")

    def _show_caption(self) -> None:
        row = self.rows.get(self.current)
        self.editor.configure(state="normal")
        self.editor.delete("1.0", "end")
        if row:
            self.editor.insert("1.0", row.caption)
            self.detail.configure(
                text=row.error
                if row.status == "error"
                else (
                    f"Generated in {row.elapsed_seconds:.1f}s · Editable draft"
                    if row.status == "done"
                    else "Ready to generate a caption."
                )
            )
        self.editor.configure(state="normal" if row and row.status == "done" else "disabled")

    def _save_edit(self) -> None:
        row = self.rows.get(self.current)
        if row and row.status == "done":
            text = self.editor.get("1.0", "end-1c").strip()
            if row.caption != text:
                row.caption = text
                row.edited = text != row.generated_caption
                self.dirty = True
                self.tree.set(row.path, "state", "Edited" if row.edited else "Done")

    def _copy(self) -> None:
        self._save_edit()
        row = self.rows.get(self.current)
        if row and row.caption:
            self.root.clipboard_clear()
            self.root.clipboard_append(row.caption)
            self.status.set("Caption copied.")

    def _restore(self) -> None:
        row = self.rows.get(self.current)
        if row and row.status == "done":
            row.caption = row.generated_caption
            row.edited = False
            self.dirty = True
            self.tree.set(row.path, "state", "Done")
            self._show_caption()

    def _start(self) -> None:
        if self.busy:
            return
        paths = [Path(row.path) for row in self.rows.values() if row.status == "pending"]
        if not paths:
            return
        self._save_edit()
        options = CaptionOptions(length=self.length.get())
        offline = self.offline.get()
        self.busy = True
        self.cancel_event.clear()
        self.batch_finished = 0
        self.batch_total = len(paths)
        self.batch_error = False
        self.progress.configure(value=0, maximum=len(paths))
        self.status.set("Preparing captioning model...")
        self._update_controls()
        threading.Thread(
            target=self._worker, args=(paths, options, offline), daemon=True, name="caption-worker"
        ).start()

    def _worker(self, paths: list[Path], options: CaptionOptions, offline: bool) -> None:
        try:
            if self.engine is None or self.engine.offline != offline:
                self.engine = CaptionEngine(offline=offline)
            for result in run_batch(
                paths,
                self.engine,
                options,
                cancel=self.cancel_event,
                status=lambda text: self.events.put(("status", text)),
            ):
                self.events.put(("result", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))
        finally:
            self.events.put(("finished", None))

    def _poll(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "status":
                    self.status.set(payload)
                elif event == "result":
                    self.rows[payload.path] = payload
                    self.tree.item(
                        payload.path,
                        values=(
                            Path(payload.path).name,
                            "Done" if payload.status == "done" else "Error",
                        ),
                        tags=(payload.status,),
                    )
                    self.batch_finished += 1
                    self.progress.configure(value=self.batch_finished)
                    self.dirty = True
                    if self.current == payload.path:
                        self._show_caption()
                    self._update_controls()
                elif event == "error":
                    self.batch_error = True
                    self.status.set(payload)
                    messagebox.showerror("Captioning paused", payload, parent=self.root)
                elif event == "finished":
                    self.busy = False
                    if not self.batch_error:
                        errors = sum(row.status == "error" for row in self.rows.values())
                        verb = "Cancelled" if self.cancel_event.is_set() else "Finished"
                        self.status.set(
                            f"{verb}: {self.batch_finished} of {self.batch_total} "
                            f"processed · {errors} error(s). Export to save your results."
                        )
                    self._update_controls()
        except queue.Empty:
            pass
        if not self.closed:
            self.root.after(100, self._poll)

    def _cancel(self) -> None:
        self.cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status.set(
            "Cancelling after the current model operation. Completed captions are kept."
        )

    def _retry(self) -> None:
        for row in self.rows.values():
            if row.status == "error":
                row.status = "pending"
                row.error = ""
                self.tree.item(row.path, values=(Path(row.path).name, "Ready"), tags=())
        self._show_caption()
        self._start()

    def _export(self) -> None:
        self._save_edit()
        results = [row for row in self.rows.values() if row.status in {"done", "error"}]
        if not results:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Export captions",
            initialfile="lumacaption-results.csv",
            defaultextension=".csv",
            filetypes=[("CSV spreadsheet", "*.csv"), ("JSON", "*.json")],
            confirmoverwrite=True,
        )
        if path:
            try:
                export_results(results, Path(path), overwrite=True)
                self.dirty = False
                self.status.set(f"Saved {len(results)} results to {Path(path).name}.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Export failed", str(exc), parent=self.root)

    def _clear(self) -> None:
        if self.busy:
            return
        self._save_edit()
        if self.dirty and not messagebox.askyesno(
            "Clear unexported captions?",
            "Unexported results will be lost. Clear the workspace?",
            parent=self.root,
        ):
            return
        self.current = None
        self.rows.clear()
        self.tree.delete(*self.tree.get_children())
        if self.preview_source:
            self.preview_source.close()
            self.preview_source = None
        self.preview_photo = None
        self.preview.configure(image="", text="Add images to start.")
        self.filename.configure(text="No image selected")
        self.detail.configure(text="Review and edit generated text before sharing.")
        self._show_caption()
        self.progress.configure(value=0)
        self.dirty = False
        self.status.set("Workspace cleared. Your original images are unchanged.")
        self._update_controls()

    def _update_controls(self) -> None:
        done = sum(row.status == "done" for row in self.rows.values())
        pending = any(row.status == "pending" for row in self.rows.values())
        errors = any(row.status == "error" for row in self.rows.values())
        self.summary.set(f"{len(self.rows)} images · {done} captioned")
        for widget in (
            self.add_button,
            self.folder_button,
            self.clear_button,
            self.offline_check,
            self.recursive_check,
        ):
            widget.configure(state="disabled" if self.busy else "normal")
        self.length_box.configure(state="disabled" if self.busy else "readonly")
        self.generate_button.configure(state="normal" if pending and not self.busy else "disabled")
        self.retry_button.configure(state="normal" if errors and not self.busy else "disabled")
        self.cancel_button.configure(
            state="normal" if self.busy and not self.cancel_event.is_set() else "disabled"
        )
        self.export_button.configure(state="normal" if done or errors else "disabled")

    def _close(self) -> None:
        self._save_edit()
        if (self.busy or self.dirty) and not messagebox.askyesno(
            "Close LumaCaption?",
            "Close the app? Running work will stop and unexported captions will be lost.",
            parent=self.root,
        ):
            return
        self.cancel_event.set()
        self.closed = True
        if self.preview_source:
            self.preview_source.close()
        self.root.destroy()


def main(*, offline: bool = False) -> None:
    root = tk.Tk()
    CaptionApp(root, offline=offline)
    root.mainloop()


if __name__ == "__main__":
    main()
