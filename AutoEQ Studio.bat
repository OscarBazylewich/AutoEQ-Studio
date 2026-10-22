@echo off
rem AutoEQ Studio: sets up its Python packages the first time, then starts the app (its window, and its icon in the
rem tray by the clock). Starting it again while it runs shows the running one's window.
setlocal
rem The folder of this file, taken once before any "cd" (as in AutoEQ Local's launcher).
set "HERE=%~dp0"
cd /d "%HERE%"
title AutoEQ Studio
call "app\setup.bat"
if errorlevel 1 goto :failed

rem Start the app without a console window. If it can't start, it says why in a message box and in data\app.log.
start "" "%VENV%\Scripts\pythonw.exe" "%HERE%app\start.py" %*
exit /b 0

:failed
pause
exit /b 1
