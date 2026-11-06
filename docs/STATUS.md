# LumaCaption status

Updated: 2026-11-06 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC11 - partial feedback recorded; acceptance blocked
Next action: LC12 - optional device selection with CPU fallback
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
GitHub Actions: disabled at user request; local checks required; do not re-enable unasked.

## Verified baseline

- 280 tests passed; Ruff lint/format passed for 25 Python files.
- Keyboard controls/help: docs/KEYBOARD.md; Ctrl+I/O/S/E, Ctrl+Enter, Esc, F6, F1.
- Ten new Windows Tk tests cover real key events, traversal, focus, and safeguards.
- All interactive controls remain visible at the 960x680 minimum client size.
- Queue selection/focus follow added or opened images; editor Tab leaves without text.
- Disabled shortcuts and modal grabs cannot bypass dialog/batch safeguards.
- Source app has LC10 changes; LC08 binaries have not been rebuilt.
- LC08 portable build and offline smoke evidence remain specific to that checkpoint.
- LC07 baseline: 50/50 captions; BLEU-1 57.60, BLEU-4 21.46, ROUGE-L 47.21.
- Reuse .venv and .cache/models; private data/reports/builds stay ignored.

## Blockers and next task

LC09 is blocked: no clean Windows host/VM was supplied; no Sandbox/VM tooling was
found on this Windows 10 Home build 19045 development host. No clean-machine pass.
LC11: user reports visual/captioning success, but used no screen reader and did not
try final edit/export/session checks. Screen-reader testing deferred at user request.
Private evidence: .local/lc11-review-2026-11-06/; no accessibility acceptance claim.
LC12 is next: inspect available hardware, keep CPU default, add explicit device
selection/fallback and tests. Do not replace the working CPU dependency setup.
Only measure GPU speed/memory on supported hardware; document unavailable evidence.
Three phases remain: blocked LC09 and LC11, next LC12.
