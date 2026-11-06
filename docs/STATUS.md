# LumaCaption status

Updated: 2026-11-05 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC04 - relink moved or missing images complete
Next task: LC05 - model and startup diagnostics
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.

## Verified baseline

- 148 tests passed (61 desktop, 8 recovery-store, 79 existing other tests).
- Ruff lint/format passed for 15 Python files.
- Relink validates images before changing paths and preserves caption/provenance/status.
- Cancel, invalid input, duplicates/aliases, busy state, and recovery/save integration tested.
- Selecting moved/restored images refreshes missing status; relink never starts generation.
- Real cached-model smoke passed: zero network attempts, unchanged source files,
  matching desktop-worker captions, and CSV/JSON exports; total 44.653 seconds.
- Hosted CI is checked once after push; see GitHub for current status.
- Reuse .venv and .cache/models; .local reports remain ignored.

## LC05 starting points

- CLI entry/options: src/lumacaption/cli.py; existing CLI tests: tests/test_core.py.
- Model/cache readiness: src/lumacaption/engine.py and Setup-Windows.ps1.
- Add a concise diagnostic command for Python/Tk/dependencies/cache readiness.
- Diagnostics must not download weights or expose private paths/tokens.
- Report actionable failures and distinguish cached files from proven model readiness.
- Keep the working CPU setup and all existing caption/session/recovery behavior.
- Use synthetic or mocked missing-dependency/cache cases; reuse the installed environment.
- Desktop tests share one Tcl runtime with a fresh window per test.

## Outstanding evidence

Fresh-machine installation, manual visual/accessibility acceptance, comparative benchmarks,
and GPU execution remain unverified. These do not block LC05.
