# Progress log

Entries describe work actually performed on the date shown (America/Chicago). Commits use their actual creation timestamps. Multiple checkpoints on one day are still one contribution day; this project does not fabricate historical or future activity.

## 2026-11-03 — Checkpoint 1: independent project foundation

- Reviewed the supplied tutorial scripts without executing them. Identified absolute Mac paths, missing generated dependencies, and mismatched training/inference model directories.
- Created a separate LumaCaption project with packaging, development configuration, and source-only Git exclusions.
- Kept all uploaded tutorial files and dataset directories in the parent workspace, outside this repository.
- Chose a Windows desktop application with CPU-first pretrained BLIP inference; user confirmed use of a pretrained model.
- Located Python 3.11.9 and created a dedicated virtual environment.
- Validation: inspected project boundaries and package configuration. Application implementation is the next checkpoint.

## 2026-11-03 — Checkpoint 2: captioning pipeline and exports

- Added lazy BLIP loading with a pinned upstream model revision, CPU inference, bounded generation, cached offline mode, and restricted weights-only loading.
- Added Windows/Unicode path handling, image deduplication, EXIF orientation, grayscale and transparency handling, 40 MB/40 megapixel limits, and a 1,000-image batch limit.
- Added per-image errors, cancellation between images, original/edited caption provenance, atomic CSV/JSON exports, overwrite protection, and spreadsheet formula escaping.
- Added a CLI for individual images, folders, recursive batches, model download, and exports.
- Validation: 31 tests passed on Windows/Python 3.11.9; dependency consistency check passed. Real model download/inference verification is in progress.

## 2026-11-03 — Checkpoint 3: Windows desktop workspace

- Built the native desktop workspace with file/folder selection, preview, queue status, caption-length controls, progress, cancellation, and failed-image retry.
- Added editable captions, copy/restore actions, CSV/JSON save dialogs, and protection against accidentally discarding unexported work.
- Kept inference off the Tk event thread and preserved fatal errors across separate event polls.
- Integrated the Windows trust store after a verified HTTPS certificate-chain failure; TLS verification remains enabled.
- Added a double-click launcher, PowerShell setup script, pinned dependency snapshot, and Windows CI workflow.
- Validation: all five desktop integration tests passed in the Windows user context (36 tests total with the core suite); lint, formatting, and PowerShell syntax checks passed. The sandbox could not initialize the installed Tcl runtime, so desktop tests required the normal user context.
- Real model download is underway; caption accuracy and interactive visual acceptance are not yet established.

## 2026-11-03 — Checkpoint 4: publish the current verified source

- Completed Windows usage instructions, project licensing, model/dependency attribution, validation evidence, and a bounded roadmap for future work.
- User requested publication of all current changes to the public Pavi21P repository, excluding the YouTube originals.
- Final local verification: 36 tests passed together in the Windows user context, Ruff lint and formatting passed, dependency consistency passed, and Git whitespace checks passed.
- The model download and full setup execution were interrupted. Real inference, offline inference, fresh-machine setup, and manual visual acceptance remain explicitly unverified.
- Publication includes only the independent LumaCaption project. Original tutorial scripts/dataset remain in the parent workspace; environments, model caches, and generated files remain excluded.
- This checkpoint is committed with its real creation date; earlier implementation checkpoints are preserved.

## 2026-11-04 — Checkpoint 5: verified local model and Windows startup

- Confirmed the initial published commit passed hosted Windows CI.
- Recorded the completed November 3 real-model smoke test: two captions, zero network attempts, unchanged source-image hashes, matching desktop-worker output, and successful CSV/JSON round trips.
- Added scripts/verify_offline.py so the same checks can be repeated with locally supplied photos; model weights and reports remain outside Git.
- Verified the actual Windows launcher with an offline image path containing spaces and a JSON export.
- Strengthened setup validation to initialize Tk, and removed redundant pip version checks during installation.
- Identified an optional Transformers conversion worker that delayed normal online-mode process exit. Disabled that conversion inside the application process while retaining the pinned model and restricted weights-only loading.
- Reran Setup-Windows.ps1 -Dev -DownloadModel successfully (exit 0) in the existing development environment. Fresh-machine installation and manual visual/accessibility acceptance remain unverified.
- Extended CI lint/format coverage to the verification script. All 36 local tests passed again after the loader fix.
- Preserved the original tutorial files and dataset outside the repository. No trained weights, test photos, or local output reports are published.
- Final real-model regression run passed after the loader fix: identical captions, zero network attempts, unchanged source files, desktop worker and exports verified; total 34.238 seconds.

## 2026-11-04 — P00: compact development plan

- Replaced the broad roadmap with 12 bounded work sessions, dependencies, and concrete completion checks.
- Added AGENTS.md and a short STATUS.md handoff so future sessions read the next task and relevant files rather than re-exploring the full project.
- Defined one ready task per continue request, targeted checks, cached-environment reuse, and a progress/commit/push step using the actual work date.
- Confirmed hosted Windows CI passed for fa6a3ab. This documentation checkpoint needs no repeated model run or application tests.
- Next: LC01, versioned saved-session storage. Daily sessions remain user-triggered; no unattended scheduler was configured.

## 2026-11-04 — LC01: versioned saved-session storage

- Added sessions.py with Session/load_session/save_session APIs, a distinct versioned JSON format, complete result/settings preservation, and validation of types, timestamps, paths, duplicates, versions, and size/count/text limits.
- Added atomic saves with explicit overwrite permission, concurrent-writer protection, temporary-file cleanup, and input-file overwrite protection. Loading preserves missing-image records and performs no image reads or model inference.
- Documented the contract in SESSIONS.md and ignored the default *.lumacaption.json save-file pattern.
- Validation: 48 focused storage tests passed; all 84 project tests, Ruff lint/format, and whitespace checks passed. Existing dependencies/cache were reused; no ML run was needed.
- Next: LC02 desktop Save/Open integration. UI and autosave work were intentionally left for their planned checkpoints.
