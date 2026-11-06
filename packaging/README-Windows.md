# LumaCaption for Windows

Keep this entire folder together. Launch LumaCaption.exe for the desktop app.
LumaCaption-CLI.exe provides command-line captions, model setup, and diagnostics.
This portable development build is unsigned. Clean-machine compatibility has not
yet been verified; see the project validation record before distributing it.

## First model setup

The model is downloaded separately and is not included in this folder.
From PowerShell in this folder:

~~~powershell
.\LumaCaption-CLI.exe --download-model
.\LumaCaption-CLI.exe --diagnose
~~~

The default cache is %LOCALAPPDATA%\LumaCaption\models. To reuse another existing
cache, set LUMACAPTION_CACHE before running either launcher. The desktop
Offline checkbox uses cached files only.

~~~powershell
$env:LUMACAPTION_CACHE = "D:\your-model-cache"
.\LumaCaption-CLI.exe --offline "D:\photos\image.jpg" --output "D:\captions.json"
~~~

Sessions and exports are saved where you choose; recovery remains under your
local app-data folder. The executable folder does not contain your photos.

## Verification and notices

build-info.json records pinned package versions, source hashes, and bundled file
hashes. This is a repeatable build recipe, not a guarantee of identical binaries.
LICENSE covers original application code. THIRD_PARTY_NOTICES.md and licenses/
retain dependency notices. Model weights retain the upstream model license.

The developer-only --verify-package command runs the bundled offline verification
script; it is not needed for ordinary use. Full instructions are in docs/PACKAGING.md
in the source repository: https://github.com/Pavi21P/lumacaption.
