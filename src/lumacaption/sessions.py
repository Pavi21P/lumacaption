"""Versioned workspace storage; loading never opens images or starts inference.

Session files are UTF-8 JSON, separate from caption exports. Paths are absolute
and preserved even when images are missing. Callers decide how to display them.
"""

from __future__ import annotations

import json
import math
import ntpath
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path, PureWindowsPath

from . import __version__
from .batch import CaptionResult
from .engine import CaptionOptions
from .images import MAX_BATCH

FORMAT = "lumacaption-session"
SCHEMA_VERSION = 1
MAX_SESSION_BYTES = 16 * 1024 * 1024
MAX_TEXT_LENGTH = 16_384


class SessionError(ValueError):
    """Invalid, unsupported, or oversized session data."""


@dataclass
class Session:
    results: list[CaptionResult] = field(default_factory=list)
    options: CaptionOptions = field(default_factory=CaptionOptions)
    offline: bool = False
    recursive: bool = False


def _keys(value: object, expected: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != expected:
        raise SessionError(f"{label} has missing or unexpected fields.")
    return value


def _text(value: object, label: str, limit: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str) or len(value) > limit or "\x00" in value:
        raise SessionError(f"{label} must be text of at most {limit} characters without NUL.")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise SessionError(f"{label} contains invalid Unicode.") from exc
    return value


def _boolean(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise SessionError(f"{label} must be true or false.")
    return value


def _path_key(path: str) -> str:
    # Windows comparison without resolving or accessing source images.
    return ntpath.normcase(ntpath.normpath(path))


def _decode(document: object) -> Session:
    document = _keys(
        document, {"format", "schema_version", "app_version", "settings", "results"}, "Session"
    )
    if document["format"] != FORMAT:
        raise SessionError("This is not a LumaCaption session file.")
    if type(document["schema_version"]) is not int or document["schema_version"] != SCHEMA_VERSION:
        raise SessionError("Unsupported session version. This app supports version 1.")
    if not _text(document["app_version"], "App version", 128):
        raise SessionError("App version must not be empty.")
    settings = _keys(document["settings"], {"length", "beams", "offline", "recursive"}, "Settings")
    length = _text(settings["length"], "Caption length", 32)
    if type(settings["beams"]) is not int:
        raise SessionError("Beam count must be an integer.")
    try:
        options = CaptionOptions(length=length, beams=settings["beams"])
    except ValueError as exc:
        raise SessionError(str(exc)) from exc
    session = Session(
        options=options,
        offline=_boolean(settings["offline"], "Offline setting"),
        recursive=_boolean(settings["recursive"], "Recursive setting"),
    )
    rows = document["results"]
    if not isinstance(rows, list) or len(rows) > MAX_BATCH:
        raise SessionError(f"A session must contain a list of at most {MAX_BATCH} images.")
    seen: set[str] = set()
    fields = set(CaptionResult.__dataclass_fields__)
    for index, item in enumerate(rows):
        label = f"Image {index + 1}"
        row = dict(_keys(item, fields, label))
        path = _text(row["path"], f"{label} path", 32_767)
        if not (Path(path).is_absolute() or PureWindowsPath(path).is_absolute()):
            raise SessionError(f"{label} must have an absolute image path.")
        key = _path_key(path)
        if key in seen:
            raise SessionError("A session cannot contain duplicate image paths.")
        seen.add(key)
        for name in ("caption", "generated_caption", "error"):
            _text(row[name], f"{label} {name}")
        for name in ("status", "model", "model_revision", "created_at"):
            _text(row[name], f"{label} {name}", 512)
        if row["status"] not in {"pending", "done", "error"}:
            raise SessionError(f"{label} has an unsupported status.")
        _boolean(row["edited"], f"{label} edited flag")
        elapsed = row["elapsed_seconds"]
        if type(elapsed) not in {int, float}:
            raise SessionError(f"{label} elapsed time must be a nonnegative finite number.")
        try:
            valid_elapsed = math.isfinite(elapsed) and elapsed >= 0
        except OverflowError:
            valid_elapsed = False
        if not valid_elapsed:
            raise SessionError(f"{label} elapsed time must be a nonnegative finite number.")
        try:
            created = datetime.fromisoformat(row["created_at"])
            if created.tzinfo is None:
                raise ValueError("missing timezone")
        except ValueError as exc:
            raise SessionError(
                f"{label} created_at must be an ISO timestamp with timezone."
            ) from exc
        session.results.append(CaptionResult(**row))
    return session


def _document(session: Session) -> dict:
    if not isinstance(session, Session) or not isinstance(session.options, CaptionOptions):
        raise SessionError("Expected a Session with CaptionOptions.")
    if not isinstance(session.results, list) or any(
        not isinstance(row, CaptionResult) for row in session.results
    ):
        raise SessionError("Session results must be a list of CaptionResult objects.")
    document = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "app_version": __version__,
        "settings": {
            "length": session.options.length,
            "beams": session.options.beams,
            "offline": session.offline,
            "recursive": session.recursive,
        },
        "results": [asdict(row) for row in session.results],
    }
    _decode(document)  # Validate mutable objects again at the persistence boundary.
    return document


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SessionError("Session JSON contains duplicate fields.")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise SessionError("Session JSON cannot contain NaN or Infinity.")


def load_session(source: Path) -> Session:
    """Return a fully validated detached workspace, or raise without partial state."""
    with Path(source).open("rb") as handle:
        data = handle.read(MAX_SESSION_BYTES + 1)
    if len(data) > MAX_SESSION_BYTES:
        raise SessionError("Session exceeds the 16 MB limit.")
    try:
        document = json.loads(
            data.decode("utf-8-sig"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, SessionError):
            raise
        raise SessionError("Cannot read session: invalid UTF-8 JSON.") from exc
    return _decode(document)


def save_session(session: Session, destination: Path, *, overwrite: bool = False) -> None:
    """Atomically save a validated session; overwrite requires explicit opt-in."""
    document = _document(session)
    destination = Path(destination).expanduser().resolve()
    if destination.suffix.lower() != ".json":
        raise SessionError("Choose a .json session file, such as workspace.lumacaption.json.")
    if any(_path_key(row.path) == _path_key(str(destination)) for row in session.results):
        raise SessionError("A session cannot replace an input image.")
    # Protect hard links and symlinks to existing input files as well.
    if destination.exists():
        for row in session.results:
            try:
                same_file = os.path.samefile(destination, row.path)
            except OSError:
                same_file = False
            if same_file:
                raise SessionError("A session cannot replace an input image.")
        if not overwrite:
            raise FileExistsError(f"{destination.name} already exists. Choose another name.")
    data = (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode(
        "utf-8"
    )
    if len(data) > MAX_SESSION_BYTES:
        raise SessionError("Session exceeds the 16 MB limit.")
    descriptor, name = tempfile.mkstemp(prefix=".lumacaption-session-", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)  # Fails if another writer created the target.
    finally:
        temporary.unlink(missing_ok=True)
