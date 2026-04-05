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

$backendCommand = @"
Set-Location '$ProjectDir'
& '$CondaBat' run -n $BackendEnv python -m uvicorn backend.main:app --reload --host $BackendHost --port $BackendPort
"@

$frontendCommand = @"
Set-Location '$ProjectDir\frontend'
npm run dev -- --host $FrontendHost --port $FrontendPort
"@

Start-Process powershell -WorkingDirectory $ProjectDir -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null
Start-Process powershell -WorkingDirectory (Join-Path $ProjectDir "frontend") -ArgumentList "-NoExit", "-Command", $frontendCommand | Out-Null

Write-Host "V2 dev mode started."
Write-Host "Backend: http://$BackendHost`:$BackendPort/docs"
Write-Host "Frontend: http://$FrontendHost`:$FrontendPort"
