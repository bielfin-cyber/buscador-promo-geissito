$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Execute INICIAR.bat pelo menos uma vez antes da verificacao."
}
& $venvPython -m unittest -v test_core.py
if ($LASTEXITCODE -ne 0) { throw "Os testes locais falharam." }
& $venvPython smoke_test_live.py
if ($LASTEXITCODE -ne 0) { throw "O teste ao vivo falhou." }
Write-Host "Todos os testes foram concluidos." -ForegroundColor Green

