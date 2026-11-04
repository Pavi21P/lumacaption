"""Bounded, orientation-aware image loading without modifying source files."""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"})
MAX_FILE_BYTES = 40 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_BATCH = 1000


class ImageInputError(ValueError):
    """A readable input error suitable for display in the app."""


def collect_images(inputs: Iterable[Path], *, recursive: bool = False) -> list[Path]:
    """Deduplicate files in stable order; ignore unsupported files inside folders."""
    found: dict[str, Path] = {}
    for source in inputs:
        source = Path(source).expanduser().resolve()
        if source.is_dir():
            candidates = source.rglob("*") if recursive else source.iterdir()
            for path in candidates:
                if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                    found.setdefault(str(path.resolve()).casefold(), path.resolve())
                    if len(found) > MAX_BATCH:
                        raise ImageInputError(f"Choose at most {MAX_BATCH} images per batch.")
        elif source.is_file() and source.suffix.lower() in SUPPORTED_SUFFIXES:
            found.setdefault(str(source).casefold(), source)
        else:
            raise ImageInputError(f"Not a supported image or folder: {source.name}")
        if len(found) > MAX_BATCH:
            raise ImageInputError(f"Choose at most {MAX_BATCH} images per batch.")
    if not found:
        raise ImageInputError("No supported images found. Choose JPG, PNG, WebP, BMP, or TIFF.")
    return sorted(found.values(), key=lambda path: str(path).casefold())


def load_image(path: Path) -> Image.Image:
    """Return a detached RGB image, flattening transparency onto white."""
    path = Path(path)
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ImageInputError("Image exceeds the 40 MB file limit.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.width * source.height > MAX_PIXELS:
                    raise ImageInputError("Image exceeds the 40 megapixel limit.")
                # Animated formats use their first frame.
                oriented = ImageOps.exif_transpose(source)
                if oriented.mode in {"RGBA", "LA"} or "transparency" in oriented.info:
                    rgba = oriented.convert("RGBA")
                    background = Image.new("RGBA", rgba.size, "white")
                    return Image.alpha_composite(background, rgba).convert("RGB")
                return oriented.convert("RGB")
    except ImageInputError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageInputError("Image dimensions are too large to open safely.") from exc
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise ImageInputError(f"Cannot read {path.name}: damaged or unsupported image.") from exc
