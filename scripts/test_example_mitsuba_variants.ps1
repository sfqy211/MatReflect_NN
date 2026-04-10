param(
    [string[]]$Materials,
    [switch]$SkipMerl,
    [switch]$SkipNbrdf
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sceneDir = Join-Path $projectRoot "scene\dj_xml"
$outputRoot = Join-Path $projectRoot "data\outputs\example_mitsuba_smoke"

$sceneMerl = Join-Path $sceneDir "scene_test_merl_accelerated.xml"
$sceneNbrdf = Join-Path $sceneDir "scene_test_nbrdf_npy.xml"

$variants = @(
    @{
        Name = "mitsuba-master_my_copy"
        Exe = "D:\AHEU\GP\03_Hyper-SNBRDF_mitsuba eval\mitsuba\mitsuba-master_my_copy\mitsuba-master\dist\mitsuba.exe"
    },
    @{
        Name = "mitsuba-master_my_sine_21_GT"
        Exe = "D:\AHEU\GP\03_Hyper-SNBRDF_mitsuba eval\mitsuba\mitsuba-master_my_sine_21_GT\mitsuba-master\dist\mitsuba.exe"
    },
    @{
        Name = "mitsuba-master_my_testing3"
        Exe = "D:\AHEU\GP\03_Hyper-SNBRDF_mitsuba eval\mitsuba\mitsuba-master_my_testing3\mitsuba-master\dist\mitsuba.exe"
    },
    @{
        Name = "mitsuba-master_SNBRDF_21_GT_7_28"
        Exe = "D:\AHEU\GP\03_Hyper-SNBRDF_mitsuba eval\mitsuba\mitsuba-master_SNBRDF_21_GT_7_28\mitsuba-master\dist\mitsuba.exe"
    }
)

function Get-AllTestableMaterials {
    $binaryDir = Join-Path $projectRoot "data\inputs\binary"
    $npyDir = Join-Path $projectRoot "data\inputs\npy"

    $binaryNames = @{}
    Get-ChildItem $binaryDir -Filter *.binary -File | ForEach-Object {
        $binaryNames[$_.BaseName] = $true
    }

    $npyNames = @{}
    Get-ChildItem $npyDir -Filter *_fc1.npy -File | ForEach-Object {
        $name = $_.BaseName
        if ($name.EndsWith("_fc1")) {
            $name = $name.Substring(0, $name.Length - 4)
        }
        $npyNames[$name] = $true
    }

    $all = @()
    foreach ($name in $binaryNames.Keys) {
        if ($npyNames.ContainsKey($name)) {
            $all += $name
        }
    }

    return $all | Sort-Object
}

if (-not $Materials -or $Materials.Count -eq 0) {
    $Materials = Get-AllTestableMaterials
}

if (-not $Materials -or $Materials.Count -eq 0) {
    throw "No testable materials found. Expected matching files in data\\inputs\\binary and data\\inputs\\npy."
}

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

function Invoke-MitsubaRender {
    param(
        [string]$Exe,
        [string]$VariantName,
        [string]$ScenePath,
        [string[]]$ArgsExtra,
        [string]$OutputPng
    )

    $distDir = Split-Path $Exe -Parent
    $logPath = [System.IO.Path]::ChangeExtension($OutputPng, ".log")

    $argList = @($ScenePath, "-o", $OutputPng) + $ArgsExtra

    Write-Host ""
    Write-Host "=== $VariantName ==="
    Write-Host $Exe
    Write-Host ($argList -join " ")

    Push-Location $distDir
    try {
        & $Exe @argList 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    [PSCustomObject]@{
        Variant = $VariantName
        Output = $OutputPng
        Log = $logPath
        ExitCode = $exitCode
        OutputExists = Test-Path $OutputPng
    }
}

function Test-MaterialInputs {
    param(
        [string]$MaterialName
    )

    $binaryPath = Join-Path $projectRoot ("data\inputs\binary\{0}.binary" -f $MaterialName)
    $nnBase = Join-Path $projectRoot ("data\inputs\npy\{0}_" -f $MaterialName)

    if (-not (Test-Path $binaryPath)) {
        throw "Missing binary material: $binaryPath"
    }

    if (-not (Test-Path ($nnBase + "fc1.npy"))) {
        throw "Missing NBRDF weights: $($nnBase + 'fc1.npy')"
    }

    return @{
        BinaryPath = $binaryPath
        NnBase = $nnBase
    }
}

$results = @()

foreach ($material in $Materials) {
    $inputs = Test-MaterialInputs -MaterialName $material
    $binaryPath = $inputs.BinaryPath
    $nnBase = $inputs.NnBase

    foreach ($variant in $variants) {
        if (-not (Test-Path $variant.Exe)) {
            $results += [PSCustomObject]@{
                Material = $material
                Variant = $variant.Name
                Output = ""
                Log = ""
                ExitCode = -1
                OutputExists = $false
                Note = "mitsuba.exe not found"
            }
            continue
        }

        $variantOutDir = Join-Path (Join-Path $outputRoot $material) $variant.Name
        New-Item -ItemType Directory -Force -Path $variantOutDir | Out-Null

        if (-not $SkipMerl) {
            $merlOut = Join-Path $variantOutDir ("{0}_merl_accelerated.png" -f $material)
            $merlResult = Invoke-MitsubaRender `
                -Exe $variant.Exe `
                -VariantName ($variant.Name + " | " + $material + " | MERL") `
                -ScenePath $sceneMerl `
                -ArgsExtra @("-Dbrdf_dir=$binaryPath") `
                -OutputPng $merlOut
            $merlResult | Add-Member -NotePropertyName Material -NotePropertyValue $material
            $results += $merlResult
        }

        if (-not $SkipNbrdf) {
            $nbrdfOut = Join-Path $variantOutDir ("{0}_nbrdf_npy.png" -f $material)
            $nbrdfResult = Invoke-MitsubaRender `
                -Exe $variant.Exe `
                -VariantName ($variant.Name + " | " + $material + " | NBRDF") `
                -ScenePath $sceneNbrdf `
                -ArgsExtra @("-Dnn_base=$nnBase") `
                -OutputPng $nbrdfOut
            $nbrdfResult | Add-Member -NotePropertyName Material -NotePropertyValue $material
            $results += $nbrdfResult
        }
    }
}

Write-Host ""
Write-Host "=== Summary ==="
$results | Format-Table Material, Variant, ExitCode, OutputExists, Output -AutoSize
