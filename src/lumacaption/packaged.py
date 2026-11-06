"""Frozen launcher and developer verification dispatch; source CLI stays unchanged."""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    # Windowed PyInstaller builds have no console streams; libraries may still log.
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--_runtime-probe"]:
        from .diagnostics import _probe_runtime

        print(json.dumps(_probe_runtime()), flush=True)
        return 0
    if args and args[0] == "--verify-package":
        base = (
            Path(sys._MEIPASS)
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[2]
        )
        script = (
            base / "verify_offline.py"
            if getattr(sys, "frozen", False)
            else base / "scripts/verify_offline.py"
        )
        original = sys.argv
        try:
            sys.argv = [str(script), *args[1:]]
            runpy.run_path(str(script), run_name="__main__")
        finally:
            sys.argv = original
        return 0
    from .cli import main as cli_main

    return cli_main(args)
