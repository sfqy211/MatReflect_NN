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

$occupiedPort = Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' } | Select-Object -First 1
if ($occupiedPort) {
    $occupiedProcess = Get-Process -Id $occupiedPort.OwningProcess -ErrorAction SilentlyContinue
    $processLabel = if ($occupiedProcess) { "$($occupiedProcess.ProcessName) (PID $($occupiedPort.OwningProcess))" } else { "PID $($occupiedPort.OwningProcess)" }
    throw "Backend port $BackendPort is already in use by $processLabel. Stop the existing service or run this script with a different -BackendPort."
}

$dependencyCheck = & $CondaBat run -n $BackendEnv python -c "import fastapi, uvicorn; print('backend dependency check ok')" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Backend env '$BackendEnv' is missing required packages. Run: conda run -n $BackendEnv python -m pip install -r backend/requirements.txt`n$dependencyCheck"
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
