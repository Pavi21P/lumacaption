# LumaCaption status

Updated: 2026-11-07 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC08R - failed finalization and host crash report recorded
Next action: no automatic build retry; use tested source baseline
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
Resource preference: lightweight work; no heavy build/model/test runs this session.
GitHub Actions: disabled at user request; do not re-enable unasked.

## Verified baseline

- LC12 source: 03bda3f; 300 tests and Ruff passed before the packaging attempt.
- CPU/CUDA selection, CPU fallback, keyboard controls, sessions, and recovery exist.
- LC12 real offline CPU/fallback captions matched prior output; zero network attempts.
- No source code or dependency changes in this packaging/documentation checkpoint.
- Original verified LC08 executable remains older than LC10/LC12.
- Reuse .venv and .cache/models; private data/reports/builds stay ignored.

## Failed refresh and remaining conditions

LC08R compilation/collection completed; checksum finalization failed with OSError
[Errno 22] Invalid argument in hashlib.file_digest. No runtime pass or sealed manifest.
Unverified output: dist/LumaCaption-0.1.0-win64-lc12/LumaCaption/.
Evidence: build/LumaCaption-0.1.0-win64-lc12/build.log and .local/verify-lc08r.py.
Low memory and shell-start failures occurred; user reported a blue screen.
Exact crash cause is unconfirmed. Heavy build/model work stopped; user requested push.
Do not automatically retry packaging on continuation. Investigate resources or use
a separate build host before resuming. Do not distribute the unverified folder.
LC09 still needs a clean Windows host/VM.
LC11 screen-reader testing was deferred by the user; final manual persistence checks
were not tried. Positive visual/captioning feedback is not accessibility acceptance.
Real GPU execution/performance remain unverified.
