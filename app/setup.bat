@echo off
rem (copied from AutoEQ Local's app\setup.bat: each app ships on its own)
rem Sets up (or repairs) the Python packages AutoEQ Studio needs. The launcher in the main folder calls this; it tells
rem them where the Python environment is (VENV). First run: finds a 64-bit Python 3.10 or newer, makes the environment
rem and installs the packages (the exact versions in requirements.txt, or if this Python has none of those, the
rem newest that work, from requirements-any.txt). Later runs: nothing to do unless requirements.txt changed or the
rem environment broke (e.g. its Python was removed or upgraded), then it's set up again. Details: data\setup.log.
setlocal
rem The folder of this file, taken once before any "cd": %~dp0 of a file started by a relative path is worked
rem out again from the current folder each time, which is wrong after a "cd".
set "APPDIR=%~dp0"
cd /d "%APPDIR%"
for %%I in ("%APPDIR%..") do set "ROOT=%%~fI\"
if not exist "%ROOT%data" mkdir "%ROOT%data"
set "LOG=%ROOT%data\setup.log"
set "AEQ_ROOT=%ROOT%"
set "AEQ_LOG=%LOG%"

rem Where the environment goes: .venv in the main folder, or %LOCALAPPDATA% when the app is in OneDrive (syncing
rem thousands of package files slows setup and can lock them) or in a folder with a long path (Windows' 260-character
rem limit breaks the install: Qt's deepest package file is 175 characters below the main folder, so a main folder
rem over 80 characters is too long). An existing .venv is kept where it is.
set "VENV=%ROOT%.venv"
if exist "%ROOT%.venv\Scripts\python.exe" goto :check
set "AWAY="
if not "%ROOT:~80,1%"=="" set "AWAY=1"
if not "%ROOT:OneDrive=%"=="%ROOT%" set "AWAY=1"
if defined AWAY if defined LOCALAPPDATA set "VENV=%LOCALAPPDATA%\AutoEQ Studio\venv"

:check
if not exist "%VENV%\Scripts\python.exe" goto :install
"%VENV%\Scripts\python.exe" -c "import sys" >nul 2>nul
if errorlevel 1 goto :rebuild
if not exist "%VENV%\requirements.installed" goto :install
fc /b "requirements.txt" "%VENV%\requirements.installed" >nul 2>nul
if errorlevel 1 goto :install
goto :ready

:rebuild
echo The app's Python environment no longer works (was Python removed or upgraded?): setting it up again.
>>"%LOG%" echo %date% %time% environment broken: rebuilding "%VENV%"
rmdir /s /q "%VENV%" >nul 2>nul

:install
echo Setting up Python packages. This takes a minute or two and only happens once.
echo.
>>"%LOG%" echo ==== %date% %time% setup in "%ROOT%" (environment "%VENV%")
if exist "%VENV%\Scripts\python.exe" goto :packages
rem files from a downloaded zip are marked as coming from the internet: unmark them, so Windows stops asking about each one
powershell -NoProfile -Command "Get-ChildItem -LiteralPath $env:AEQ_ROOT -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue" >nul 2>nul
set "PY="
for %%C in ("py -3-64" "py -3" "python" "python3") do if not defined PY call :try %%~C
>>"%LOG%" echo Python found: %SEEN%   using: %PY% %PYVER%
if not defined PY goto :nopython
echo Using %PYVER%
if not "%VENV%"=="%ROOT%.venv" echo Its packages go in "%VENV%" (this folder is in OneDrive, or its path is long).
%PY% -m venv "%VENV%" >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

:packages
echo Downloading and installing Qt, numpy, scipy, mini-racer, sounddevice and the rest (about 150 MB)...
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt >>"%LOG%" 2>&1
if not errorlevel 1 goto :installed
echo The exact package versions aren't available for this Python: installing the newest ones that are.
>>"%LOG%" echo -- the pinned versions failed: trying requirements-any.txt
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-any.txt >>"%LOG%" 2>&1
if errorlevel 1 goto :failed

:installed
copy /y "requirements.txt" "%VENV%\requirements.installed" >nul
>>"%LOG%" echo setup done
echo Done.
echo.

:ready
endlocal & set "VENV=%VENV%"
exit /b 0

rem a Python the app can use: 3.10 or newer, 64-bit (Qt and the maths packages have no 32-bit version for Windows)
:try
set "FOUND="
for /f "delims=" %%V in ('%* -c "import sys, struct; print('{}.{} {}-bit'.format(sys.version_info[0], sys.version_info[1], struct.calcsize('P') * 8))" 2^>nul') do set "FOUND=%%V"
if not defined FOUND exit /b 0
if not defined SEEN set "SEEN=%FOUND% (%*)"
%* -c "import sys, struct; sys.exit(0 if sys.version_info >= (3, 10) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 exit /b 0
set "PY=%*"
set "PYVER=Python %FOUND%"
exit /b 0

:nopython
echo.
if defined SEEN echo Found Python %SEEN%, but AutoEQ Studio needs 64-bit Python 3.10 or newer.
if not defined SEEN echo Python wasn't found.
echo Install the latest Python from https://www.python.org/downloads/ (the Windows installer, 64-bit),
echo or run: winget install Python.Python.3.13
echo then run AutoEQ Studio again.
endlocal
exit /b 1

:failed
echo.
echo Setup failed. The last lines of data\setup.log:
echo.
powershell -NoProfile -Command "Get-Content -LiteralPath $env:AEQ_LOG -Tail 12" 2>nul
echo.
echo Check the internet connection (the packages are downloaded once) and try again. If it keeps failing,
echo send data\setup.log to whoever gave you AutoEQ Studio.
endlocal
exit /b 1
