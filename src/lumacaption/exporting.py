"""Atomic exports with Excel-compatible CSV and input overwrite protection."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .batch import CaptionResult

COLUMNS = (
    "filename",
    "caption",
    "status",
    "error",
    "elapsed_seconds",
    "edited",
    "generated_caption",
    "model",
    "model_revision",
    "created_at",
)


def spreadsheet_safe(value: object) -> object:
    """Prevent image names or edited captions being interpreted as formulas."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    if isinstance(value, str) and value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def export_results(
    results: list[CaptionResult], destination: Path, *, overwrite: bool = False
) -> None:
    destination = Path(destination).expanduser().resolve()
    if not results:
        raise ValueError("There are no results to export.")
    if destination.suffix.lower() not in {".csv", ".json"}:
        raise ValueError("Choose a .csv or .json export file.")
    if any(Path(item.path).resolve() == destination for item in results):
        raise ValueError("An export cannot replace an input image.")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"{destination.name} already exists. Choose another name.")
    # Do not create arbitrary parent trees on behalf of a mistyped path.
    descriptor, temp_name = tempfile.mkstemp(prefix=".lumacaption-", dir=destination.parent)
    temp_path = Path(temp_name)
    try:
        encoding = "utf-8-sig" if destination.suffix.lower() == ".csv" else "utf-8"
        with os.fdopen(descriptor, "w", encoding=encoding, newline="") as handle:
            if destination.suffix.lower() == ".json":
                json.dump(
                    {
                        "schema_version": 1,
                        "app_version": __version__,
                        "results": [asdict(item) for item in results],
                    },
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
                handle.write("\n")
            else:
                writer = csv.DictWriter(handle, fieldnames=COLUMNS)
                writer.writeheader()
                for item in results:
                    record = asdict(item)
                    record["filename"] = Path(record.pop("path")).name
                    writer.writerow({key: spreadsheet_safe(record[key]) for key in COLUMNS})
            handle.flush()
            os.fsync(handle.fileno())
        if overwrite:
            os.replace(temp_path, destination)
        else:
            # Hard-link creation fails if destination appeared since our check.
            os.link(temp_path, destination)
            temp_path.unlink()
    finally:
        temp_path.unlink(missing_ok=True)
