param(
    [string]$ProjectDir = "",
    [string]$BackendEnv = "matreflect",
    [string]$CondaBat = "",
    [string]$WindowTitle = "MatReflect_NN Desktop",
    [int]$Width = 1600,
    [int]$Height = 1000
)

$ErrorActionPreference = "Stop"

if (-not $ProjectDir) {
    $ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

if ($CondaBat -and !(Test-Path $CondaBat)) {
    $CondaBat = ""
}

if (-not $CondaBat) {
    $condaCandidates = @(
        (Join-Path $env:USERPROFILE "miniconda3\condabin\conda.bat"),
        (Join-Path $env:USERPROFILE "anaconda3\condabin\conda.bat"),
        (Join-Path $env:USERPROFILE "miniforge3\condabin\conda.bat"),
        (Join-Path $env:USERPROFILE "mambaforge\condabin\conda.bat")
    )
    $CondaBat = $condaCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
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

$desktopCheck = Invoke-CondaCommand -Arguments @(
    "run", "-n", $BackendEnv, "python", "-c", "import uvicorn, webview; print('desktop dependency check ok')"
)
if ($desktopCheck.ExitCode -ne 0) {
    Write-Host "Installing desktop dependencies into '$BackendEnv'..."
    $installResult = Invoke-CondaCommand -Arguments @(
        "run", "-n", $BackendEnv, "python", "-m", "pip", "install", "-r", (Join-Path $ProjectDir "desktop\requirements.txt")
    )
    if ($installResult.ExitCode -ne 0) {
        throw "Failed to install desktop dependencies.`n$($desktopCheck.Output)`n$($installResult.Output)"
    }
}

Set-Location $ProjectDir
& $CondaBat run --no-capture-output -n $BackendEnv python desktop\launcher.py --project-root $ProjectDir --title $WindowTitle --width $Width --height $Height
