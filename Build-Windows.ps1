param(
    [string]$BuildName = "LumaCaption-0.1.0-win64",
    [switch]$InstallBuildTools
)
$ErrorActionPreference = "Stop"
$runtime = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $runtime)) {
    throw "Run Setup-Windows.ps1 -Dev first."
}
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($InstallBuildTools) {
        & $runtime -m pip --disable-pip-version-check install -r requirements-build.txt
        if ($LASTEXITCODE -ne 0) { throw "Build-tool installation failed." }
    }
    & $runtime scripts/build_windows.py --name $BuildName
    if ($LASTEXITCODE -ne 0) { throw "Build failed. Review the local build log." }
} finally {
    Pop-Location
}
