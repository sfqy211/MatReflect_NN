@echo off
setlocal
set "PROJECT_DIR=D:\AHEU\GP\MatReflect_NN"
set "ENV_NAME=matreflect"
if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
  call "%USERPROFILE%\miniconda3\Scripts\activate.bat" %ENV_NAME%
) else (
  call "%USERPROFILE%\miniconda3\condabin\conda.bat" activate %ENV_NAME%
)
cd /d "%PROJECT_DIR%"
echo Legacy V1 launcher: web terminal has been removed. Use V2 by default; keep this entry only for migration checks or legacy compile-helper workflows.
streamlit run app.py
endlocal
