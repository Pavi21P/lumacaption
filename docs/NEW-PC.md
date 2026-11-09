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

## University workspace checkpoint (2026-11-09)

The user confirmed that the proposed setup is permitted. This records their
confirmation; no university policy document was independently reviewed.
The workspace now has the source checkout, portable Git 2.56.0.windows.4,
official Python 3.11.9 x64 with Tcl/Tk, and the pinned runtime/build environment.
Spyder's conda-forge Python was left intact. Do not reinstall on continuation.

From this project folder, use these existing paths (Git/Python were not added to PATH):

~~~powershell
& .\.local\tools\git\cmd\git.exe status --short --branch
& .\.venv\Scripts\python.exe --version
& .\.venv\Scripts\python.exe scripts/build_windows.py --check-only --name LumaCaption-0.1.0-win64-university-20261109
~~~

The base interpreter is `.local/tools/python311/python.exe`. Runtime packages and
build tools are installed in `.venv`; pip's download cache is `.cache/pip`.
The three supplied test photos were moved into the ignored `.local/Test Images`
folder, preserving their names. Do not add photos, local tools, or raw logs to Git.
The source CLI help and synthetic tests passed; no executable or real caption was
generated. The diagnostic's model-cache failure is expected: no weights are cached.
For a future approved model setup/run, consistently set:

~~~powershell
$env:LUMACAPTION_CACHE = Join-Path (Get-Location) '.cache\models'
~~~

Latest readings after user cleanup: 5.17 GiB available RAM and 73.21 GiB free C:.
The proposed heavy-task start threshold was 8 GiB available RAM, with a stop below
2 GiB RAM or 15 GiB free disk. These are conservative operating limits, not tested
requirements. The user chose to save the setup checkpoint and leave the build pending.
Recheck resources or explicitly agree on a revised plan before any build/model run.
An ignored local monitoring helper/logs exist, but they are not part of the source
distribution. Initial setup exit-code capture was incomplete; later checks and
subsequent monitored commands supplied explicit results (see VALIDATION.md).

After a verified build, complete the requested packaged desktop/CLI launch, three
real captions, offline restart, spaced-folder path, keyboard navigation, caption
edit, CSV/JSON exports, session save/reopen, and cancel-unsaved-prompt preservation
checks. Record each actual result; none is established by the current source tests.
Screen-reader testing remains deferred. This host now has development tools, so
describe that fact when assessing the separate LC09 clean-machine requirement.
