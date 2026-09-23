@echo off
title JARVIS Brain Upgrade
cd /d "%~dp0"
echo ==========================================
echo      JARVIS BRAIN UPGRADE  (qwen2.5:14b)
echo ==========================================
echo 16 GB GPU / 16 GB RAM ke liye best smart model.
echo Download lagbhag 9 GB hai, internet ke hisaab se 10-40 minute lagenge.
echo.
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [X] Ollama nahi mila. ollama.com/download se install karo.
    pause
    exit /b 1
)
ollama pull qwen2.5:14b
if errorlevel 1 (
    echo [X] Download fail hua. Internet check karke dobara chalao.
    pause
    exit /b 1
)
echo.
echo Settings mein naya dimaag set kar raha hoon...
if exist .venv call .venv\Scripts\activate
python -c "import sys; sys.path.insert(0,'.'); from jarvis import config; p=config.MY_SETTINGS; t=p.read_text(encoding='utf-8'); lines=[l for l in t.splitlines() if not l.startswith(('OLLAMA_MODEL','AGENT_MODEL'))]; lines += ['OLLAMA_MODEL = \"qwen2.5:14b\"', 'AGENT_MODEL = \"qwen2.5:14b\"']; p.write_text(chr(10).join(lines)+chr(10), encoding='utf-8'); print('   Done:', p)"
echo.
echo ==========================================
echo  Ho gaya! JARVIS.bat se JARVIS dobara chalao.
echo  HUD mein BRAIN: qwen2.5:14b dikhna chahiye.
echo ==========================================
pause
