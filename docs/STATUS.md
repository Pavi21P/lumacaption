# LumaCaption status

Updated: 2026-11-05 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC05 - model and startup diagnostics complete
Next task: LC06 - reproducible evaluation protocol
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
GitHub Actions: disabled at user request; local checks required; do not re-enable unasked.

## Verified baseline

- 188 tests passed (61 desktop, 8 recovery, 40 diagnostics, 79 existing other tests).
- Ruff lint/format passed for 18 Python files.
- --diagnose checks Python/Tk/runtime imports/versions/pinned cache with redacted output.
- Real diagnostics passed here without loading weights; file presence is not inference proof.
- Shared model/cache settings moved to dependency-free config.py; engine reexports preserved.
- Real offline regression passed: zero network attempts, unchanged photos,
  matching desktop-worker captions and CSV/JSON exports; total 30.658 seconds.
- Reuse .venv and .cache/models; .local reports remain ignored.

## LC06 starting points

- Define a small held-out evaluation split, selection method, metrics, and review rubric.
- Verify dataset terms and document provenance before selecting evaluation inputs.
- Keep source photos, references, and generated reports outside Git.
- Avoid claims about comparative quality until LC07 runs the documented protocol.
- Consult docs/VALIDATION.md for existing smoke-test limits; these are not benchmark data.
- Protocol/documentation only; evaluation tooling and measured baseline belong to LC07.
- Preserve the original tutorial data outside the LumaCaption repository.

## Outstanding evidence

Clean-machine installation, packaged runtime, manual visual/accessibility acceptance,
comparative benchmarks, and GPU execution remain unverified.
