@echo off
rem For you: makes AutoEQ Studio's installer, releases\AutoEQ Studio Setup <version>.exe (installs it like any
rem Windows app: Start menu, Windows' list of apps, an uninstaller; for the user running it, no administrator).
rem It holds the program, its own Python and the sample curves, and none of your own files. Needs Inno Setup 6
rem (winget install JRSoftware.InnoSetup --scope user). The version is app\paths.py's VERSION.
setlocal
set "HERE=%~dp0"
cd /d "%HERE%"
title AutoEQ Studio - make the installer
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\AutoEQ Studio\venv\Scripts\python.exe" set "PY=%LOCALAPPDATA%\AutoEQ Studio\venv\Scripts\python.exe"
if not defined PY set "PY=py -3"
%PY% "%HERE%app\tools\make_installer.py"
echo.
pause
