# Windows executable build

LC08 builds a portable folder with a windowed desktop launcher and a console launcher.
Keep the whole output folder together. Model weights are downloaded separately.
This is a repeatable pinned recipe; identical binary hashes across rebuilds are not promised.

## Build prerequisites and command

Use Windows x64, CPython 3.11.9, and the existing source environment created by
Setup-Windows.ps1 -Dev. Runtime dependencies must match requirements-lock.txt;
the build adds only the versions in requirements-build.txt. Other Python patch
versions need a separately validated recipe.

From the source project directory:

~~~powershell
.\Build-Windows.ps1 -InstallBuildTools
~~~

Later builds can omit -InstallBuildTools. The script checks every locked version
before running PyInstaller 6.22.3 with hooks 2026.9. It requires at least 3 GiB
free space and writes a local build log. It never deletes old build output.
Choose a new name for another build:

~~~powershell
.\Build-Windows.ps1 -BuildName "LumaCaption-0.1.0-win64-second"
~~~

The default output is dist/LumaCaption-0.1.0-win64/LumaCaption/. It contains:

- LumaCaption.exe: desktop app without a console window.
- LumaCaption-CLI.exe: captions, model setup, and diagnostics in a terminal.
- _internal/: Python, Tk, dependencies, and supporting files. Keep this directory.
- README-Windows.md, LICENSE, THIRD_PARTY_NOTICES.md, and licenses/: usage and notices.
- build-info.json: package versions, build time, source hashes, and bundled-file hashes.

build/ and dist/ are ignored. Do not upload generated executables or logs into the
source repository. No installer, code-signing certificate, or GitHub release is
created by this command. Dependencies retain their own licenses. Notice inventory
entries include build tools; their presence is not a claim that every tool is a
runtime dependency.

## Model setup and cache

Unlike the source launcher, packaged executables default to
%LOCALAPPDATA%\LumaCaption\models. Both launchers honor LUMACAPTION_CACHE.
To reuse the development cache in a PowerShell session:

~~~powershell
$env:LUMACAPTION_CACHE = (Resolve-Path ".cache\models").Path
& ".\dist\LumaCaption-0.1.0-win64\LumaCaption\LumaCaption-CLI.exe" --diagnose
~~~

To create a separate cache on another machine, run LumaCaption-CLI.exe
--download-model while online, then use --offline or the desktop Offline checkbox.
No weights or user photos are included in the build.

## Development-machine verification

1. Run --help and --diagnose on LumaCaption-CLI.exe. Frozen diagnostics starts the
   console sibling with an internal probe flag, never Python's -m command.
2. Run the bundled offline smoke with known local development images, an explicit
   cache, and a fresh report under .local/. For example, from the source root:

~~~powershell
$env:LUMACAPTION_CACHE = (Resolve-Path ".cache\models").Path
$exe = ".\dist\LumaCaption-0.1.0-win64\LumaCaption\LumaCaption-CLI.exe"
& $exe --verify-package "D:\local\photo.jpg" --desktop --report ".local\packaged-smoke.json"
~~~

3. Repeat --verify-package with LumaCaption.exe and a different report path to check
   the windowed bootloader. Use Start-Process -Wait -PassThru when running a GUI
   executable from PowerShell so completion and its exit code are checked.
4. Compare source-image hashes and captions with the source smoke. The embedded
   script blocks HTTP/socket connections, exercises the real Tk caption worker and
   CSV/JSON exports, and disables recovery so verification does not alter user data.
   It creates and withdraws a real Tk window; this is not manual visual acceptance.
5. Keep raw reports/images private and publish only aggregate results in
   [VALIDATION.md](VALIDATION.md). Preserve failed-run evidence rather than overwriting it.

A successful build or a running process alone is not runtime verification.
Missing optional-module warnings in the build log require review against the used
BLIP path. Test actual model loading and generation before calling a package usable.

## Build choices and limits

The [PyInstaller spec](https://pyinstaller.org/en/stable/spec-files.html) shares one
analysis between the two launchers. Transformers source files and explicit BLIP/BERT
imports support its lazy import maps; metadata is retained for dependency checks.
The finalization step removes pip direct_url.json files only inside the generated
bundle, excluding editable-install source URLs before checksums are recorded. The entry point calls freeze_support
before application imports and supplies sink streams in windowed mode, following
[PyInstaller's frozen-process guidance](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html).

The developer evaluation CLI remains a source-environment tool; the packaged app
covers desktop/standard CLI captioning and diagnostics. The package is unsigned.
Clean Windows/VM installation, a machine without the development environment, and
offline restart with a newly downloaded cache belong to LC09. Manual accessibility
and GPU verification remain separate tasks.
