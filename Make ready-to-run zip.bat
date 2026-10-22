@echo off
rem For you, not the testers: makes a ready-to-run zip of AutoEQ Studio (its own Python inside: testers just unzip and start it), in releases\. It holds the
rem program, the sample curves (one IEM and target ready to go) and TESTING.txt, and none of your own files
rem (settings, History, measurements, downloads, output, logs, profiles, the Python environment).
rem (AutoEQ Local's "Make share zip.bat", for this app.)
setlocal
set "HERE=%~dp0"
cd /d "%HERE%"
title AutoEQ Studio - make a ready-to-run zip
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\AutoEQ Studio\venv\Scripts\python.exe" set "PY=%LOCALAPPDATA%\AutoEQ Studio\venv\Scripts\python.exe"
if not defined PY set "PY=py -3"
%PY% "%HERE%app\tools\make_share_zip.py" --ready
echo.
pause
