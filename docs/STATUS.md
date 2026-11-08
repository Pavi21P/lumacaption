# LumaCaption status

Updated: 2026-11-07 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC08D - checksum failure diagnostics tested
Next action: arrange a separate Windows build host or agree on a resource plan
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
Resource preference: lightweight work; no automatic build/model retries.
GitHub Actions: disabled at user request; do not re-enable unasked.

## Verified baseline

- LC12 source: 03bda3f; 300 tests and Ruff passed before the packaging attempt.
- CPU/CUDA selection, CPU fallback, keyboard controls, sessions, and recovery exist.
- LC12 real offline CPU/fallback captions matched prior output; zero network attempts.
- LC08D build helper names checksum failures; 304 tests and Ruff passed.
- Application code/dependencies unchanged; no build/model work performed.
- Original verified LC08 executable remains older than LC10/LC12.
- Reuse .venv and .cache/models; private data/reports/builds stay ignored.

## Remaining conditions

LC08R compilation/collection completed; checksum finalization failed with OSError
[Errno 22] Invalid argument in hashlib.file_digest. No runtime pass or sealed manifest.
Unverified output: dist/LumaCaption-0.1.0-win64-lc12/LumaCaption/; do not distribute.
Last resource snapshot after user cleanup: 4.19 GiB free build-drive space, above the 3 GiB disk minimum;
2.85 GiB RAM available. Snapshots do not establish safe build capacity.
A recent Kernel-Power event records BugcheckCode 59; exact crash cause is unknown.
See docs/VALIDATION.md for resource/event evidence and LC08D diagnostic tests.
No automatic packaging retry: use a separate host or agree on a resource plan first.
LC09 still needs a clean Windows host/VM.
LC11 screen-reader testing was deferred; final manual persistence checks were not tried.
Positive visual/captioning feedback is not accessibility acceptance.
Real GPU execution/performance remain unverified.
