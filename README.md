# LumaCaption

**Your photos, put into words.** A Windows desktop app that generates image captions locally, lets you edit them, and exports a whole batch to CSV or JSON.

LumaCaption's application code is written from scratch. Its AI is the pretrained [Salesforce BLIP base model](https://huggingface.co/Salesforce/blip-image-captioning-base); this project does not claim to have trained BLIP. No original tutorial code, Flickr8k data, or model weights are included in this repository.

## What it does

- Add individual images or a folder, optionally including subfolders.
- Preview images with correct EXIF orientation and transparent backgrounds.
- Generate short, standard, or long captions on CPU; optionally request CUDA with CPU fallback.
- Keep the window responsive while processing; cancel between images.
- Edit captions, restore the original AI text, and copy to the clipboard.
- Save and reopen a session with its queue, edited captions, and settings.
- Automatically keep a local recovery copy and offer to restore it after an interruption.
- Relink moved images while preserving their captions and edits.
- Export CSV for spreadsheets or JSON with original captions and model provenance.
- Continue past damaged files, then retry errors.
- Work offline after the model is downloaded. Images never go to a captioning API.

## Start on Windows

Requirements: 64-bit Windows 10/11, **Python 3.11–3.13 with Tcl/Tk**, an internet connection for initial installation, and several GB of free disk space. CPU inference needs no GPU or API key. 8 GB RAM is recommended; available memory affects speed and capacity.

Open PowerShell in this folder:

~~~powershell
.\Setup-Windows.ps1 -DownloadModel
~~~

If Python isn't detected:

~~~powershell
.\Setup-Windows.ps1 -PythonExe "C:\Path\To\Python\python.exe" -DownloadModel
~~~

Then double-click **Launch-LumaCaption.cmd**. The main desktop module is **src/lumacaption/desktop.py**. The launcher keeps a console available for download progress and startup errors.

The first model download is approximately 1 GB. The launcher stores it in `.cache/models`, excluded from Git. Subsequent launches reuse it. Turn on **Offline** to prevent model-download requests.

Setup creates a dedicated `.venv`, installs the pinned dependency snapshot, and prints:

~~~text
LumaCaption is ready. Double-click Launch-LumaCaption.cmd.
~~~

For development tools, add `-Dev`. If Windows reports a missing runtime DLL, install the Microsoft Visual C++ 2015–2022 x64 Redistributable from Microsoft's official site. If Tcl/Tk is missing, modify your Python installation to include it.

## Command line

The launcher also accepts CLI arguments:

~~~powershell
.\Launch-LumaCaption.cmd "C:\Photos\dog.jpg"
.\Launch-LumaCaption.cmd "C:\Photos" --output captions.csv
.\Launch-LumaCaption.cmd "C:\Photos" --recursive --offline --length Long --output captions.json
~~~

Or invoke `.venv\Scripts\python.exe -m lumacaption` directly. Direct invocation uses `%LOCALAPPDATA%\LumaCaption\models` unless `LUMACAPTION_CACHE` is set. To use the launcher's cache in PowerShell:

~~~powershell
$env:LUMACAPTION_CACHE = Join-Path $PWD ".cache\models"
.\.venv\Scripts\python.exe -m lumacaption --download-model
~~~

An existing CLI export is protected unless you pass `--force`. Exit codes: 0 success, 1 one or more image failures, 2 input/setup failure, 130 interrupted.

## Compute device

CPU is the default. Choose cpu or cuda in the desktop's **Compute device** control,
or pass --device cuda to the launcher/CLI. The header and CLI status report the
actual device; unavailable CUDA falls back to CPU. This machine's CPU fallback is
verified; real GPU execution and performance remain unverified. Device selection
does not install drivers or change dependencies. See [device behavior and limits](docs/DEVICES.md).

## Local diagnostics

Run this from the project folder:

~~~powershell
.\Launch-LumaCaption.cmd --diagnose
~~~

This checks supported Python/bitness, actual Tk window initialization, installed runtime dependency versions/imports, and readable files for the pinned BLIP revision. It does not download files, load model weights, or start captioning. The isolated import probe blocks network connections and has a 45-second timeout. Output omits local paths, tokens, build identifiers, and raw errors.

Exit code 0 means every reported check passed; 1 means at least one check needs attention; 2 means invalid command usage. Use --diagnose by itself. A readable cache is not proof of weight integrity or successful inference. Follow the printed setup/download hints, then test an image to verify captioning.

For scripted use without the launcher's pause on failures, run .venv/Scripts/python.exe -m lumacaption --diagnose with LUMACAPTION_CACHE set to .cache/models. Direct invocation otherwise uses the regular app-data cache, as described above.

## Portable Windows executable

Build a portable folder with desktop and console launchers using
Build-Windows.ps1 -InstallBuildTools. The pinned recipe requires Windows x64
and CPython 3.11.9; see [build and verification instructions](docs/PACKAGING.md).
Keep the complete output folder together. Model weights are a separate download.
This development build is unsigned; clean-machine verification is still pending.

## Working with captions

1. Select **Add images** or **Open folder**.
2. Choose a caption length and click **Generate captions**.
3. Select a row to review its image and edit the draft caption.
4. Use **Save session** to keep your workspace, then **Open session** to resume later.
5. Use **Export results** for a CSV spreadsheet or JSON report.

Sessions default to workspace.lumacaption.json. Opening, clearing, or closing an idle workspace prompts to save unsaved changes. Cancelling a save or encountering a save error keeps the current workspace. Save/Open controls are disabled during generation; cancel the batch and wait for it to finish before saving.

Sessions store image paths, not copies of your photos. Missing images appear as red **Missing** rows, with their saved captions preserved for editing, copying, and export. Select a missing row and use **Relink image...** to locate its file. The app validates the replacement before changing the path, keeps the caption, and updates the recovery copy. Review the caption against the replacement image. Relinking is disabled during generation. Opening a session never starts generation automatically. See the [session format and behavior](docs/SESSIONS.md).

Export files contain results; use a session file to restore the queue and settings. Exporting does not clear the unsaved-workspace prompt. The desktop keeps an automatic recovery copy about one second after changes stop, and snapshots pending work before generation. After an interruption, reopening offers to restore the queue, edits, and settings without starting generation.

Recovery lives in %LOCALAPPDATA%\LumaCaption\recovery, outside the project. It does not clear the unsaved-work prompt or replace **Save session**. Explicitly saving or discarding a workspace removes its recovery copy. The footer reports recovery status; if recovery is unavailable, use **Save session** manually. Only one open app window owns automatic recovery at a time.

JPG, PNG, WebP, BMP, and TIFF are supported. Animated/multipage inputs use the first frame. Limits: 40 MB and 40 megapixels per image, 1,000 images per workspace. Duplicate paths are skipped.

Cancellation finishes the current model operation before stopping. A model download can take time and cannot be interrupted immediately with the batch button. Completed captions remain available to export.

CSV uses UTF-8 with a BOM for Excel and escapes formula-like cells. JSON preserves paths, original AI captions, edits, errors, generation time, and model revision. Your original image files are never changed.

## Keyboard controls

Use Ctrl+I to add images, Ctrl+Enter to generate, Ctrl+E to export, and Ctrl+S /
Ctrl+O to save or open sessions. F6 switches between the queue and caption editor.
Tab and Shift+Tab leave the editor without inserting tabs. Esc cancels a running
batch; F1 opens the full shortcut list. See [keyboard behavior and verification
limits](docs/KEYBOARD.md). LC10 changes are in the source app; the existing local
LC08 executable needs rebuilding to include them.

## Improvements over the starting tutorial

| Starting workflow | LumaCaption |
| --- | --- |
| Absolute Mac paths | Windows file dialogs, pathlib, quoted launch paths |
| Training needed before running inference | Download a pretrained model once |
| Separate scripts with mismatched model folders | Shared desktop/CLI inference engine |
| One image from a terminal | Previewable batch queue and editable captions |
| Generated pickle/tokenizer files | Versioned pretrained processor and model |
| Minimal error reporting | File validation, per-image recovery, export protection |
| Unrecorded manual changes | Local tests, checkpoint commits, and progress log |

These are workflow and reliability improvements. **No controlled caption-quality comparison with the tutorial model has been performed.**

## Validation and limitations

Run checks from this directory:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts packaging/entry.py
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts packaging/entry.py
.\.venv\Scripts\python.exe -m pip check
~~~

The 310 automated tests use synthetic images and a fake captioner; they do not download model weights. A separate real-BLIP smoke test also passed with network calls blocked, including the desktop worker and exports. See [validation evidence and reproduction steps](docs/VALIDATION.md).

The [evaluation protocol and CLI instructions](docs/EVALUATION.md) define a fixed 50-image local test subset, lexical metrics, and a separate human-review rubric. The first offline run completed all 50 images with zero network attempts: BLEU-1 57.60, BLEU-4 21.46, and ROUGE-L 47.21 on the defined 0-100 scales. These are reference-overlap scores, not accuracy percentages or proof of improvement over the tutorial. Human review is pending; see the [configuration, timings, and limitations](docs/VALIDATION.md#lc07-evaluation-runner-and-baseline-2026-11-05).

BLIP can omit details, invent objects, or describe people incorrectly. Review captions before using them as accessibility text. Longer generation limits do not guarantee more accurate detail. This release generates English captions and defaults to CPU. It does not include custom model training or an installer executable. The optional CUDA path is experimental; real GPU validation is pending.

## Development record

GitHub Actions is currently disabled at the user's request. Development checkpoints run appropriate local checks before publication; documentation-only checkpoints verify links and consistency.

[Progress](docs/PROGRESS.md) · [Design decisions](docs/DECISIONS.md) · [Execution plan](docs/PLAN.md) · [Current status](docs/STATUS.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Progress is recorded in meaningful commits on the actual day of work. Future daily contributions require future work; no history is backdated. To count toward a GitHub profile, commit email must be associated with that account and commits must reach its default branch.

## License

Original LumaCaption code is MIT licensed. Dependencies and model weights retain their own licenses; see the third-party notices.
