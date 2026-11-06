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
from .recovery import RecoveryStore, default_recovery_directory
from .sessions import Session, load_session, save_session

BG = "#f3f5f7"
INK = "#152a36"
MUTED = "#576b78"
ACCENT = "#087f75"
PANEL = "#ffffff"
AUTOSAVE_DELAY_MS = 1000


class CaptionApp:
    def __init__(
        self,
        root: tk.Tk,
        *,
        offline: bool = False,
        recovery_dir: Path | None = None,
        autosave: bool = True,
    ) -> None:
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
        self.session_path: Path | None = None
        self.image_errors: dict[str, str] = {}
        self.beams = 3
        self.recovery: RecoveryStore | None = None
        self.autosave_after: str | None = None
        self.autosave_status = tk.StringVar(value="Automatic recovery is off.")
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
        for variable in (self.length, self.offline, self.recursive):
            variable.trace_add("write", self._settings_changed)
        if autosave:
            self._initialize_recovery(recovery_dir or default_recovery_directory())
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

        sessions = ttk.Frame(self.root, padding=(24, 0, 24, 12))
        sessions.pack(fill="x")
        self.open_session_button = ttk.Button(
            sessions, text="Open session", command=self._open_session
        )
        self.open_session_button.pack(side="left")
        self.save_session_button = ttk.Button(
            sessions, text="Save session", command=self._save_session
        )
        self.save_session_button.pack(side="left", padx=8)
        ttk.Label(
            sessions, text="Save your queue, captions, and settings.", style="Muted.TLabel"
        ).pack(side="left", padx=8)

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
        self.editor.bind("<<Modified>>", self._editor_modified)
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
        ttk.Label(
            footer, textvariable=self.autosave_status, style="Muted.TLabel", wraplength=1060
        ).pack(anchor="w", pady=(3, 0))
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
            if new:
                self._mark_dirty()
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
                text=self.image_errors.get(row.path) or row.error
                if row.path in self.image_errors or row.status == "error"
                else (
                    f"Generated in {row.elapsed_seconds:.1f}s · Editable draft"
                    if row.status == "done"
                    else "Ready to generate a caption."
                )
            )
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.editor.configure(state="normal" if row and row.status == "done" else "disabled")

    def _editor_modified(self, _event=None) -> None:
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self._save_edit()

    def _save_edit(self) -> None:
        row = self.rows.get(self.current)
        if row and row.status == "done":
            text = self.editor.get("1.0", "end-1c").strip()
            if row.caption != text:
                row.caption = text
                row.edited = text != row.generated_caption
                self._mark_dirty()
                self._refresh_row(row)

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
            self._mark_dirty()
            self._refresh_row(row)
            self._show_caption()

    def _start(self) -> None:
        if self.busy:
            return
        paths = [
            Path(row.path)
            for row in self.rows.values()
            if row.status == "pending" and row.path not in self.image_errors
        ]
        if not paths:
            return
        self._save_edit()
        options = CaptionOptions(length=self.length.get(), beams=self.beams)
        offline = self.offline.get()
        self.busy = True
        self.cancel_event.clear()
        self.batch_finished = 0
        self.batch_total = len(paths)
        self.batch_error = False
        self.progress.configure(value=0, maximum=len(paths))
        self._mark_dirty()
        self._autosave_now()
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
                    self._mark_dirty()
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
                            f"processed · {errors} error(s). Save the session to keep your work."
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
        if self.busy:
            return
        self._save_edit()
        for row in self.rows.values():
            if row.status == "error" and row.path not in self.image_errors:
                self._mark_dirty()
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
                self.status.set(f"Exported {len(results)} results to {Path(path).name}.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Export failed", str(exc), parent=self.root)

    def _snapshot(self) -> Session:
        # Called only on the Tk thread; persistence finishes before UI state can change.
        return Session(
            results=list(self.rows.values()),
            options=CaptionOptions(length=self.length.get(), beams=self.beams),
            offline=self.offline.get(),
            recursive=self.recursive.get(),
        )

    def _initialize_recovery(self, directory: Path) -> None:
        try:
            self.recovery = RecoveryStore(directory)
            session = self.recovery.load()
            self.autosave_status.set("Automatic recovery ready.")
            if session is not None:
                recover = messagebox.askyesno(
                    "Recover unsaved workspace?",
                    "An unsaved workspace was found. Restore its queue, captions, and settings? "
                    "Generation will stay stopped. No discards this recovery copy.",
                    parent=self.root,
                )
                if recover:
                    self._apply_session(session)
                    self._mark_dirty()
                    self.status.set(
                        "Workspace recovered. Review it and use Save session to keep it."
                    )
                else:
                    self.recovery.discard()
        except (OSError, ValueError) as exc:
            # Preserve unreadable recovery files for manual inspection.
            self._release_recovery()
            self.autosave_status.set(f"Recovery unavailable: {exc} Use Save session.")

    def _mark_dirty(self) -> None:
        self.dirty = True
        if self.recovery is not None and not self.closed:
            self._cancel_autosave()
            self.autosave_after = self.root.after(AUTOSAVE_DELAY_MS, self._autosave_now)
            self.autosave_status.set("Recovery copy pending...")

    def _cancel_autosave(self) -> None:
        if self.autosave_after is not None:
            self.root.after_cancel(self.autosave_after)
            self.autosave_after = None

    def _autosave_now(self) -> None:
        self._cancel_autosave()
        if self.closed or self.recovery is None:
            return
        self._save_edit()
        self._cancel_autosave()
        if not self.dirty:
            return
        try:
            self.recovery.save(self._snapshot())
            self.autosave_status.set("Recovery copy saved locally. Use Save session to keep it.")
        except (OSError, ValueError) as exc:
            self.autosave_status.set(f"Recovery save failed: {exc} Use Save session.")
        # Autosave never clears dirty: explicit discard/save decisions still matter.

    def _discard_recovery(self) -> bool:
        self._cancel_autosave()
        if self.recovery is not None:
            try:
                self.recovery.discard()
            except OSError as exc:
                self.autosave_status.set(f"Could not remove recovery copy: {exc}")
                messagebox.showerror(
                    "Recovery cleanup failed",
                    "The previous recovery copy could not be removed. "
                    "Your workspace is kept open. Check storage permissions and try again.",
                    parent=self.root,
                )
                return False
            self.autosave_status.set("Automatic recovery ready.")
        return True

    def _release_recovery(self) -> None:
        self._cancel_autosave()
        if self.recovery is not None:
            self.recovery.close()
            self.recovery = None

    def _settings_changed(self, *_args) -> None:
        self._mark_dirty()

    def _refresh_row(self, row: CaptionResult) -> None:
        state = (
            "Missing"
            if row.path in self.image_errors
            else "Edited"
            if row.status == "done" and row.edited
            else {"pending": "Ready", "done": "Done", "error": "Error"}[row.status]
        )
        self.tree.item(
            row.path,
            values=(Path(row.path).name, state),
            tags=("error" if row.path in self.image_errors else row.status,),
        )

    def _save_session(self) -> bool:
        if self.busy:
            return False
        self._save_edit()
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save session",
            initialfile=self.session_path.name
            if self.session_path
            else "workspace.lumacaption.json",
            initialdir=str(self.session_path.parent) if self.session_path else None,
            defaultextension=".lumacaption.json",
            filetypes=[("LumaCaption session", "*.lumacaption.json"), ("JSON", "*.json")],
            confirmoverwrite=True,
        )
        if not path:
            return False
        try:
            if self.recovery and Path(path).resolve() == self.recovery.path.resolve():
                raise ValueError("Choose a location outside the automatic recovery file.")
            save_session(self._snapshot(), Path(path), overwrite=True)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save session", str(exc), parent=self.root)
            return False
        self.session_path = Path(path)
        self.dirty = False
        self._discard_recovery()
        self.status.set(f"Session saved to {self.session_path.name}.")
        return True

    def _confirm_replace(self) -> bool:
        self._save_edit()
        if not self.dirty:
            return True
        choice = messagebox.askyesnocancel(
            "Save workspace changes?",
            "Save your queue, captions, and settings before continuing?\n"
            "Yes: save a session. No: discard changes. Cancel: keep working.",
            parent=self.root,
        )
        if choice is None:
            return False
        return self._save_session() if choice else True

    def _open_session(self) -> None:
        if self.busy:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open session",
            filetypes=[("LumaCaption session", "*.lumacaption.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        # Validate before offering to replace anything. Read again after a save:
        # the user may save the active workspace over the file being opened.
        try:
            session = load_session(Path(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not open session", str(exc), parent=self.root)
            return
        self._save_edit()
        had_changes = self.dirty
        if not self._confirm_replace():
            return
        try:
            if had_changes and not self.dirty:
                session = load_session(Path(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not open session", str(exc), parent=self.root)
            return
        if not self._discard_recovery():
            return
        self._apply_session(session, Path(path))
        self.status.set(
            f"Opened {self.session_path.name}: {len(self.rows)} image(s), "
            f"{len(self.image_errors)} missing or unavailable. "
            "Generation starts only when requested."
        )

    def _apply_session(self, session: Session, path: Path | None = None) -> None:
        missing = {}
        for row in session.results:
            try:
                available = Path(row.path).is_file()
            except OSError:
                available = False
            if not available:
                missing[row.path] = "Image missing or unavailable. Saved captions are kept."
        self._reset_workspace()
        self.rows = {row.path: row for row in session.results}
        self.image_errors = missing
        self.length.set(session.options.length)
        self.beams = session.options.beams
        self.offline.set(session.offline)
        self.recursive.set(session.recursive)
        for row in session.results:
            self.tree.insert("", "end", iid=row.path)
            self._refresh_row(row)
        self.session_path = path
        self.dirty = False
        if self.rows:
            self.tree.selection_set(next(iter(self.rows)))
            self._select()
        self._cancel_autosave()
        if self.recovery is not None:
            self.autosave_status.set("Automatic recovery ready.")
        self._update_controls()

    def _reset_workspace(self) -> None:
        self._cancel_autosave()
        # Clear the selection before replacing rows so queued selection events
        # cannot apply the old editor contents to a restored caption.
        self.current = None
        self.rows.clear()
        self.image_errors.clear()
        self.tree.delete(*self.tree.get_children())
        if self.preview_source:
            self.preview_source.close()
            self.preview_source = None
        self.preview_photo = None
        self.preview.configure(image="", text="Add images to start.")
        self.filename.configure(text="No image selected")
        self.detail.configure(text="Review and edit generated text before sharing.")
        self._show_caption()
        self.editor.edit_reset()
        self.progress.configure(value=0)
        self.session_path = None
        self.dirty = False

    def _clear(self) -> None:
        if self.busy or not self._confirm_replace():
            return
        if not self._discard_recovery():
            return
        self._reset_workspace()
        self.status.set("Workspace cleared. Your original images are unchanged.")
        self._update_controls()

    def _update_controls(self) -> None:
        done = sum(row.status == "done" for row in self.rows.values())
        pending = any(
            row.status == "pending" and row.path not in self.image_errors
            for row in self.rows.values()
        )
        errors = any(
            row.status == "error" and row.path not in self.image_errors
            for row in self.rows.values()
        )
        self.summary.set(f"{len(self.rows)} images · {done} captioned")
        for widget in (
            self.add_button,
            self.folder_button,
            self.clear_button,
            self.open_session_button,
            self.save_session_button,
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
        self.export_button.configure(
            state="normal"
            if any(row.status in {"done", "error"} for row in self.rows.values())
            else "disabled"
        )

    def _close(self) -> None:
        self._save_edit()
        if self.busy:
            if not messagebox.askyesno(
                "Close LumaCaption?",
                "A batch is running. Close and discard unsaved work? "
                "Choose No to return, cancel the batch, and save first.",
                parent=self.root,
            ):
                return
        elif not self._confirm_replace():
            return
        if not self._discard_recovery():
            return
        self._release_recovery()
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
