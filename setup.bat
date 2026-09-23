@echo off
setlocal EnableDelayedExpansion
title JARVIS Setup
cd /d "%~dp0"
echo ================================
echo        JARVIS SETUP
echo ================================

python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python nahi mila. python.org se Python 3.12 install karo
    echo     aur "Add python.exe to PATH" tick karna mat bhoolna.
    pause
    exit /b 1
)

ollama --version >nul 2>&1
if errorlevel 1 (
    echo [X] Ollama nahi mila. ollama.com/download se install karo, phir ye file dobara chalao.
    pause
    exit /b 1
)

echo [1/3] Virtual environment bana raha hoon...
if not exist .venv python -m venv .venv
call .venv\Scripts\activate

echo [2/3] Libraries install kar raha hoon (kuch minute lagenge)...
python -m pip install --upgrade pip
pip cache purge >nul 2>&1
rem Har library alag se, taaki ek fail ho to baaki ruk na jaayein
set FAILED=
for /f "usebackq delims=" %%p in ("requirements.txt") do (
    echo     - %%p
    pip install -q --no-cache-dir %%p
    if errorlevel 1 set FAILED=!FAILED! %%p
)
if defined FAILED (
    echo.
    echo [!] Ye install nahi hui:!FAILED!
    echo     Internet check karke setup.bat dobara chalao.
)

echo Check kar raha hoon...
python -c "import pyttsx3, speech_recognition, sounddevice, psutil, ollama; print('    [OK] Zaroori libraries ready hain')"

echo [3/3] JARVIS ka dimaag download kar raha hoon (~2GB, sirf ek baar)...
ollama pull qwen2.5:3b

echo.
echo ================================
echo  Setup ho gaya! Ab JARVIS.bat par double-click karo.
echo ================================
pause
