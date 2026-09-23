@echo off
title J.A.R.V.I.S.
cd /d "%~dp0"
if not exist .venv (
    echo Pehle setup.bat chalao.
    pause
    exit /b 1
)
call .venv\Scripts\activate
python main.py %*
if errorlevel 1 pause
