# LumaCaption working instructions

## Resume with minimal context

1. Read docs/STATUS.md first. It is the compact handoff, not a substitute for code.
2. Check git status --short. Preserve unrelated user changes.
3. Read only the selected task in docs/PLAN.md and the files needed for it.
4. On "continue", complete ONE ready task, verify it, record progress, commit and push to origin/main, then stop. Do not start the next task unless asked.

## Efficient execution

- After the reported blue screen during LC08R, the user requested low PC load. Default to lightweight edits and focused checks, run resource-sensitive work sequentially, and do not automatically retry packaging or model inference on a generic continuation. Review resource needs and agree on a safe execution environment before another heavy build. Do not close unrelated user apps.
- Reuse the installed .venv and downloaded model. Do not reinstall, redownload, rescan the whole repository, reread all historical logs, or run a broad review by default.
- Use targeted rg searches and batch independent reads. Keep tool output short.
- Work as one agent unless the user explicitly requests delegation.
- For functional changes: run focused checks during development, then the existing full pytest suite and Ruff before the checkpoint push. Do not repeat passing checks without a relevant change.
- For documentation-only changes: check links/paths, consistency, and git diff --check; do not rerun ML inference or the full test suite.
- Run scripts/verify_offline.py only for model, generation, device, image-processing, or inference-thread changes. Use cached weights and local photos.
- Desktop tests require the Windows user context if the sandbox cannot initialize Tcl.
- GitHub Actions is disabled at the user's request. Keep it disabled unless explicitly asked to re-enable it. Run local checks before pushing and verify the remote commit; do not wait for hosted CI.

## Commit and handoff

- The user authorized commits and pushes to public Pavi21P/lumacaption on main. Continue within that scope without repeatedly asking for the same permission.
- Use actual commit timestamps and meaningful changes. Never backdate, create empty activity commits, or claim one session equals several contribution days.
- Update docs/STATUS.md (keep it under 40 lines), the task state in docs/PLAN.md, and append a short actual-date entry to docs/PROGRESS.md in the same checkpoint commit.
- Include task ID in the commit subject. Report outcome, checks, commit, and next task concisely.
- Keep tutorial originals, datasets, photos, weights, environments, caches, exports, credentials, and local verification reports out of Git. They are not application source.
- Preserve model/dependency attribution. Never claim measured accuracy, fresh-machine compatibility, GPU support, or accessibility acceptance without evidence.

## Daily sessions

The plan is a queue of work sessions, not an unattended scheduler. A user message starts each session. If a task is blocked by missing hardware or human acceptance, record the blocker and choose only a ready independent task within the authorized scope; do not manufacture a commit to fill a day.
