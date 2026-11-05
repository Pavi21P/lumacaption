# LumaCaption status

Updated: 2026-11-04 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC01 — versioned saved-session storage complete
Next task: LC02 — Save/Open session in the desktop
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.

## Verified baseline

- 84 tests passed (48 session-storage tests plus 36 existing tests); Ruff passed.
- LC01 changed storage only; desktop Save/Open controls are not implemented.
- Prior real offline inference, setup, launcher, and exports passed at fa6a3ab.
- Hosted CI for fa6a3ab passed; check current checkpoint CI on GitHub.
- Reuse .venv and .cache/models; local reports in .local are ignored.

## LC02 starting points

- Storage contract: docs/SESSIONS.md
- API: Session, load_session, save_session in src/lumacaption/sessions.py
- UI state and dialogs: src/lumacaption/desktop.py
- Existing UI tests: tests/test_desktop.py
- Import the entire file successfully before replacing the active workspace.
- Protect unsaved edits; show missing images as errors while preserving their captions.
- Default file name: workspace.lumacaption.json (ignored by Git).
- Save/Open integration only; autosave belongs to LC03.

## Outstanding evidence

Fresh-machine installation, manual accessibility acceptance, comparative benchmarks, and GPU execution remain unverified. These do not block LC02.
