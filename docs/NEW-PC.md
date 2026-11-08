# Continue LumaCaption on another Windows PC

The source, decisions, progress, and next task travel through GitHub. A new Codex
chat can read them; the original chat is not required. Codex documents local
[session history storage](https://developers.openai.com/codex/config-advanced/#history-persistence).
Cloning this project does not transfer that history or restore the old chat.

## Open the project

Use a university PC only where your coursework permits development tools and the
planned workload. Its capacity and availability have not yet been checked.

In an allowed working folder, with Git available:

~~~powershell
git clone https://github.com/Pavi21P/lumacaption.git
cd lumacaption
~~~

Open this **lumacaption folder** in VS Code (File > Open Folder), then open the
Codex extension and sign in with your account. Start a new chat and paste the
prompt below. You can read this file directly on GitHub before cloning.
If Git or the extension is unavailable, use the university's approved installation
process; the repository can still be read in the browser.

## Paste into a new Codex chat

~~~text
Continue my LumaCaption project from this Git checkout. The previous chat is on
another PC. Read AGENTS.md, docs/STATUS.md, and docs/NEW-PC.md, then check git status.
Read only the relevant task in docs/PLAN.md. Do not start work from scratch.

This is a candidate university Windows PC, not yet an approved build environment.
First do ONE lightweight, read-only host assessment: Windows/Python architecture
and versions, available RAM, free space on the project/system drives, installed
Git/Python tools, and whether the project environment already exists. Report any
access restrictions or missing tools. Ask me to confirm that the university allows
the proposed setup/build before making system or environment changes.

Do not install dependencies, download models, start PyInstaller, run inference,
change system settings, or enable GitHub Actions during this assessment. My home
PC blue-screened during an earlier build; the cause remains unknown. Passing the
3 GiB disk guard alone is not proof of safe build capacity. Propose a resource plan
for this machine before any heavy work. Work sequentially and leave other apps alone.

The application uses pretrained BLIP; all application code is original. Keep
YouTube originals, datasets, photos, model weights, caches, environments, build
output, exports, credentials, and raw local reports out of Git. GitHub Actions
stays disabled. Screen-reader testing was deferred; do not restart it unprompted.

Use the current repository handoff as the source of truth. Record verified results
and limitations in the plan/status/progress. Commit meaningful changes on their real
date and push to Pavi21P/lumacaption main when Git authentication is available, then
verify the remote commit. Stop after this one checkpoint. Do not mark packaging,
clean-machine testing, GPU support, or accessibility passed without actual evidence.
~~~

## What is and is not transferred

- Tracked application code, build recipe, tests, and documentation come with the clone.
- Read [STATUS.md](STATUS.md) for the latest checkpoint and [PLAN.md](PLAN.md) for tasks.
- The home PC's .venv, model cache, private photos/reports, and executable folders
  are intentionally excluded. Old absolute paths in evidence refer to that PC.
- A fresh clone needs its own approved environment before the build check can run.
  The pinned executable recipe requires Windows x64 and CPython 3.11.9; see
  [PACKAGING.md](PACKAGING.md). Do not copy the home .venv onto the university PC.
- A university PC is a candidate separate host, not automatically a clean test
  environment. Record its actual setup before claiming LC09 verification.

## Keep both PCs in sync

Before changing files on either PC, inspect `git status`. If clean, use
`git pull --ff-only` to obtain the latest work. If there are local edits or diverged
history, preserve them and reconcile deliberately; do not reset or overwrite them.

For commits on the new checkout, configure the existing identity locally:

~~~powershell
git config user.name "Pavi21P"
git config user.email "pavitrapatil333@gmail.com"
~~~

Commit/push completed work and update the handoff before switching machines.
Git authentication is separate from Codex sign-in; use the normal approved login
flow, not copied credential files. On a shared university login, sign out of
Codex/GitHub when finished and do not leave saved credentials behind.
