@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if %errorlevel% equ 0 (
  uv venv .venv --python 3.12
  if errorlevel 1 exit /b 1
  uv pip install --python .venv\Scripts\python.exe -r requirements.txt
) else (
  py -3.12 -m venv .venv
  if errorlevel 1 exit /b 1
  .venv\Scripts\python.exe -m pip install -r requirements.txt
)
if errorlevel 1 exit /b 1
echo Ready. Start ComfyUI, then run "Start Director's Cut.bat".
pause
