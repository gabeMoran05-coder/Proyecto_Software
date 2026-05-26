Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir "alertas_caducidad.log"

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

Set-Location $ProjectRoot

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Iniciando envio de alertas de caducidad" | Add-Content -Path $LogFile

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose run --rm -T web python manage.py enviar_alertas_caducidad *>> $LogFile
$dockerExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference

if ($dockerExitCode -ne 0) {
    throw "El envio de alertas fallo con codigo $dockerExitCode"
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] Finalizo envio de alertas de caducidad" | Add-Content -Path $LogFile
