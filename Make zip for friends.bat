@echo off
rem For you: makes the zip to send to friends, in releases\: "AutoEQ Studio <version>.zip" with the installer
rem (AutoEQ Studio Setup <version>.exe: installs it like any Windows app, nothing else needed) and READ ME FIRST.txt
rem (how to install it). None of your own files. It makes the installer first (Make installer.bat's steps: the
rem quick self-test, Inno Setup 6). The version is app\paths.py's VERSION.
setlocal
set "HERE=%~dp0"
cd /d "%HERE%"
title AutoEQ Studio - make a zip for friends
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\AutoEQ Studio\venv\Scripts\python.exe" set "PY=%LOCALAPPDATA%\AutoEQ Studio\venv\Scripts\python.exe"
if not defined PY set "PY=py -3"
%PY% "%HERE%app\tools\make_installer.py" --zip
echo.
pause
