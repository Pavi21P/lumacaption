param(
    [string]$PythonExe,
    [switch]$Dev,
    [switch]$DownloadModel
)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not $PythonExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $PythonExe = $candidate
            break
        }
    }
    if (-not $PythonExe) {
        $command = Get-Command python -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike "*WindowsApps*") {
            $PythonExe = $command.Source
        }
    }
}
if (-not $PythonExe) {
    throw "Install 64-bit Python 3.11, 3.12, or 3.13 from python.org (including Tcl/Tk), then rerun. Or pass -PythonExe with its full path."
}
& $PythonExe -c "import sys, struct, tkinter; assert (3, 11) <= sys.version_info[:2] < (3, 14) and struct.calcsize('P') == 8, 'Use 64-bit Python 3.11-3.13'"
if ($LASTEXITCODE -ne 0) { throw "Unsupported Python installation or missing Tkinter." }
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}
$runtime = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $runtime -m pip install --use-feature=truststore --upgrade "pip>=24.2"
if ($LASTEXITCODE -ne 0) { throw "Could not update pip. Check your internet connection." }
& $runtime -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
$package = if ($Dev) { ".[dev]" } else { "." }
& $runtime -m pip install -e $package
if ($LASTEXITCODE -ne 0) { throw "LumaCaption installation failed." }
& $runtime -m pip check
if ($LASTEXITCODE -ne 0) { throw "Dependency validation failed." }
$env:LUMACAPTION_CACHE = Join-Path $PSScriptRoot ".cache\models"
if ($DownloadModel) {
    & $runtime -m lumacaption --download-model
    if ($LASTEXITCODE -ne 0) { throw "Model download failed. Retry when online." }
}
Write-Host ""
Write-Host "LumaCaption is ready. Double-click Launch-LumaCaption.cmd."
