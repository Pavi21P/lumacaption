# LumaCaption status

Updated: 2026-11-04 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC02 - desktop Save/Open sessions complete
Next task: LC03 - local autosave and recovery
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.

## Verified baseline

- 101 tests passed, including 22 desktop tests; Ruff lint/format passed.
- Save/Open restores queue, edits, settings, and provenance without starting inference.
- Save/discard/cancel prompts protect unsaved work; export does not save a session.
- Missing-image warnings preserve stored rows/captions and exclude them from generation.
- Real cached-model smoke passed: zero network attempts, unchanged source files,
  matching desktop-worker captions, and CSV/JSON exports; total 28.904 seconds.
- Hosted CI status is checked after each push; see GitHub for the latest checkpoint.
- Reuse .venv and .cache/models; .local reports remain ignored.

## LC03 starting points

- Storage contract/API: docs/SESSIONS.md and src/lumacaption/sessions.py.
- Desktop state/dialogs and dirty tracking: src/lumacaption/desktop.py.
- Tests: tests/test_desktop.py and tests/test_sessions.py.
- Add debounced autosave outside Git and offer recovery at startup.
- Capture Tk state on the UI thread; do not race generation/results or manual saves.
- Recovered jobs must remain pending until the user starts generation.
- Preserve existing save/discard/cancel and failed-import behavior.
- Relinking missing paths remains LC04.

## Outstanding evidence

Fresh-machine installation, manual visual/accessibility acceptance, comparative benchmarks,
and GPU execution remain unverified. These do not block LC03.
