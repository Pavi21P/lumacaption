# LumaCaption status

Updated: 2026-11-09 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC08U - university setup verified; build pending by user choice
Next action: recheck RAM before build/model work; reuse installed setup (docs/NEW-PC.md).
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
Resource preference: lightweight work; no automatic build/model retries.
GitHub Actions: disabled at user request; do not re-enable unasked.

## Verified baseline

- University Windows 11 Enterprise x64, build 26200; 15.69 GiB installed RAM.
- User confirmed permitted setup; Git 2.56.0.windows.4 and official Python 3.11.9 x64 installed.
- Fresh .venv has locked runtime/build packages; pip check and build -CheckOnly passed.
- 310 source tests passed in 15.66s; Ruff lint/format passed (42 files).
- Source CLI --help passed. --diagnose passed Python/Tk/imports, exited 1 for absent model cache.
- Source/locks unchanged from 9741365; no model download, inference, or executable build.
- Three user photos are ignored under .local/Test Images; local logs/tools are also ignored.
- Reuse this .venv and .local/tools; see docs/NEW-PC.md for exact launch paths.

## Remaining conditions

After user cleanup: 5.17 GiB available RAM, 73.21 GiB free C: space.
Proposed heavy-work limits: start at >=8 GiB available RAM; stop below 2 GiB RAM or 15 GiB disk.
These are conservative session limits, not measured requirements or a safety guarantee.
User chose to save setup and leave build pending. Work sequentially; leave other apps alone.
Home LC08R failed checksum finalization (OSError 22); its bundle remains unverified.
The reported home-PC crash cause remains unknown; see docs/VALIDATION.md.
Packaged desktop/CLI, real captions, offline restart, and spaced-path runtime checks are unperformed here.
Manual keyboard/edit/CSV/JSON/session/cancel-preserves-edits checks remain pending.
Source synthetic tests do not establish packaged behavior or manual acceptance.
LC09 clean-host verification, LC11 screen-reader acceptance, and real GPU testing remain unverified.
Screen-reader testing stays deferred. Original verified LC08 executable predates LC10/LC12.
