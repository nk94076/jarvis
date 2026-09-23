@echo off
title JARVIS Rollback
cd /d "%~dp0"
set BACKUP=%USERPROFILE%\JARVIS Data\backups\last
if not exist "%BACKUP%\main.py" (
    echo Koi backup nahi mila. Backup update.bat chalane par banta hai.
    pause
    exit /b 1
)
echo Pichla version wapas la raha hoon (memory safe rahegi)...
robocopy "%BACKUP%" "%~dp0." /E /XD .venv /NFL /NDL /NJH /NJS /NP >nul
python -c "import sys; sys.path.insert(0,'.'); from jarvis import config; print('   Version: v' + config.VERSION)" 2>nul
echo Ho gaya! JARVIS.bat se JARVIS chalao.
pause
