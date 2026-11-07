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

## 2026-11-04 - LC02: desktop Save/Open sessions

- Added native Save/Open dialogs for complete workspaces, including pending rows, edited/original captions, generation settings, and provenance.
- Added save/discard/cancel prompts before replacing unsaved work. Failed or cancelled saves keep the workspace; malformed imports never replace it. Saving over the session being opened restores the newly saved contents.
- Flagged missing images as red Missing rows without changing their stored result data. Retained captions remain available; missing rows are excluded from generation/retry. Opening a session does not start inference.
- Kept Save/Open disabled during batches and separated result export from saving a workspace. Reset editor undo history when switching/restoring captions.
- Validation: 22 desktop tests passed; 101 tests passed overall; Ruff lint/format and Git whitespace checks passed.
- Because restored generation options now reach the worker, reran the real cached-model offline smoke: zero network attempts, unchanged source hashes, matching desktop-worker captions, successful CSV/JSON export checks, 28.904 seconds total.
- Published source/docs only; original tutorial files, photos, weights, environments, sessions, and local reports remain excluded. No manual visual/accessibility acceptance is claimed.
- Next: LC03 local autosave and recovery.

## 2026-11-05 - LC03: local autosave and startup recovery

- Added one-second debounced atomic snapshots in Windows local app data, with a pre-generation snapshot of pending work. Caption edits, pasted text, settings, retries, and completed results trigger recovery updates.
- Added startup restore/discard choice. Recovery preserves captions/provenance/settings, leaves interrupted rows pending, and never starts the model automatically.
- Added OS-lock ownership so another app window cannot overwrite the active recovery copy. Abrupt-process-exit tests confirm the lock releases and the saved copy survives.
- Kept manual session saves distinct from recovery. Explicit save/discard actions clean the recovery copy; cancellation, invalid imports, and failed saves preserve it. Failed writes preserve the last good copy; corrupt startup files are left intact with recovery disabled and a visible message.
- Added 28 tests: 20 desktop recovery cases and 8 recovery-storage cases. Full suite: 129 passed; Ruff lint/format and whitespace checks passed.
- Repeated independent Tk creation exposed intermittent fixture setup errors. Changed tests to one Tcl runtime and a fresh window per case; the full suite then passed without skips.
- Real-model offline regression passed: identical captions, zero network attempts, unchanged source hashes, matching desktop-worker output, CSV/JSON checks, 48.959 seconds total. Smoke tooling disables recovery to avoid touching user data.
- Source, tests, and docs only; tutorial originals, images, weights, recovery data, and reports remain excluded. Manual visual/accessibility acceptance is still unverified.
- Next: LC04, relink moved or missing images.

## 2026-11-05 - LC04: relink moved or missing images

- Added a selection-aware Relink image dialog for missing rows, disabled while a batch runs. Replacement files must pass supported-type and existing image validation before any path change.
- Preserve captions, edits, original AI text, status/errors, timing, provenance, queue order, and selection. Refresh the preview, mark the workspace unsaved, and schedule recovery without starting generation.
- Reject duplicate normalized Windows paths and existing file aliases. Cancelled dialogs and invalid/unavailable/damaged replacements preserve the previous row and recovery copy.
- Detect images moved while the app is open when their row is selected; reselecting a restored file clears its missing warning.
- Added 19 desktop cases for field preservation, cancelled/failed validation, duplicates/hard links, order/selection, restored paths, busy controls, moved images, recovery/manual-save round trips, and explicit generation using the replacement.
- Validation: 148 tests passed, including 61 desktop cases; Ruff lint/format and whitespace checks passed.
- Real cached-model regression passed with identical captions, zero network attempts, unchanged source hashes, matching desktop-worker output, and CSV/JSON checks in 44.653 seconds. Original images and the report remain local.
- Updated the compact plan and usage documentation. Tutorial originals, datasets, photos, weights, environments, recovery files, and reports remain excluded from publication.
- Next: LC05, model and startup diagnostics.

## 2026-11-05 - LC05: model and startup diagnostics

- Added --diagnose with supported Python/bitness, real Tk initialization, runtime dependency version/import checks, and pinned-cache file checks. It prints actionable fixed hints without local paths, tokens, raw errors, or local build identifiers.
- Isolated Tk/dependency imports in a child process with network connections disabled and a 45-second timeout. Diagnostics never calls model loading or downloads; cache readability is explicitly distinguished from weight integrity and inference readiness.
- Made CLI backend imports lazy so diagnostics/help work when Pillow or ML packages are unavailable. Extracted unchanged model/cache settings into dependency-free config.py and retained engine reexports.
- Added 40 diagnostic tests covering missing/incompatible dependencies, bad metadata, unsupported Python/bitness, incomplete/unreadable caches, child failures/timeouts, private output, offline guards, and CLI dispatch without application dependencies.
- Validation: 188 tests passed, Ruff lint/format passed for 18 files, and real diagnostics returned exit 0 with all checks passing in the Windows user context.
- Shared-settings regression: real offline captions matched prior output; zero network attempts, unchanged source hashes, matching desktop-worker output, and CSV/JSON checks passed in 30.658 seconds.
- Disabled GitHub Actions following the user's stop request; no active runs remained to cancel. After the user resumed development, retained the disabled state and documented local verification for future checkpoints.
- Tutorial originals, images, weights, environments, sessions, and local reports remain excluded. Next: LC06 evaluation protocol.

## 2026-11-05 - LC06: reproducible evaluation protocol

- Added docs/EVALUATION.md: deterministic 50-image test and 10-image dev selection, frozen private manifests, fixed CPU generation settings, explicit BLEU/ROUGE-L variants, failure accounting, timing, and a separate human-review rubric.
- Checked publisher terms and primary metric/model sources; documented educational/non-commercial dataset use, attribution, and unverified overlap with BLIP training data.
- Audited local metadata: disjoint 6000/1000/1000 train/dev/test lists; all 1000 test identifiers have existing image paths and five references. Selected 50 test/10 dev inputs also have files and reference IDs 0-4. Two known smoke-test inputs do not occur in dev/test.
- Selection/source hashes are recorded in an ignored local aggregate audit. No images were opened or inference run; no quality scores or human ratings exist for this checkpoint.
- Documentation checks cover relative links, paths, control characters, task consistency, and git diff whitespace. Existing 188-test/Ruff/offline evidence remains the LC05 baseline; no functional code changed.
- Tutorial originals, datasets, captions, weights, and local reports remain excluded. GitHub Actions stays disabled. Next: LC07, evaluation runner and measured baseline.

## 2026-11-05 - LC07: evaluation runner and measured baseline

- Added a separate freeze/run CLI with deterministic selection, strict manifest checks, explicit BLEU-1/BLEU-4/ROUGE-L scoring, fixed offline CPU settings, and source/environment hashes. The desktop and shared inference engine are unchanged.
- Retain all 50 test rows across missing/corrupt/changed inputs, model failures, and interruption. Atomically checkpoint progress; refuse output reuse; sanitize errors and keep all raw artifacts inside ignored local storage.
- Added 64 synthetic tests for metric edge cases and non-perfect scores, reference validation, stable sampling/exclusions, changed files, partial reports, offline guards, timing, blank human reviews, and CLI output protection. Final full suite: 252 passed; Ruff lint/format: 21 files.
- Frozen manifest matches LC06's dataset/selection/exclusion hashes. Real cached-model evaluation completed 50/50 with no image failures or network attempts. BLEU-1 57.60, BLEU-4 21.46, ROUGE-L 47.21 are reference-overlap scores, not accuracy percentages.
- Verified all 60 selected input hashes, original split/reference hashes, frozen manifest, protocol, dependency lock, and runtime source hashes. Raw captions, references, reports, and review templates stay local.
- Human review remains pending at 0/50. Some synthetic tests ran concurrently, so recorded timing is not an isolated performance benchmark. No controlled comparison with the tutorial or guarantee of upstream training-data independence.
- Updated usage, validation, and compact handoff. GitHub Actions remains disabled. Next: LC08, reproducible Windows executable build.

## 2026-11-06 - LC07: publication checkpoint

- Resumed publication after interruption; implementation and baseline were completed in the preceding session. Rechecked documentation and publication exclusions before committing the existing tested work.

## 2026-11-06 - LC08: portable Windows executable build

- Added a pinned PyInstaller folder recipe with desktop and console launchers, frozen diagnostics, a bundled offline smoke command, source/file checksums, and dependency notices. Existing source launchers and CPU generation settings remain unchanged.
- Build refuses existing output, checks Python/dependency versions, keeps weights separate, and strips generated pip source-URL metadata before finalization. Retained Python, Tcl/Tk, and dependency license texts; build artifacts stay ignored.
- Built a 621.6 MiB folder with 6,200 verified file hashes and 23 matching source hashes. Python 3.11.9 x64, PyInstaller 6.22.3, hooks 2026.9. The initial finalization correctly rejected editable-install metadata; corrected cleanup and finalized the compiled bundle.
- Full regression: 270 tests passed, Ruff lint/format for 25 Python files, pip check, and PowerShell syntax validation passed.
- Console and windowed executables each captioned two local photos offline, matched prior source captions, preserved inputs, and passed real Tk worker plus CSV/JSON export checks. Zero network attempts; smoke times 40.405 and 30.444 seconds respectively.
- Help and frozen diagnostics passed. Tracked files and reachable history exclude tutorial originals, datasets, photos, weights, caches, and generated output. GitHub Actions remains disabled.
- No installer, signature, binary release, clean-machine claim, or manual visual/accessibility acceptance. Next: LC09 clean Windows distribution verification.

## 2026-11-06 - LC10: keyboard navigation and focus; LC09 blocked

- Checked the LC09 prerequisite: Windows 10 Home build 19045, no WindowsSandbox.exe, Hyper-V command/service, VMware vmrun, or VirtualBox VBoxManage found, and no separate clean test host supplied. Recorded LC09 as blocked; did not install VM tooling or claim clean-machine success.
- Completed the next independent task, LC10. Added keyboard shortcuts and F1 help, editor Tab/Shift+Tab traversal, queue/editor switching, queue selection focus, disabled-control focus recovery, and a descriptive editor label/focus border.
- Shortcuts invoke the existing enabled controls and respect modal grabs. Existing Save/Open/discard/recovery rules remain intact; normal text editing and undo retain Tk bindings.
- Real key tests exposed an unsupported non-Windows key symbol, removed before verification, and a pre-existing layout issue hiding lower controls on this 1366x768 display. Reserved footer space and let the queue shrink so controls remain visible, including at the minimum 960x680 client size.
- Ten new real-Tk keyboard/layout cases pass; full regression: 280 passed in 25.10 seconds. Ruff lint/format passed for 25 Python files. Tests use a fake captioner and stubbed native-dialog responses; no model download or inference rerun was needed.
- Documented shortcuts and an LC11 manual walkthrough. The existing LC08 executable remains an older snapshot; source launcher includes these changes, and a new named build is required for updated binaries.
- Tutorial files, datasets, photos, weights, environments, and generated output remain excluded. GitHub Actions stays disabled. Next: LC11 manual accessibility acceptance; LC09 awaits a clean environment.

## 2026-11-06 - LC11: partial manual feedback; accessibility acceptance deferred

- Opened the current source app at b7dc980 with offline mode, the existing model cache, and an isolated recovery directory. Created two original synthetic image fixtures under ignored local storage. Recorded a 1366x768 display and Tk 8.6.12; no user recovery files were replaced.
- User reported the app and captioning worked well. Follow-up clarified that no screen reader was used and the final edit/export/save/reopen/cancel checks had not been tried. This is positive visual/captioning feedback, not completed accessibility or persistence acceptance.
- User requested skipping screen-reader testing for now. Marked LC11 blocked and retained the walkthrough for later. No application defect was reported or source fix made.
- Documentation-only checkpoint: checked links, status/task consistency, whitespace, and publication exclusions. Existing 280-test LC10 evidence remains unchanged; no tests or inference were rerun.
- Raw observations and fixtures remain private. GitHub Actions stays disabled. Next: LC12 optional device selection with CPU fallback; LC09 and LC11 still need their external test conditions.

## 2026-11-06 - LC12: optional device selection with CPU fallback

- Added desktop cpu/cuda selection and CLI --device, with CPU remaining the default. The header/CLI show the actual device and fallback; settings are locked during a batch, and device preference stays outside saved sessions.
- Added CUDA availability/placement fallback and a single CPU retry after CUDA out-of-memory. Move model and all inputs together without changing integer token types; preserve generation settings and reuse the fallback engine across batches.
- Read-only hardware check: Intel HD Graphics 620, torch 2.15.0+cpu, no CUDA build, CUDA unavailable, zero CUDA devices. Kept dependencies/drivers unchanged; no real GPU execution or performance claim.
- Added 18 simulated engine/CLI cases and two desktop cases. Full suite: 300 passed in 23.76 seconds; Ruff lint/format passed for 26 Python files, including prior keyboard/minimum-layout regressions.
- Real offline CPU and requested-CUDA fallback runs each captioned two local photos, matched earlier CPU captions, preserved originals, made zero network attempts, and passed real Tk worker plus CSV/JSON export checks. Times: 24.537 and 23.312 seconds; these are CPU smoke timings, not GPU benchmarks.
- Documented device behavior, hardware limits, and reproducible checks. The fixed CPU evaluation and session format remain unchanged. Existing LC08 binaries predate LC10/LC12 and were not rebuilt.
- Tutorial originals, datasets, images, weights, local reports, and build outputs remain excluded. GitHub Actions stays disabled. Only LC09 clean-machine and LC11 manual accessibility acceptance remain incomplete, both blocked by their test conditions.
