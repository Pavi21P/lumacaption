"""Frozen dispatch and build safety without generating binaries in unit tests."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from lumacaption import diagnostics, packaged


@pytest.fixture
def builder():
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_windows.py"
    spec = importlib.util.spec_from_file_location("build_windows", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_probe_uses_console_sibling_not_python_m(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\folder with spaces\LumaCaption.exe")
    expected = {name: True for name in ("Tk", *diagnostics.DEPENDENCIES)}

    def run(command, **kwargs):
        assert command == [r"C:\folder with spaces\LumaCaption-CLI.exe", "--_runtime-probe"]
        assert kwargs["timeout"] == 45
        return SimpleNamespace(returncode=0, stdout=json.dumps(expected), stderr="")

    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    assert diagnostics.check_runtime() == expected


def test_frozen_cache_failure_points_to_executable(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    result = diagnostics.check_cache(tmp_path)
    assert not result.ok
    assert "LumaCaption-CLI.exe --download-model" in result.detail
    assert "Launch-LumaCaption.cmd" not in result.detail


def test_packaged_probe_dispatch_does_not_relaunch_cli(monkeypatch, capsys):
    monkeypatch.setattr(diagnostics, "_probe_runtime", lambda: {"Tk": True})
    monkeypatch.setitem(sys.modules, "lumacaption.cli", None)
    assert packaged.main(["--_runtime-probe"]) == 0
    assert json.loads(capsys.readouterr().out) == {"Tk": True}


def test_packaged_cli_preserves_arguments_and_exit_status(monkeypatch):
    from lumacaption import cli

    seen = []
    monkeypatch.setattr(cli, "main", lambda args: seen.append(args) or 7)
    assert packaged.main(["--offline", "image with space.jpg"]) == 7
    assert seen == [["--offline", "image with space.jpg"]]


@pytest.mark.parametrize("fails", [False, True])
def test_packaged_smoke_uses_bundled_script_and_restores_argv(monkeypatch, tmp_path, fails):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    original = sys.argv

    def run(path, run_name):
        assert path == str(tmp_path / "verify_offline.py")
        assert run_name == "__main__"
        assert sys.argv[1:] == ["photo.jpg", "--desktop", "--report", "report.json"]
        if fails:
            raise RuntimeError("test")

    monkeypatch.setattr(packaged.runpy, "run_path", run)
    args = ["--verify-package", "photo.jpg", "--desktop", "--report", "report.json"]
    if fails:
        with pytest.raises(RuntimeError):
            packaged.main(args)
    else:
        assert packaged.main(args) == 0
    assert sys.argv is original


@pytest.mark.parametrize("name", ["../build", r"a\b", "C:build", "x.", "x ", "", "/tmp", ".."])
def test_build_rejects_path_names(builder, name):
    with pytest.raises(ValueError):
        builder.validate_name(name)


def test_build_refuses_existing_outputs_without_removing_them(builder, monkeypatch, tmp_path):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "check_environment", lambda: {})
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.1.0"\n')
    existing = tmp_path / "dist" / "existing"
    existing.mkdir(parents=True)
    marker = existing / "keep.txt"
    marker.write_text("user data")
    with pytest.raises(ValueError, match="already exists"):
        builder.build("existing")
    assert marker.read_text() == "user data"


def test_build_rejects_dependency_drift(builder, monkeypatch):
    monkeypatch.setattr(builder.platform, "python_version", lambda: "3.11.9")
    monkeypatch.setattr(builder.metadata, "version", lambda _: "0.0.0")
    with pytest.raises(ValueError, match="differs from the lock"):
        builder.check_environment()


def test_build_metadata_omits_private_editable_url(builder, monkeypatch, tmp_path):
    distribution = SimpleNamespace(
        version="0.1.0",
        read_text=lambda name: {
            "METADATA": "Name: lumacaption\nVersion: 0.1.0\n",
            "WHEEL": "Wheel-Version: 1.0\n",
            "direct_url.json": '{"url":"file:///private/source"}',
        }.get(name),
    )
    monkeypatch.setattr(builder.metadata, "distribution", lambda _: distribution)
    builder.stage_metadata(tmp_path, "0.1.0")
    files = list((tmp_path / "lumacaption-0.1.0.dist-info").iterdir())
    assert {p.name for p in files} == {"METADATA", "WHEEL"}
    assert all("private" not in p.read_text() for p in files)


def test_only_generated_installation_urls_are_removed(builder, monkeypatch, tmp_path):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    bundle = tmp_path / "dist" / "package"
    meta = bundle / "_internal" / "package.dist-info"
    meta.mkdir(parents=True)
    private = meta / "direct_url.json"
    private.write_text('{"url":"file:///private/source"}')
    notice = meta / "LICENSE"
    notice.write_text("Retain me")
    assert builder.sanitize_metadata(bundle) == 1
    assert not private.exists() and notice.read_text() == "Retain me"
    with pytest.raises(ValueError, match="inside"):
        builder.sanitize_metadata(tmp_path)


def test_build_digest_matches_known_sha256(builder, tmp_path):
    path = tmp_path / "tiny.txt"
    path.write_bytes(b"abc")
    assert builder.digest(path) == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


@pytest.mark.parametrize("stage", ["open", "read"])
def test_hash_failure_identifies_artifact_without_private_root(
    builder, monkeypatch, tmp_path, stage
):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    path = tmp_path / "dist" / "folder with spaces" / "broken.dll"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"tiny fixture")
    failure = OSError(22, "Invalid argument", str(path))

    def fail(*args, **kwargs):
        raise failure

    if stage == "open":
        monkeypatch.setattr(Path, "open", fail)
    else:
        monkeypatch.setattr(builder.hashlib, "file_digest", fail)
    with pytest.raises(ValueError) as caught:
        builder.digest(path)
    assert "dist/folder with spaces/broken.dll" in str(caught.value)
    assert "OS error 22" in str(caught.value)
    assert "unverified" in str(caught.value)
    assert str(tmp_path) not in str(caught.value)
    assert caught.value.__cause__ is failure


def test_hash_failure_exits_without_manifest_or_retry(builder, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    output = tmp_path / "dist" / "fixture"
    bundle = output / "LumaCaption"
    bundle.mkdir(parents=True)
    stage = tmp_path / "stage"
    (stage / "licenses").mkdir(parents=True)
    for name in ("LumaCaption.exe", "LumaCaption-CLI.exe"):
        (bundle / name).write_bytes(b"fixture, not an executable")
    (tmp_path / "packaging").mkdir()
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "packaging/README-Windows.md"):
        (tmp_path / name).write_text("fixture")
    failed = bundle / "LumaCaption.exe"
    original_digest = builder.hashlib.file_digest
    attempts = []

    def read(handle, algorithm):
        if Path(handle.name) == failed:
            attempts.append(handle.name)
            raise OSError(22, "Invalid argument", handle.name)
        return original_digest(handle, algorithm)

    monkeypatch.setattr(builder.hashlib, "file_digest", read)
    monkeypatch.setattr(builder, "build", lambda name: builder.finish_bundle(output, stage, {}, {}))
    monkeypatch.setattr(sys, "argv", ["build_windows.py", "--name", "fixture"])
    assert builder.main() == 1
    error = capsys.readouterr().err
    assert "dist/fixture/LumaCaption/LumaCaption.exe" in error
    assert "OS error 22" in error and "unverified" in error
    assert str(tmp_path) not in error
    assert len(attempts) == 1
    assert not (bundle / "build-info.json").exists()
    assert failed.read_bytes() == b"fixture, not an executable"


@pytest.mark.parametrize("problem", [None, "disk", "output", "work", "dependency", "name"])
def test_check_only_never_builds_or_writes(builder, monkeypatch, tmp_path, capsys, problem):
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion="0.1.0"\n')
    monkeypatch.setattr(builder, "check_environment", lambda: {"fake-package": "1.0"})
    monkeypatch.setattr(
        builder.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(free=(3 * 1024**3 - 1 if problem == "disk" else 3 * 1024**3)),
    )
    if problem in ("output", "work"):
        parent = "dist" if problem == "output" else "build"
        (tmp_path / parent / "check fixture").mkdir(parents=True)
    if problem == "dependency":

        def missing():
            raise builder.metadata.PackageNotFoundError("fake-package")

        monkeypatch.setattr(builder, "check_environment", missing)

    def forbidden(*args, **kwargs):
        pytest.fail("Check-only must not build, install, stage, or finalize")

    for name in ("build", "collect_notices", "stage_metadata", "finish_bundle"):
        monkeypatch.setattr(builder, name, forbidden)
    monkeypatch.setattr(builder.subprocess, "run", forbidden)
    name = "../escape" if problem == "name" else "check fixture"
    monkeypatch.setattr(sys, "argv", ["build_windows.py", "--name", name, "--check-only"])
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert builder.main() == (1 if problem else 0)
    captured = capsys.readouterr()
    if problem:
        assert "Build check failed" in captured.err
        assert "checks passed" not in captured.out
    else:
        assert "no build started" in captured.out
        assert "RAM capacity" in captured.out
    assert {p.relative_to(tmp_path) for p in tmp_path.rglob("*")} == before
