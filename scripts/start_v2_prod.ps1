param(
    [string]$ProjectDir = "D:\AHEU\GP\MatReflect_NN",
    [string]$BackendEnv = "matreflect",
    [string]$CondaBat = "C:\Users\sfqy\miniconda3\condabin\conda.bat",
    [string]$BackendHost = "127.0.0.1",
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $CondaBat)) {
    $CondaBat = "$env:USERPROFILE\miniconda3\condabin\conda.bat"
}

if (!(Test-Path $CondaBat)) {
    throw "Conda not found. Update -CondaBat to your miniconda3 condabin\\conda.bat path."
}

Push-Location (Join-Path $ProjectDir "frontend")
try {
    npm run build
}
finally {
    Pop-Location
}

Set-Location $ProjectDir
Write-Host "Frontend dist built. Launching backend in production mode..."
Write-Host "App: http://$BackendHost`:$BackendPort"
& $CondaBat run -n $BackendEnv python -m uvicorn backend.main:app --host $BackendHost --port $BackendPort
