@echo off
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
pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Kuch libraries fail hui. pyaudio ke liye try kar raha hoon...
    pip install pipwin && pipwin install pyaudio
)

echo [3/3] JARVIS ka dimaag download kar raha hoon (~2GB, sirf ek baar)...
ollama pull qwen2.5:3b

echo.
echo ================================
echo  Setup ho gaya! Ab JARVIS.bat par double-click karo.
echo ================================
pause
