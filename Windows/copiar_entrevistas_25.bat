@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Vista previa (no modifica nada) ===
python copiar_entrevistas_25.py --dry-run
echo.
choice /M "Copiar estos clips al bin destino? (el bin tiene que estar cerrado en Avid)"
if errorlevel 2 goto fin
python copiar_entrevistas_25.py
:fin
echo.
pause
