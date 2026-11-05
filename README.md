# LumaCaption

**Your photos, put into words.** A Windows desktop app that generates image captions locally, lets you edit them, and exports a whole batch to CSV or JSON.

LumaCaption's application code is written from scratch. Its AI is the pretrained [Salesforce BLIP base model](https://huggingface.co/Salesforce/blip-image-captioning-base); this project does not claim to have trained BLIP. No original tutorial code, Flickr8k data, or model weights are included in this repository.

## What it does

- Add individual images or a folder, optionally including subfolders.
- Preview images with correct EXIF orientation and transparent backgrounds.
- Generate short, standard, or long captions on your CPU.
- Keep the window responsive while processing; cancel between images.
- Edit captions, restore the original AI text, and copy to the clipboard.
- Save and reopen a session with its queue, edited captions, and settings.
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

## Working with captions

1. Select **Add images** or **Open folder**.
2. Choose a caption length and click **Generate captions**.
3. Select a row to review its image and edit the draft caption.
4. Use **Save session** to keep your workspace, then **Open session** to resume later.
5. Use **Export results** for a CSV spreadsheet or JSON report.

Sessions default to workspace.lumacaption.json. Opening, clearing, or closing an idle workspace prompts to save unsaved changes. Cancelling a save or encountering a save error keeps the current workspace. Save/Open controls are disabled during generation; cancel the batch and wait for it to finish before saving.

Sessions store image paths, not copies of your photos. Missing images appear as red **Missing** rows, with their saved captions preserved for editing, copying, and export. Restore the files to their original paths and reopen the session to use them again. Opening a session never starts generation automatically. See the [session format and behavior](docs/SESSIONS.md).

Export files contain results; use a session file to restore the queue and settings. Exporting does not clear the unsaved-workspace prompt. Automatic recovery is not implemented yet.

JPG, PNG, WebP, BMP, and TIFF are supported. Animated/multipage inputs use the first frame. Limits: 40 MB and 40 megapixels per image, 1,000 images per workspace. Duplicate paths are skipped.

Cancellation finishes the current model operation before stopping. A model download can take time and cannot be interrupted immediately with the batch button. Completed captions remain available to export.

CSV uses UTF-8 with a BOM for Excel and escapes formula-like cells. JSON preserves paths, original AI captions, edits, errors, generation time, and model revision. Your original image files are never changed.

## Improvements over the starting tutorial

| Starting workflow | LumaCaption |
| --- | --- |
| Absolute Mac paths | Windows file dialogs, pathlib, quoted launch paths |
| Training needed before running inference | Download a pretrained model once |
| Separate scripts with mismatched model folders | Shared desktop/CLI inference engine |
| One image from a terminal | Previewable batch queue and editable captions |
| Generated pickle/tokenizer files | Versioned pretrained processor and model |
| Minimal error reporting | File validation, per-image recovery, export protection |
| Unrecorded manual changes | Tests, Windows CI, and checkpoint progress log |

These are workflow and reliability improvements. **No controlled caption-quality comparison with the tutorial model has been performed.**

## Validation and limitations

Run checks from this directory:

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
.\.venv\Scripts\python.exe -m pip check
~~~

The 101 automated tests use synthetic images and a fake captioner; they do not download model weights. A separate real-BLIP smoke test also passed with network calls blocked, including the desktop worker and exports. See [validation evidence and reproduction steps](docs/VALIDATION.md).

BLIP can omit details, invent objects, or describe people incorrectly. Review captions before using them as accessibility text. Longer generation limits do not guarantee more accurate detail. This release generates English captions, runs on CPU, and does not include custom model training, an installer executable, automatic recovery, or GPU acceleration.

## Development record

[Progress](docs/PROGRESS.md) · [Design decisions](docs/DECISIONS.md) · [Execution plan](docs/PLAN.md) · [Current status](docs/STATUS.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Progress is recorded in meaningful commits on the actual day of work. Future daily contributions require future work; no history is backdated. To count toward a GitHub profile, commit email must be associated with that account and commits must reach its default branch.

## License

Original LumaCaption code is MIT licensed. Dependencies and model weights retain their own licenses; see the third-party notices.
