# LumaCaption status

Updated: 2026-11-06 (America/Chicago)
Repository: https://github.com/Pavi21P/lumacaption
Branch: main
Current checkpoint: LC12 - optional device selection and CPU fallback complete
Next action: resume blocked validation when its prerequisites are available
Task source: docs/PLAN.md
Session rule: one ready task per "continue", verify, commit/push, stop.
Scheduling: user-triggered; no unattended daily job.
GitHub Actions: disabled at user request; local checks required; do not re-enable unasked.

## Verified baseline

- 300 tests passed; Ruff lint/format passed for 26 Python files.
- Desktop Compute device and CLI --device cpu/cuda; CPU stays the default.
- CUDA availability/placement failures fall back to CPU with an actual-device report.
- CUDA out-of-memory retries the current image once on CPU; later images stay on CPU.
- Simulated GPU tests cover routing, tensor types, failures, retry bounds, and engine reuse.
- Real CPU and requested-CUDA fallback smokes both matched earlier source captions.
- Both: zero network attempts, unchanged inputs, real Tk worker and CSV/JSON checks.
- Private evidence: .local/offline-lc12-{cpu,cuda}-2026-11-06.json.
- Hardware: Intel HD Graphics 620; torch 2.15.0+cpu; zero available CUDA devices.
- Real GPU execution/speed/memory remain unverified; dependencies were not replaced.
- Session format and fixed CPU evaluation protocol remain unchanged.
- Source includes LC10/LC12; the LC08 executable needs a new named build for these.
- Reuse .venv and .cache/models; private data/reports/builds stay ignored.

## Remaining conditions

Two planned phases remain: LC09 and LC11, both blocked; no ready queue item remains.
LC09 needs a clean Windows host/VM. The development host is Windows 10 Home build
19045; no available Sandbox/VM tooling or separate test host was supplied.
LC11 has positive user visual/captioning feedback only. No screen reader was used;
final manual edit/export/session checks were not tried. Screen-reader testing was
deferred by the user. Do not mark accessibility passed or repeat that request unasked.
See docs/DEVICES.md for device limits and docs/KEYBOARD.md for the deferred walkthrough.
