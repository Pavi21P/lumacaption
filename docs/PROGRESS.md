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
