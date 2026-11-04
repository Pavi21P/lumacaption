"""Shared batch orchestration used by both the desktop app and CLI."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from time import perf_counter
from typing import Protocol

from PIL import Image

from .engine import MODEL_ID, MODEL_REVISION, CaptionOptions
from .images import load_image


class Captioner(Protocol):
    def prepare(self, status: Callable[[str], None] = ...) -> None: ...
    def caption(self, image: Image.Image, options: CaptionOptions) -> str: ...


@dataclass
class CaptionResult:
    path: str
    caption: str = ""
    status: str = "pending"
    error: str = ""
    elapsed_seconds: float = 0.0
    generated_caption: str = ""
    edited: bool = False
    model: str = MODEL_ID
    model_revision: str = MODEL_REVISION
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def run_batch(
    paths: Sequence[Path],
    engine: Captioner,
    options: CaptionOptions,
    *,
    cancel: Event | None = None,
    status: Callable[[str], None] = lambda _: None,
) -> Iterator[CaptionResult]:
    """Finish the current inference on cancel; don't start another image."""
    cancel = cancel or Event()
    prepared = False
    for index, path in enumerate(paths, start=1):
        if cancel.is_set():
            break
        status(f"Captioning {index} of {len(paths)}: {path.name}")
        started = perf_counter()
        result = CaptionResult(path=str(path))
        try:
            with load_image(path) as image:
                # Validate input before downloading the model.
                if not prepared:
                    engine.prepare(status)
                    prepared = True
                if cancel.is_set():
                    break
                result.caption = engine.caption(image, options)
                result.generated_caption = result.caption
                result.status = "done"
        except Exception as exc:
            from .engine import ModelUnavailableError

            if isinstance(exc, ModelUnavailableError):
                raise
            result.status = "error"
            result.error = str(exc)
        result.elapsed_seconds = round(perf_counter() - started, 3)
        yield result
