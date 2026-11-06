# LumaCaption execution plan

One row is one bounded work session, usually one day's work when the user returns daily. Dates are recorded when work happens, not assigned in advance. Read STATUS.md first and work on the next ready task only.

## Task queue

| ID | State | Deliverable | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P00 | Done | Compact plan, status handoff, agent instructions | Plan is committed and pushed; next task is explicit | — |
| LC01 | Done | Versioned saved-session storage | New sessions.py saves/loads paths, captions, edits, options, and statuses; validates JSON/version/limits; atomic saves; malformed input and round-trip tests pass. No UI work yet. | P00 |
| LC02 | Done | Save/Open session in the desktop | Native dialogs save and restore a workspace; failed import preserves the current workspace; unsaved edits are protected; UI tests pass. Missing images appear as errors without being deleted. | LC01 |
| LC03 | Done | Local autosave and recovery | Debounced autosave preserves captions/edits outside Git; reopening offers recovery; interrupted jobs restore as pending rather than starting themselves; recovery tests pass. | LC02 |
| LC04 | Done | Relink moved or missing images | User can select a replacement path for a missing image without losing its edited caption; duplicate/cancel/error cases are tested. | LC02 |
| LC05 | Done | Model and startup diagnostics | A concise diagnostic command reports Python/Tk/dependency/cache readiness without downloading weights or exposing private paths/tokens; failures give actionable messages; checks pass. | P00 |
| LC06 | Done | Reproducible evaluation protocol | Document a small held-out evaluation split, dataset terms, selection method, metrics, and human-review rubric. Keep all source images/reference captions outside Git. No quality claims yet. | P00 |
| LC07 | Done | Evaluation runner and measured baseline | A CLI evaluates the documented local split, preserves per-image failures, emits a reproducible report, and distinguishes model output from human ratings. Synthetic tests pass; a real run is recorded if data is available. | LC06 |
| LC08 | Done | Reproducible Windows executable build | Add a build script/spec and dependency notices; executable launches and captions on the development machine; weights remain a separate download; build artifacts are ignored. | LC03, LC05 |
| LC09 | Blocked | Clean Windows distribution verification | Test the executable and model setup on a clean Windows machine/VM, including a path with spaces and offline restart. Record exact environment and results. If unavailable, mark blocked rather than passed. | LC08 + clean Windows environment |
| LC10 | Done | Keyboard navigation and focus | Add useful shortcuts, predictable focus, and accessible control labels; test keyboard-only add/generate/edit/export/session flows. | LC02 |
| LC11 | Next | Manual accessibility acceptance | Use Windows assistive technology with a user/tester to review announcements, focus, progress, and errors; record evidence and fix observed issues. If unavailable, mark blocked. | LC10 + manual testing |
| LC12 | Planned | Optional GPU inference | Add explicit device selection with CPU fallback and tests; measure real speed/memory only on available supported hardware. Do not replace the working CPU setup merely to attempt a benchmark. | LC05 + hardware decision |

LC09 blocker (2026-11-06): this development host is Windows 10 Home, build 19045.
WindowsSandbox.exe, Hyper-V Get-VM/vmms, VMware vmrun, and VirtualBox VBoxManage
were not found through command/service discovery. No separate clean Windows host
was supplied. Clean-machine testing remains unperformed; no OS features or VM
software were installed. LC10 proceeded as the next independent ready task.

## Session routine

1. Read STATUS.md and the selected row; inspect only relevant code and current Git changes.
2. State the task in one short progress update. Implement its deliverable without expanding into later tasks.
3. Run checks appropriate to the change, following AGENTS.md. Prefer existing fixtures and cached dependencies.
4. Update task state, overwrite the compact handoff, and append a brief dated progress entry: task, result, checks, limitations.
5. Commit meaningful source/docs with subject such as `feat(LC01): add versioned session storage`; push main and verify the remote commit. GitHub Actions stays disabled until the user requests otherwise.
6. Stop after that verified unit. Final response: result, validation, commit link, next ID.

If work is interrupted, STATUS.md must say what is complete, which checks remain, and the exact next action. A partial checkpoint may be committed if useful and clearly labeled; do not mark its task Done.

## GitHub contribution expectations

Each actual workday can produce a real commit. This plan does not run while the conversation is inactive, guarantee a contribution streak, or schedule future commits. More commits on one date do not create more contribution days. Continue using the configured author email; GitHub attribution depends on that email being associated with the account.

## Keep context small

STATUS.md is the normal entry point. PLAN.md is the queue. PROGRESS.md is the append-only evidence trail, consulted only for the relevant checkpoint. VALIDATION.md records substantial test boundaries and results. Do not duplicate these documents or reread the full history on every session.
