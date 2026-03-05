param(
    [string]$ProjectDir = "D:\AHEU\GP\MatReflect_NN",
    [string]$EnvName = "matreflect",
    [string]$CondaHook = "C:\Users\sfqy\miniconda3\shell\condabin\conda-hook.ps1"
)
$ErrorActionPreference = "Stop"
if (!(Test-Path $CondaHook)) {
    $CondaHook = "$env:USERPROFILE\miniconda3\shell\condabin\conda-hook.ps1"
}
& $CondaHook
conda activate $EnvName
Set-Location $ProjectDir
streamlit run app.py
