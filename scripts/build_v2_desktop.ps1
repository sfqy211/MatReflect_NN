param(
    [string]$ProjectDir = "D:\AHEU\GP\MatReflect_NN",
    [string]$BackendEnv = "matreflect",
    [string]$CondaBat = "C:\Users\sfqy\miniconda3\condabin\conda.bat",
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

if (!(Test-Path $CondaBat)) {
    $CondaBat = "$env:USERPROFILE\miniconda3\condabin\conda.bat"
}

if (!(Test-Path $CondaBat)) {
    throw "Conda not found. Update -CondaBat to your miniconda3 condabin\\conda.bat path."
}

function Invoke-CondaCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $CondaBat @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    return [PSCustomObject]@{
        Output = $output.Trim()
        ExitCode = $exitCode
    }
}

Push-Location (Join-Path $ProjectDir "frontend")
try {
    npm run build
}
finally {
    Pop-Location
}

Write-Host "Ensuring desktop packaging dependencies..."
$installResult = Invoke-CondaCommand -Arguments @(
    "run", "-n", $BackendEnv, "python", "-m", "pip", "install", "-r", (Join-Path $ProjectDir "desktop\requirements.txt")
)
if ($installResult.ExitCode -ne 0) {
    throw "Failed to install desktop dependencies.`n$($installResult.Output)"
}

if ($Clean) {
    Remove-Item -LiteralPath (Join-Path $ProjectDir "desktop\build") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath (Join-Path $ProjectDir "desktop\dist") -Recurse -Force -ErrorAction SilentlyContinue
}

Set-Location $ProjectDir
& $CondaBat run --no-capture-output -n $BackendEnv python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath (Join-Path $ProjectDir "desktop\dist") `
    --workpath (Join-Path $ProjectDir "desktop\build") `
    desktop\MatReflectNNDesktop.spec
