# LumaCaption status

Updated: 2026-11-05 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC03 - local autosave and startup recovery complete
Next task: LC04 - relink moved or missing images
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.

## Verified baseline

- 129 tests passed (42 desktop, 8 recovery-store, 79 existing other tests).
- Ruff lint/format passed for 15 Python files.
- One-second debounced recovery plus immediate pre-generation pending snapshot.
- Startup recovery restores edits/settings; generation stays stopped.
- Atomic writes, process-exit recovery, exclusive ownership, and cleanup verified.
- Real cached-model smoke passed: zero network attempts, unchanged source files,
  matching desktop-worker captions, and CSV/JSON exports; total 48.959 seconds.
- Hosted CI is checked once after push; see GitHub for current status.
- Reuse .venv and .cache/models; .local reports remain ignored.

## LC04 starting points

- Desktop missing-image display: image_errors, _apply_session, _refresh_row.
- Add a relink action without losing caption edits or model provenance.
- Validate the replacement image before changing the existing row/path/tree ID.
- Handle duplicate paths, cancellation, unavailable files, and invalid images.
- Use _mark_dirty() after successful relinks so autosave captures the change.
- Keep missing-path recovery/export behavior covered by desktop tests.
- RecoveryStore in recovery.py owns the local store; tests use temporary directories.
- Desktop tests share one Tcl runtime with a fresh window per test.

## Outstanding evidence

Fresh-machine installation, manual visual/accessibility acceptance, comparative benchmarks,
and GPU execution remain unverified. These do not block LC04.
