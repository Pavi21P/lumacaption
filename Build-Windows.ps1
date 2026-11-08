param(
    [string]$BuildName = "LumaCaption-0.1.0-win64",
    [switch]$InstallBuildTools,
    [switch]$CheckOnly
)
$ErrorActionPreference = "Stop"
if ($CheckOnly -and $InstallBuildTools) {
    throw "-CheckOnly cannot be combined with -InstallBuildTools; no changes were made."
}
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
    $buildArguments = @("scripts/build_windows.py", "--name", $BuildName)
    if ($CheckOnly) { $buildArguments += "--check-only" }
    & $runtime @buildArguments
    if ($LASTEXITCODE -ne 0) {
        if ($CheckOnly) { throw "Build prerequisite check failed. Review the message above." }
        throw "Build failed. Review the message above and any local build log."
    }
} finally {
    Pop-Location
}
