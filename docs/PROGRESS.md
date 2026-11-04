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
