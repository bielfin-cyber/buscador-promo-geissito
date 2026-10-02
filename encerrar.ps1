$ErrorActionPreference = "SilentlyContinue"
Set-Location -LiteralPath $PSScriptRoot
$pidFile = Join-Path $PSScriptRoot ".promo.pid"
if (Test-Path -LiteralPath $pidFile) {
    $savedPid = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($savedPid -match '^\d+$') {
        $process = Get-Process -Id ([int]$savedPid) -ErrorAction SilentlyContinue
        if ($process) { & taskkill.exe /PID $process.Id /T /F | Out-Null }
    }
    Remove-Item -LiteralPath $pidFile -Force
}
