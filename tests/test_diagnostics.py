"""Diagnostics isolate imports and never disclose raw paths or error output."""

import json
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from lumacaption import diagnostics as diag
from lumacaption.cli import main
from lumacaption.config import MODEL_ID, MODEL_REVISION

SECRET = "PRIVATE_PATH_AND_TOKEN"
RUNTIME = dict.fromkeys(["Tk", *diag.DEPENDENCIES], True)


@pytest.fixture
def cached(tmp_path):
    snapshot = tmp_path / ("models--" + MODEL_ID.replace("/", "--")) / "snapshots" / MODEL_REVISION
    snapshot.mkdir(parents=True)
    for name in diag.CACHE_FILES:
        (snapshot / name).write_bytes(b"{}" if name.endswith(".json") else b"fixture")
    return tmp_path, snapshot


@pytest.fixture
def versions(monkeypatch):
    requirements = [
        "Pillow>=11.3,<13",
        "torch>=2.6,<3",
        "transformers>=4.57.1,<5",
        "truststore>=0.10,<1",
        "pytest>=8; extra == 'dev'",
    ]
    installed = {
        "Pillow": "12.3.0",
        "torch": "2.15.0+cpu",
        "transformers": "4.57.6",
        "truststore": "0.10.5",
    }
    monkeypatch.setattr(diag.metadata, "requires", lambda name: requirements)
    monkeypatch.setattr(diag.metadata, "version", lambda name: installed[name])
    return installed


def test_cache_is_read_only_and_never_claims_model_loaded(cached):
    directory, snapshot = cached
    before = {p.name: p.read_bytes() for p in snapshot.iterdir()}
    check = diag.check_cache(directory)
    assert check.ok and "readable" in check.detail
    assert {p.name: p.read_bytes() for p in snapshot.iterdir()} == before


@pytest.mark.parametrize("kind", ["missing", "empty", "invalid_json", "wrong_type", "oversized"])
def test_incomplete_cache_is_actionable_and_redacted(cached, kind):
    directory, snapshot = cached
    target = snapshot / "config.json"
    if kind == "missing":
        target.unlink()
    elif kind == "empty":
        (snapshot / "pytorch_model.bin").write_bytes(b"")
    else:
        target.write_bytes(
            {
                "invalid_json": SECRET.encode(),
                "wrong_type": b"[]",
                "oversized": b" " * (1024 * 1024 + 1),
            }[kind]
        )
    check = diag.check_cache(directory)
    assert not check.ok and "--download-model" in check.detail
    assert str(directory) not in check.detail and SECRET not in check.detail


def test_missing_cache_directory_is_not_created(tmp_path):
    missing = tmp_path / SECRET
    assert not diag.check_cache(missing).ok
    assert not missing.exists()


def test_cache_permission_error_does_not_expose_path(cached, monkeypatch):
    directory, _ = cached

    def denied(*args, **kwargs):
        raise PermissionError(SECRET)

    monkeypatch.setattr(Path, "open", denied)
    check = diag.check_cache(directory)
    assert not check.ok and SECRET not in check.detail


def test_cache_requires_exact_pinned_revision(cached):
    directory, snapshot = cached
    snapshot.rename(snapshot.parent / "another-revision")
    assert not diag.check_cache(directory).ok


def test_versions_support_local_builds_without_disclosing_identifier(versions):
    versions["torch"] = "2.15.0+" + SECRET.lower()
    checks = diag.dependency_versions()
    assert all(check.ok for check in checks.values())
    assert "2.15.0" in checks["torch"].detail
    assert SECRET.lower() not in checks["torch"].detail


@pytest.mark.parametrize("value", ["2.5.0", "3.0.0", "2.6.0rc1", SECRET])
def test_unsupported_versions_fail(versions, value):
    versions["torch"] = value
    check = diag.dependency_versions()["torch"]
    assert not check.ok and "Setup-Windows.ps1" in check.detail
    assert SECRET not in check.detail


def test_missing_dependency_does_not_stop_other_checks(versions):
    del versions["Pillow"]
    checks = diag.dependency_versions()
    assert not checks["Pillow"].ok
    assert checks["torch"].ok


def test_missing_app_metadata_is_reported_privately(monkeypatch):
    def unavailable(name):
        raise OSError(SECRET)

    monkeypatch.setattr(diag.metadata, "requires", unavailable)
    checks = diag.dependency_versions()
    assert all(not check.ok and SECRET not in check.detail for check in checks.values())


@pytest.mark.parametrize(
    "version,bits,ok",
    [
        ((3, 11, 9), 8, True),
        ((3, 13, 0), 8, True),
        ((3, 10, 0), 8, False),
        ((3, 14, 0), 8, False),
        ((3, 11, 9), 4, False),
    ],
)
def test_python_requirements(monkeypatch, version, bits, ok):
    monkeypatch.setattr(diag.sys, "version_info", version)
    monkeypatch.setattr(diag.struct, "calcsize", lambda fmt: bits)
    assert diag.check_python().ok is ok


def test_runtime_probe_discards_startup_noise_and_stderr(monkeypatch):
    def run(command, **options):
        assert command == [sys.executable, "-m", "lumacaption.diagnostics", "--probe"]
        assert options["capture_output"] and options["timeout"] == 45
        return SimpleNamespace(
            returncode=0, stdout=SECRET + "\n" + json.dumps(RUNTIME), stderr=SECRET
        )

    monkeypatch.setattr(diag.subprocess, "run", run)
    assert diag.check_runtime() == RUNTIME


@pytest.mark.parametrize("response", ["", SECRET, "[]", '{"Tk": 1}', '{"Tk": true}'])
def test_invalid_probe_output_is_rejected(monkeypatch, response):
    monkeypatch.setattr(
        diag.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=0, stdout=response, stderr=SECRET),
    )
    assert diag.check_runtime() is None


@pytest.mark.parametrize("failure", ["timeout", "launch", "exit"])
def test_probe_failure_is_bounded_and_redacted(monkeypatch, failure):
    def run(*args, **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(SECRET, 45, output=SECRET, stderr=SECRET)
        if failure == "launch":
            raise OSError(SECRET)
        return SimpleNamespace(returncode=1, stdout=SECRET, stderr=SECRET)

    monkeypatch.setattr(diag.subprocess, "run", run)
    assert diag.check_runtime() is None


def test_network_guard_blocks_dns_and_connections(monkeypatch):
    for name in ("create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, getattr(socket, name))
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, getattr(socket.socket, name))
    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
        monkeypatch.setenv(name, "0")
    diag._block_network()
    with pytest.raises(OSError, match="disabled"):
        socket.getaddrinfo("example.com", 443)
    with pytest.raises(OSError, match="disabled"):
        socket.create_connection(("example.com", 443))
    with socket.socket() as client:
        with pytest.raises(OSError, match="disabled"):
            client.connect(("127.0.0.1", 9))


def test_import_probe_reports_failures_without_loading_model(monkeypatch):
    destroyed = []

    class Root:
        def withdraw(self):
            pass

        def update_idletasks(self):
            pass

        def destroy(self):
            destroyed.append(True)

    monkeypatch.setitem(sys.modules, "tkinter", SimpleNamespace(Tk=Root))
    monkeypatch.setattr(diag, "_block_network", lambda: None)

    def module(name):
        if name == "torch":
            raise OSError(SECRET)
        if name == "transformers":
            return SimpleNamespace(BlipProcessor=object, BlipForConditionalGeneration=object)
        return object()

    monkeypatch.setattr(diag.importlib, "import_module", module)
    report = diag._probe_runtime()
    assert report["Tk"] and not report["torch"] and report["transformers"]
    assert destroyed == [True] and SECRET not in json.dumps(report)


def test_report_exits_nonzero_for_failed_import(versions, cached, monkeypatch, capsys):
    directory, _ = cached
    monkeypatch.setattr(diag, "default_cache", lambda: directory)
    monkeypatch.setattr(diag, "check_runtime", lambda: {**RUNTIME, "torch": False})
    assert main(["--diagnose"]) == 1
    output = capsys.readouterr()
    assert "[FAIL] torch: Import failed." in output.out
    assert "do not prove weight integrity or inference" in output.out
    assert str(directory) not in output.out and not output.err


def test_successful_diagnostics_do_not_import_engine(versions, cached, monkeypatch, capsys):
    directory, _ = cached
    monkeypatch.setattr(diag, "default_cache", lambda: directory)
    monkeypatch.setattr(diag, "check_runtime", lambda: RUNTIME)
    # Even with unavailable backend imports, dispatch stays entirely in diagnostics.
    monkeypatch.setitem(sys.modules, "lumacaption.engine", None)
    monkeypatch.setitem(sys.modules, "lumacaption.batch", None)
    assert main(["--diagnose"]) == 0
    output = capsys.readouterr().out
    assert "[OK] Model cache:" in output and "No downloads or model loading" in output


@pytest.mark.parametrize(
    "extra", [["--download-model"], ["photo.jpg"], ["--output", "file.json"], ["--offline"]]
)
def test_diagnostic_mode_rejects_other_actions(extra):
    with pytest.raises(SystemExit) as exc:
        main(["--diagnose", *extra])
    assert exc.value.code == 2


def test_cli_import_works_without_image_or_ml_dependencies():
    script = """
import sys
sys.modules["PIL"] = None
sys.modules["torch"] = None
sys.modules["transformers"] = None
from lumacaption.cli import main
import lumacaption.diagnostics as diagnostics
diagnostics.run_diagnostics = lambda: 0
assert main(["--diagnose"]) == 0
assert "lumacaption.engine" not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_engine_reexports_shared_configuration():
    from lumacaption import config, engine

    assert engine.MODEL_ID == config.MODEL_ID
    assert engine.MODEL_REVISION == config.MODEL_REVISION
    assert engine.default_cache is config.default_cache
    assert engine.LENGTHS is config.LENGTHS
