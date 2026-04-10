param(
    [string]$ProjectDir = "D:\AHEU\GP\MatReflect_NN",
    [string]$BackendEnv = "matreflect",
    [string]$CondaBat = "C:\Users\sfqy\miniconda3\condabin\conda.bat",
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [string]$FrontendHost = "127.0.0.1",
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $CondaBat)) {
    $CondaBat = "$env:USERPROFILE\miniconda3\condabin\conda.bat"
}

if (!(Test-Path $CondaBat)) {
    throw "Conda not found. Update -CondaBat to your miniconda3 condabin\\conda.bat path."
}

$occupiedBackendPort = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' } | Select-Object -First 1
if ($occupiedBackendPort) {
    $occupiedProcess = Get-Process -Id $occupiedBackendPort.OwningProcess -ErrorAction SilentlyContinue
    $processLabel = if ($occupiedProcess) { "$($occupiedProcess.ProcessName) (PID $($occupiedBackendPort.OwningProcess))" } else { "PID $($occupiedBackendPort.OwningProcess)" }
    throw "Backend port $BackendPort is already in use by $processLabel. Stop the existing service or run this script with a different -BackendPort."
}

$occupiedFrontendPort = Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' } | Select-Object -First 1
if ($occupiedFrontendPort) {
    $occupiedProcess = Get-Process -Id $occupiedFrontendPort.OwningProcess -ErrorAction SilentlyContinue
    $processLabel = if ($occupiedProcess) { "$($occupiedProcess.ProcessName) (PID $($occupiedFrontendPort.OwningProcess))" } else { "PID $($occupiedFrontendPort.OwningProcess)" }
    throw "Frontend port $FrontendPort is already in use by $processLabel. Stop the existing service or run this script with a different -FrontendPort."
}

$dependencyCheck = & $CondaBat run -n $BackendEnv python -c "import fastapi, uvicorn; print('backend dependency check ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Backend env '$BackendEnv' is missing required packages. Run: conda run -n $BackendEnv python -m pip install -r backend/requirements.txt`n$dependencyCheck"
}

$backendCommand = @"
Set-Location '$ProjectDir'
`$Host.UI.RawUI.WindowTitle = 'MatReflect Backend'
Write-Host 'Starting MatReflect backend...'
Write-Host 'ProjectDir: $ProjectDir'
Write-Host 'URL: http://$BackendHost`:$BackendPort/docs'
& '$CondaBat' run --no-capture-output -n $BackendEnv python -m backend.run_server --reload --host $BackendHost --port $BackendPort
"@

$frontendCommand = @"
Set-Location '$ProjectDir\frontend'
`$Host.UI.RawUI.WindowTitle = 'MatReflect Frontend'
Write-Host 'Starting MatReflect frontend...'
Write-Host 'URL: http://$FrontendHost`:$FrontendPort'
npm run dev -- --host=$FrontendHost --port=$FrontendPort
"@

Start-Process powershell -WorkingDirectory $ProjectDir -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null
Start-Process powershell -WorkingDirectory (Join-Path $ProjectDir "frontend") -ArgumentList "-NoExit", "-Command", $frontendCommand | Out-Null

Write-Host "V2 dev mode started."
Write-Host "Backend: http://$BackendHost`:$BackendPort/docs"
Write-Host "Frontend: http://$FrontendHost`:$FrontendPort"
