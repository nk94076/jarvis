@echo off
title JARVIS Update
cd /d "%~dp0"
set BACKUP=%USERPROFILE%\JARVIS Data\backups\last
echo ================================
echo      JARVIS UPDATE
echo ================================
echo Aapki memory aur settings (JARVIS Data folder) safe rahengi.
echo.
echo [1/4] Backup bana raha hoon: "%BACKUP%"
robocopy "%~dp0." "%BACKUP%" /MIR /XD .venv __pycache__ model /NFL /NDL /NJH /NJS /NP >nul
echo [2/4] Naya version download kar raha hoon...
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$zip = Join-Path $env:TEMP 'jarvis_update.zip'; $dir = Join-Path $env:TEMP 'jarvis_update';" ^
  "Invoke-WebRequest 'https://github.com/nk94076/jarvis/archive/refs/heads/naveen/trusting-wright-m001cv.zip' -OutFile $zip;" ^
  "if (Test-Path $dir) { Remove-Item -Recurse -Force $dir };" ^
  "Expand-Archive -Force $zip $dir;" ^
  "$src = Get-ChildItem $dir | Select-Object -First 1;" ^
  "Copy-Item -Recurse -Force (Join-Path $src.FullName '*') '%~dp0'"
if errorlevel 1 (
    echo [X] Download fail hua. Internet check karke dobara chalao. Purana version waise hi hai.
    pause
    exit /b 1
)
echo [3/4] Nayi libraries check kar raha hoon...
if exist .venv (
    call .venv\Scripts\activate
    for /f "usebackq delims=" %%p in ("requirements.txt") do pip install -q --no-cache-dir %%p
)
echo [4/4] Naye version ka test (regression test)...
python -m jarvis.selftest
if errorlevel 1 (
    echo.
    echo [!] Naya version test mein fail hua. Purana version wapas la raha hoon...
    robocopy "%BACKUP%" "%~dp0." /E /XD .venv /NFL /NDL /NJH /NJS /NP >nul
    echo [OK] Purana version restore ho gaya. Kripya ye screen ka screenshot bhejo.
    pause
    exit /b 1
)
python -c "import sys; sys.path.insert(0,'.'); from jarvis import config; print('   Naya version: v' + config.VERSION)" 2>nul
echo.
echo Ho gaya! JARVIS.bat se JARVIS dobara chalao.
pause
