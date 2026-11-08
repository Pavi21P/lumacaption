"""Pinned Windows folder build. No cleanup, model downloads, or source-data collection."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return hashlib.file_digest(handle, "sha256").hexdigest()
    except OSError as exc:
        # Keep the failing artifact identifiable without publishing local root paths.
        display = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
        raise ValueError(
            f"Cannot hash {display!r} (OS error {exc.errno}). Build remains unverified."
        ) from exc


def pins(path: Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, version = line.split("==")
            result[name] = version
    return result


def validate_name(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,79}", name) or name.endswith((".", " ")):
        raise ValueError("Build name must be a simple folder name without path separators.")
    return name


def check_environment() -> dict[str, str]:
    if (
        sys.platform != "win32"
        or struct.calcsize("P") != 8
        or platform.python_version() != "3.11.9"
    ):
        raise ValueError("This build recipe requires Windows and CPython 3.11.9 x64.")
    expected = pins(ROOT / "requirements-lock.txt") | pins(ROOT / "requirements-build.txt")
    for name, version in expected.items():
        if metadata.version(name) != version:
            raise ValueError(f"Build dependency differs from the lock: {name}.")
    return expected


def collect_notices(stage: Path, distributions: dict[str, str]) -> list[dict]:
    """Copy installed license/notice texts, retaining their distribution-relative names."""
    notices = stage / "licenses"
    notices.mkdir()
    inventory = []
    for name, version in sorted(distributions.items()):
        dist = metadata.distribution(name)
        copied = []
        for item in dist.files or []:
            if not re.match(r"(?i)^(licen[sc]e|copying|notice|authors)([._-]|$)", item.name):
                continue
            if item.suffix.lower() in {".py", ".pyc", ".pyd", ".exe", ".dll"}:
                continue
            source = Path(dist.locate_file(item))
            if not source.is_file():
                continue
            # Metadata paths can contain ../; output names must stay inside this distribution.
            relative = Path(*[part for part in item.parts if part not in ("..", ".", "/", "\\")])
            if relative.is_absolute() or relative.drive:
                raise ValueError("Unsafe distribution license path.")
            destination = notices / name / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied.append(destination.relative_to(notices).as_posix())
        inventory.append(
            {
                "name": name,
                "version": version,
                "license_expression": dist.metadata.get("License-Expression"),
                "license_files": copied,
            }
        )
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    shutil.copyfile(python_license, notices / "Python-LICENSE.txt")
    tk_license = Path(sys.base_prefix) / "tcl" / "tk8.6" / "license.terms"
    shutil.copyfile(tk_license, notices / "Tk-license.terms")
    shutil.copyfile(ROOT / "packaging/licenses/Tcl-license.terms", notices / "Tcl-license.terms")
    (notices / "inventory.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8"
    )
    return inventory


def stage_metadata(stage: Path, version: str) -> None:
    """Retain runtime requirement metadata without an editable-install local URL."""
    dist = metadata.distribution("lumacaption")
    if dist.version != version:
        raise ValueError("Installed LumaCaption version differs from pyproject.toml.")
    folder = stage / f"lumacaption-{version}.dist-info"
    folder.mkdir()
    for name in ("METADATA", "WHEEL", "entry_points.txt", "top_level.txt"):
        content = dist.read_text(name)
        if content:
            (folder / name).write_text(content, encoding="utf-8")


def build(name: str) -> Path:
    name = validate_name(name)
    versions = check_environment()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project["version"] != "0.1.0":
        raise ValueError("Update the pinned spec metadata before building a new version.")
    output = ROOT / "dist" / name
    work = ROOT / "build" / name
    if output.exists() or work.exists():
        raise ValueError("Build output already exists; choose a new --name. Nothing was removed.")
    if shutil.disk_usage(ROOT).free < 3 * 1024**3:
        raise ValueError("At least 3 GiB free disk space is required for this build.")
    work.mkdir(parents=True)
    stage = work / "stage"
    stage.mkdir()
    collect_notices(stage, versions)
    stage_metadata(stage, project["version"])
    env = {
        **os.environ,
        "LUMACAPTION_BUILD_STAGE": str(stage),
        "PYTHONHASHSEED": "0",
        "PYTHONUTF8": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
    }
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--distpath",
        str(output),
        "--workpath",
        str(work / "pyinstaller"),
        str(ROOT / "packaging/LumaCaption.spec"),
    ]
    print(f"Building {name}; detailed output: build/{name}/build.log", flush=True)
    with (work / "build.log").open("w", encoding="utf-8") as log:
        subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    return finish_bundle(output, stage, versions, project)


def sanitize_metadata(bundle: Path) -> int:
    """Remove pip source URLs only inside this generated bundle."""
    root = bundle.resolve()
    if not root.is_relative_to((ROOT / "dist").resolve()):
        raise ValueError("Metadata cleanup must stay inside the build output.")
    paths = list(bundle.rglob("direct_url.json"))
    if any(not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("Metadata link escapes the build output.")
    for path in paths:
        path.unlink()
    return len(paths)


def finish_bundle(output: Path, stage: Path, versions: dict, project: dict) -> Path:
    bundle = output / "LumaCaption"
    if (bundle / "build-info.json").exists():
        raise ValueError("This bundle has already been finalized.")
    removed_metadata = sanitize_metadata(bundle)
    for filename in ("LumaCaption.exe", "LumaCaption-CLI.exe"):
        if not (bundle / filename).is_file():
            raise ValueError("Build did not produce both launchers.")
    shutil.copytree(stage / "licenses", bundle / "licenses", dirs_exist_ok=True)
    for source, filename in (
        (ROOT / "LICENSE", "LICENSE"),
        (ROOT / "THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        (ROOT / "packaging/README-Windows.md", "README-Windows.md"),
    ):
        shutil.copyfile(source, bundle / filename)
    files = sorted(p for p in bundle.rglob("*") if p.is_file())
    # Application weights/data must never be pulled in by the build recipe.
    forbidden = {".safetensors", ".h5", ".pkl", ".pickle"}
    for path in files:
        if path.name == "pytorch_model.bin" or path.suffix.lower() in forbidden:
            raise ValueError("Unexpected model or data artifact in executable folder.")
        if path.name == "direct_url.json":
            raise ValueError("Editable-install metadata must not ship in the executable folder.")
    hashes = {p.relative_to(bundle).as_posix(): digest(p) for p in files}
    source_paths = [
        *sorted((ROOT / "src/lumacaption").glob("*.py")),
        *sorted((ROOT / "packaging").rglob("*")),
        ROOT / "scripts/build_windows.py",
        ROOT / "scripts/verify_offline.py",
        ROOT / "requirements-lock.txt",
        ROOT / "requirements-build.txt",
    ]
    info = {
        "app": project["name"],
        "version": project["version"],
        "built_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "machine": platform.machine(),
        "distributions": versions,
        "source_sha256": {
            p.relative_to(ROOT).as_posix(): digest(p) for p in source_paths if p.is_file()
        },
        "file_sha256": hashes,
        "bytes": sum(p.stat().st_size for p in files),
        "license_inventory_entries": len(versions),
        "model_weights_included": False,
        "installation_metadata_files_removed": removed_metadata,
        "reproducibility": "Pinned recipe and checksums; bit-for-bit reproducibility not claimed.",
    }
    (bundle / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(
        f"Created dist/{output.name}/LumaCaption ({info['bytes'] / 1024**2:.1f} MiB).", flush=True
    )
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="LumaCaption-0.1.0-win64")
    args = parser.parse_args()
    try:
        build(args.name)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
