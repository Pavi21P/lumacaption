"""Bounded local diagnostics; no weights are loaded and raw errors stay private."""

from __future__ import annotations

import importlib
import importlib.metadata as metadata
import json
import os
import socket
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import MODEL_ID, MODEL_REVISION, default_cache

DEPENDENCIES = {
    "Pillow": "PIL.Image",
    "torch": "torch",
    "transformers": "transformers",
    "truststore": "truststore",
}
CACHE_FILES = (
    "config.json",
    "preprocessor_config.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
    "pytorch_model.bin",
)
SETUP_HINT = "Run Setup-Windows.ps1 with supported 64-bit Python."
PROBE_TIMEOUT = 45


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def check_python() -> Check:
    supported = (3, 11) <= sys.version_info[:2] < (3, 14) and struct.calcsize("P") == 8
    version = ".".join(str(part) for part in sys.version_info[:3])
    bits = struct.calcsize("P") * 8
    return Check(
        "Python",
        supported,
        f"{version}, {bits}-bit" if supported else "Use 64-bit Python 3.11-3.13.",
    )


def dependency_versions() -> dict[str, Check]:
    try:
        from packaging.requirements import Requirement
        from packaging.version import Version

        requirements = {}
        for text in metadata.requires("lumacaption") or []:
            requirement = Requirement(text)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                requirements[requirement.name.lower()] = requirement.specifier
    except Exception:
        return {
            name: Check(name, False, "Dependency metadata unavailable. " + SETUP_HINT)
            for name in DEPENDENCIES
        }
    checks = {}
    for name in DEPENDENCIES:
        try:
            version = Version(metadata.version(name))
            supported = version in requirements[name.lower()]
            # PEP 440 public version is numeric/standardized; do not print local
            # build identifiers, metadata URLs, or exception text.
            detail = (
                f"{version.public}; version supported"
                if supported
                else ("Installed version is outside the supported range. " + SETUP_HINT)
            )
            checks[name] = Check(name, supported, detail)
        except Exception:
            checks[name] = Check(name, False, "Missing or unreadable dependency. " + SETUP_HINT)
    return checks


def _block_network() -> None:
    def denied(*args, **kwargs):
        raise OSError("Network disabled during diagnostics.")

    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    socket.getaddrinfo = denied
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def _probe_runtime() -> dict[str, bool]:
    """Runs only in a child process; never echo module errors or startup noise."""
    _block_network()
    results = {}
    root = None
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        results["Tk"] = True
    except Exception:
        results["Tk"] = False
    finally:
        if root is not None:
            root.destroy()
    for name, module in DEPENDENCIES.items():
        try:
            imported = importlib.import_module(module)
            if name == "transformers":
                # Resolve the lazy BLIP classes to catch missing transitive
                # dependencies, without calling from_pretrained.
                _ = imported.BlipProcessor, imported.BlipForConditionalGeneration
            results[name] = True
        except Exception:
            results[name] = False
    return results


def check_runtime() -> dict[str, bool] | None:
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        completed = subprocess.run(
            [sys.executable, "-m", "lumacaption.diagnostics", "--probe"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROBE_TIMEOUT,
            creationflags=flags,
        )
        if completed.returncode != 0:
            return None
        # Only consume the final structured line; never relay captured stdout/stderr.
        report = json.loads(completed.stdout.splitlines()[-1])
        if not isinstance(report, dict) or set(report) != {"Tk", *DEPENDENCIES}:
            return None
        if any(type(value) is not bool for value in report.values()):
            return None
        return report
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def check_cache(directory: Path | None = None) -> Check:
    try:
        cache = default_cache() if directory is None else directory
        snapshot = cache / ("models--" + MODEL_ID.replace("/", "--")) / "snapshots" / MODEL_REVISION
        for name in CACHE_FILES:
            with (snapshot / name).open("rb") as handle:
                if name.endswith(".json"):
                    data = handle.read(1024 * 1024 + 1)
                    if len(data) > 1024 * 1024 or not isinstance(json.loads(data), dict):
                        raise ValueError("Invalid metadata")
                elif not handle.read(1):
                    raise ValueError("Empty file")
        return Check("Model cache", True, "Expected pinned-revision files are readable.")
    except (OSError, ValueError, RecursionError):
        return Check(
            "Model cache",
            False,
            "Missing, unreadable, or invalid cached files. "
            "Run Launch-LumaCaption.cmd --download-model when online; "
            "use the same LUMACAPTION_CACHE setting for both commands.",
        )


def collect_checks() -> list[Check]:
    checks = [check_python()]
    versions = dependency_versions()
    runtime = check_runtime()
    checks.append(
        Check(
            "Tk",
            bool(runtime and runtime["Tk"]),
            "Window initialization passed."
            if runtime and runtime["Tk"]
            else (
                "Could not initialize Tk. Install Tcl/Tk with Python "
                "and run in a Windows desktop session."
            ),
        )
    )
    if runtime is None:
        checks.append(
            Check(
                "Runtime probe",
                False,
                "Probe failed or exceeded 45 seconds. Close busy apps and rerun; "
                "if it persists, rerun Setup-Windows.ps1.",
            )
        )
    for name in DEPENDENCIES:
        check = versions[name]
        if not check.ok:
            checks.append(check)
        elif runtime is None:
            checks.append(Check(name, False, "Import was not verified. " + SETUP_HINT))
        elif not runtime[name]:
            checks.append(Check(name, False, "Import failed. " + SETUP_HINT))
        else:
            checks.append(Check(name, True, check.detail + "; import passed"))
    checks.append(check_cache())
    return checks


def run_diagnostics() -> int:
    checks = collect_checks()
    print("LumaCaption diagnostics - local checks only")
    for check in checks:
        print(f"[{'OK' if check.ok else 'FAIL'}] {check.label}: {check.detail}")
    print("No downloads or model loading. File checks do not prove weight integrity or inference.")
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--probe"]:
        print(json.dumps(_probe_runtime()), flush=True)
    else:
        raise SystemExit(run_diagnostics())
