$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host ""
Write-Host "  PROMO DO GEISSITO" -ForegroundColor Cyan
Write-Host "  Preparando o buscador..." -ForegroundColor Green
Write-Host ""

$pythonCommand = $null

# O Windows pode expor um falso "python.exe" que apenas abre a Microsoft Store.
# Por isso, primeiro validamos cada opção antes de usá-la.
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
    if ($LASTEXITCODE -eq 0) { $pythonCommand = @("py", "-3") }
}

if (-not $pythonCommand) {
    $knownPythons = @(
        (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
        "C:\pinokio\bin\miniconda\python.exe",
        "C:\pinokio\bin\miniforge\python.exe",
        "C:\pinokio\bin\py\env\Scripts\python.exe"
    )
    $pathPython = Get-Command python -ErrorAction SilentlyContinue
    if ($pathPython -and $pathPython.Source -notlike "*\WindowsApps\*") {
        $knownPythons += $pathPython.Source
    }
    foreach ($candidate in $knownPythons) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        & $candidate -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonCommand = @($candidate)
            break
        }
    }
}

if (-not $pythonCommand) {
    throw "Python 3.10 ou superior nao foi encontrado. Instale-o em https://www.python.org/downloads/ e marque 'Add Python to PATH'."
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Primeiro uso: criando o ambiente do programa..." -ForegroundColor Yellow
    if ($pythonCommand.Count -eq 2) {
        & $pythonCommand[0] $pythonCommand[1] -m venv .venv
    } else {
        & $pythonCommand[0] -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente Python." }
}

Write-Host "Conferindo os componentes..." -ForegroundColor Yellow
& $venvPython -m pip install --disable-pip-version-check -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar os componentes. Verifique sua conexao com a internet." }

$env:HOST = "127.0.0.1"
$env:PORT = "7860"
$env:OPEN_BROWSER = "0"
$url = "http://127.0.0.1:7860"
$pidFile = Join-Path $PSScriptRoot ".promo.pid"

function Test-BuscadorAtivo {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $task = $client.ConnectAsync("127.0.0.1", 7860)
        if (-not $task.Wait(400)) { $client.Dispose(); return $false }
        $connected = $client.Connected
        $client.Dispose()
        return $connected
    } catch {
        return $false
    }
}

if (-not (Test-BuscadorAtivo)) {
    $logDir = Join-Path $PSScriptRoot "logs"
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $stdoutLog = Join-Path $logDir "server.out.log"
    $stderrLog = Join-Path $logDir "server.err.log"
    $process = Start-Process -FilePath $venvPython -ArgumentList "app.py" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
    Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

    $ready = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        if (Test-BuscadorAtivo) { $ready = $true; break }
        if ($process.HasExited) {
            $details = if (Test-Path $stderrLog) { (Get-Content $stderrLog -Raw).Trim() } else { "" }
            throw "O buscador encerrou durante a inicializacao. $details"
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "O buscador demorou demais para iniciar." }
}

Write-Host "Buscador pronto. Abrindo o navegador..." -ForegroundColor Green
Start-Process $url

