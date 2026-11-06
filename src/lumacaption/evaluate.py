"""Private, offline evaluation CLI: python -m lumacaption.evaluate --help."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from .config import MODEL_ID, MODEL_REVISION, default_cache
from .engine import CaptionEngine, CaptionOptions, ModelUnavailableError
from .evaluation import (
    PROTOCOL,
    EvaluationError,
    build_manifest,
    digest,
    exclusions_from_reports,
    load_manifest,
    rank,
    score,
)
from .images import ImageInputError, load_image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRIVATE_ROOT = PROJECT_ROOT / ".local" / "evaluation" / "v1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def json_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def write_new(path: Path, data: bytes) -> None:
    """Exclusive creation protects frozen manifests and previous run artifacts."""
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def checkpoint(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        handle.write(json_bytes(report))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


@contextmanager
def offline_guard():
    """Block Python HTTP/socket access during all model operations and count attempts."""
    attempts = []

    def blocked(*_args, **_kwargs):
        attempts.append("blocked")
        raise RuntimeError("Network access is disabled during evaluation.")

    with (
        patch.dict(
            os.environ,
            {
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
                "DISABLE_SAFETENSORS_CONVERSION": "true",
            },
        ),
        patch("requests.sessions.Session.request", blocked),
        patch.object(socket.socket, "connect", blocked),
        patch.object(socket.socket, "connect_ex", blocked),
        patch.object(socket.socket, "sendto", blocked),
        patch.object(socket, "getaddrinfo", blocked),
    ):
        yield attempts


def environment() -> dict:
    def git(*args):
        try:
            return subprocess.check_output(
                ["git", "-C", str(PROJECT_ROOT), *args],
                stderr=subprocess.DEVNULL,
                timeout=10,
                text=True,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            return None

    versions = {}
    for name in ("Pillow", "torch", "transformers"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    cpu = platform.processor()
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            ) as key:
                cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    state = git("status", "--porcelain")
    return {
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": None if state is None else bool(state),
        "python": platform.python_version(),
        "packages": versions,
        "os": {"system": platform.system(), "release": platform.release()},
        "cpu": cpu,
        "cpu_threads": min(4, os.cpu_count() or 1),
        "protocol_sha256": digest(PROJECT_ROOT / "docs" / "EVALUATION.md"),
        "lock_sha256": digest(PROJECT_ROOT / "requirements-lock.txt"),
        "source_sha256": {
            p.name: digest(p) for p in sorted((PROJECT_ROOT / "src" / "lumacaption").glob("*.py"))
        },
    }


class InputChangedError(EvaluationError):
    """Image bytes differ from the frozen manifest."""


def caption_row(row: dict, image_root: Path, engine) -> tuple[str, float]:
    path = image_root / row["id"]
    if row["image_sha256"] is None:
        raise InputChangedError("Image was unreadable when the manifest was frozen.")
    if digest(path) != row["image_sha256"]:
        raise InputChangedError("Image differs from the frozen manifest.")
    started = time.perf_counter()
    with load_image(path) as image:
        caption = engine.caption(image, CaptionOptions())
    elapsed = time.perf_counter() - started
    if digest(path) != row["image_sha256"]:
        raise InputChangedError("Image changed during evaluation.")
    if not isinstance(caption, str) or not caption.strip():
        raise EvaluationError("Empty or invalid model output.")
    return caption, elapsed


def error_category(exc: Exception) -> str:
    if isinstance(exc, InputChangedError):
        return "input_changed_or_unreadable_at_freeze"
    if isinstance(exc, ModelUnavailableError):
        return "model_unavailable"
    if isinstance(exc, ImageInputError):
        return "invalid_image"
    if isinstance(exc, OSError):
        return "image_unreadable"
    return "caption_failed"


def summarize(report: dict, manifest: dict) -> None:
    rows = report["results"]
    counts = {
        status: sum(row["status"] == status for row in rows)
        for status in ("done", "error", "not_processed")
    }
    successful = sorted(row["elapsed_seconds"] for row in rows if row["status"] == "done")
    report["summary"] = {
        "counts": counts,
        "completion_rate": counts["done"] / len(rows),
        "metrics": score(
            [row["generated_caption"] if row["status"] == "done" else "" for row in rows],
            [row["references"] for row in manifest["images"]["test"]],
        ),
        "timing": {
            "successful_count": len(successful),
            "median_seconds": statistics.median(successful) if successful else None,
            "p95_seconds": successful[math.ceil(0.95 * len(successful)) - 1]
            if successful
            else None,
            "failed_seconds": [row["elapsed_seconds"] for row in rows if row["status"] == "error"],
        },
        "human_review": {
            "reviewed": 0,
            "successful": counts["done"],
            "coverage": 0.0 if counts["done"] else None,
            "axis_distributions": None,
            "acceptable_fraction": None,
            "hallucination_counts": None,
        },
    }


def run_evaluation(
    manifest_path: Path,
    image_root: Path,
    output: Path,
    *,
    cache_dir: Path | None = None,
    engine_factory=CaptionEngine,
    progress=lambda _message: None,
) -> dict:
    manifest, raw = load_manifest(manifest_path)
    metadata = environment()
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "manifest.json", raw)
    report = {
        "schema_version": 1,
        "protocol": PROTOCOL,
        "run_id": output.name,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "environment": metadata,
        "generation": {
            "model": MODEL_ID,
            "revision": MODEL_REVISION,
            "device": "cpu",
            "length": "Standard",
            "max_new_tokens": 35,
            "num_beams": 3,
            "do_sample": False,
            "no_repeat_ngram_size": 3,
            "prompt": None,
        },
        "started_at": utc_now(),
        "ended_at": None,
        "state": "running",
        "baseline_complete": False,
        "preparation": {"status": "not_processed", "elapsed_seconds": None, "error": None},
        "warmup": {"status": "not_processed", "elapsed_seconds": None, "error": None},
        "test_wall_seconds": None,
        "network_attempts": 0,
        "results": [
            {
                "id": row["id"],
                "status": "not_processed",
                "generated_caption": None,
                "elapsed_seconds": None,
                "error": None,
                "human_review": None,
            }
            for row in manifest["images"]["test"]
        ],
    }
    report_path = output / "report.json"

    def save():
        summarize(report, manifest)
        checkpoint(report_path, report)

    save()
    attempts = []
    test_started = None
    phase = None
    phase_started = None
    current = None
    try:
        with offline_guard() as attempts:
            phase = report["preparation"]
            phase_started = time.perf_counter()
            engine = engine_factory(offline=True, cache_dir=cache_dir or default_cache())
            engine.prepare()
            phase.update(status="done", elapsed_seconds=time.perf_counter() - phase_started)
            progress("Model prepared; warming up on one dev image.")
            phase = report["warmup"]
            phase_started = time.perf_counter()
            caption_row(manifest["images"]["dev"][0], image_root, engine)
            phase.update(status="done", elapsed_seconds=time.perf_counter() - phase_started)
            phase = None
            save()
            test_started = time.perf_counter()
            for source, current in zip(manifest["images"]["test"], report["results"], strict=True):
                phase_started = time.perf_counter()
                fatal = False
                try:
                    caption, elapsed = caption_row(source, image_root, engine)
                    current.update(
                        status="done", generated_caption=caption, elapsed_seconds=elapsed
                    )
                except Exception as exc:
                    current.update(status="error", error=error_category(exc))
                    fatal = isinstance(exc, ModelUnavailableError) or bool(attempts)
                finally:
                    if current["status"] != "done":
                        current["elapsed_seconds"] = time.perf_counter() - phase_started
                report["network_attempts"] = len(attempts)
                save()
                processed = sum(r["status"] != "not_processed" for r in report["results"])
                progress(f"Processed {processed}/50.")
                if fatal:
                    report["state"] = "aborted"
                    break
                current = None
            else:
                report["state"] = "completed"
    except KeyboardInterrupt:
        report["state"] = "interrupted"
        if phase is not None:
            phase.update(status="interrupted", elapsed_seconds=time.perf_counter() - phase_started)
        if current is not None and current["status"] == "not_processed":
            current["error"] = "interrupted"
    except Exception as exc:
        report["state"] = "aborted"
        if phase is not None:
            phase.update(
                status="error",
                error=error_category(exc),
                elapsed_seconds=time.perf_counter() - phase_started,
            )
        else:
            report["runner_error"] = "evaluation_failed"
    finally:
        report["network_attempts"] = len(attempts)
        report["ended_at"] = utc_now()
        if test_started is not None:
            report["test_wall_seconds"] = time.perf_counter() - test_started
        report["baseline_complete"] = report["state"] == "completed" and not attempts
        save()
    by_id = {row["id"]: row for row in report["results"]}
    review = {
        "protocol": PROTOCOL,
        "manifest_sha256": report["manifest_sha256"],
        "instructions": "Human ratings only. See docs/EVALUATION.md. Save reviews separately.",
        "rows": [
            {
                "id": name,
                "generated_caption": by_id[name]["generated_caption"],
                "reviewer": None,
                "reviewed_at": None,
                "rubric": PROTOCOL,
                "faithfulness": None,
                "coverage": None,
                "fluency": None,
                "hallucination": None,
                "note": None,
            }
            for name in rank(
                [row["id"] for row in report["results"] if row["status"] == "done"], "review"
            )
        ],
    }
    write_new(output / "review-template.json", json_bytes(review))
    return report


def private_destination(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(PRIVATE_ROOT.resolve()) or resolved == PRIVATE_ROOT.resolve():
        raise EvaluationError("Choose an output inside .local/evaluation/v1/.")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze", help="Freeze local selection before generation")
    freeze.add_argument("--text-root", required=True, type=Path)
    freeze.add_argument("--image-root", required=True, type=Path)
    freeze.add_argument("--smoke-report", action="append", default=[], type=Path)
    freeze.add_argument("--exclusions", type=Path, help="Private JSON object: image ID to reason")
    freeze.add_argument("--output", required=True, type=Path)
    run = commands.add_parser("run", help="Evaluate a frozen manifest offline")
    run.add_argument("--manifest", required=True, type=Path)
    run.add_argument("--image-root", required=True, type=Path)
    run.add_argument("--cache-dir", type=Path)
    run.add_argument("--output", required=True, type=Path, help="New private run directory")
    args = parser.parse_args(argv)
    try:
        output = private_destination(args.output)
        if args.command == "freeze":
            if output.exists():
                raise EvaluationError("Manifest already exists; use a new output.")
            exclusions = exclusions_from_reports(args.smoke_report)
            if args.exclusions:
                extra = json.loads(args.exclusions.read_text(encoding="utf-8-sig"))
                if not isinstance(extra, dict):
                    raise EvaluationError("Exclusions must be a JSON object.")
                exclusions.update(extra)
            manifest = build_manifest(args.text_root, args.image_root, exclusions)
            output.parent.mkdir(parents=True, exist_ok=True)
            write_new(output, json_bytes(manifest))
            print("Frozen 50 test and 10 dev images; source content remains local.")
            return 0
        report = run_evaluation(
            args.manifest,
            args.image_root,
            output,
            cache_dir=args.cache_dir,
            progress=lambda message: print(message, flush=True),
        )
        print(
            json.dumps(
                {
                    "state": report["state"],
                    "baseline_complete": report["baseline_complete"],
                    "summary": report["summary"],
                    "network_attempts": report["network_attempts"],
                },
                indent=2,
            )
        )
        if report["state"] == "interrupted":
            return 130
        return 0 if report["baseline_complete"] and not report["summary"]["counts"]["error"] else 1
    except (OSError, ValueError, TypeError):
        print(
            "Evaluation input/output failed. Check paths, JSON, and the protocol; "
            "use a new private output.",
            file=sys.stderr,
        )
        return 2
    except KeyboardInterrupt:
        print("Evaluation cancelled before a run could be recorded.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
