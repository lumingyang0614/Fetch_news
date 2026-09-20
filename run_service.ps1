param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Continue"
$ProjectRoot = $PSScriptRoot
$StdoutLog = Join-Path $ProjectRoot "service.stdout.log"
$StderrLog = Join-Path $ProjectRoot "service.stderr.log"
$env:PYTHONUNBUFFERED = "1"

if (-not $PythonExe) {
    $PythonExe = Join-Path (Split-Path $ProjectRoot -Parent) "venv_fetch_news\Scripts\python.exe"
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python virtual environment not found: $PythonExe"
}

Set-Location -LiteralPath $ProjectRoot
while ($true) {
    "[$(Get-Date)] Starting Fetch News" | Add-Content -LiteralPath $StdoutLog
    & $PythonExe -m app.main run 1>> $StdoutLog 2>> $StderrLog
    "[$(Get-Date)] Fetch News exited with code $LASTEXITCODE; restarting in 10 seconds" |
        Add-Content -LiteralPath $StderrLog
    Start-Sleep -Seconds 10
}
