"""Command line entry point; run without arguments for the desktop app."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .batch import run_batch
from .engine import LENGTHS, CaptionEngine, CaptionOptions, ModelUnavailableError
from .exporting import export_results
from .images import ImageInputError, collect_images


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lumacaption", description="Local image captions for Windows"
    )
    parser.add_argument("inputs", nargs="*", type=Path, help="Image files or folders")
    parser.add_argument("--recursive", action="store_true", help="Include subfolders")
    parser.add_argument("--offline", action="store_true", help="Only use cached model files")
    parser.add_argument("--length", choices=LENGTHS, default="Standard")
    parser.add_argument("--beams", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--output", type=Path, help="Export to .csv or .json")
    parser.add_argument("--force", action="store_true", help="Replace an existing export")
    parser.add_argument("--download-model", action="store_true", help="Cache the model and exit")
    args = parser.parse_args(argv)
    status = lambda message: print(message, file=sys.stderr, flush=True)  # noqa: E731
    engine = CaptionEngine(offline=args.offline)
    try:
        if args.download_model:
            engine.prepare(status)
            return 0
        if not args.inputs:
            from .desktop import main as desktop_main

            desktop_main(offline=args.offline)
            return 0
        if args.output:
            if args.output.suffix.lower() not in {".csv", ".json"}:
                parser.error("--output must end in .csv or .json")
            if args.output.exists() and not args.force:
                parser.error("Output already exists; choose another path or pass --force")
        paths = collect_images(args.inputs, recursive=args.recursive)
        results = []
        for result in run_batch(
            paths, engine, CaptionOptions(args.length, args.beams), status=status
        ):
            results.append(result)
            print(
                f"{Path(result.path).name}: {result.caption or 'ERROR: ' + result.error}",
                flush=True,
            )
        if args.output:
            export_results(results, args.output, overwrite=args.force)
            status(f"Saved {len(results)} result(s) to {args.output}")
        return 1 if any(item.status == "error" for item in results) else 0
    except (ImageInputError, ModelUnavailableError, OSError, ValueError) as exc:
        print(f"LumaCaption: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
