@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONUTF8=1"
echo Consol let's go > start.log
if exist ".venv\Scripts\python.exe" goto dependencies
where py >nul 2>&1
if errorlevel 1 goto fallback
py -3 -m venv .venv >> start.log 2>&1
if not errorlevel 1 goto dependencies
:fallback
python -m venv .venv >> start.log 2>&1
if errorlevel 1 goto fail
:dependencies
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ required'" >> start.log 2>&1
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "import service" >> start.log 2>&1
if not errorlevel 1 goto launch
echo SQLite is live wait...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt >> start.log 2>&1
if errorlevel 1 goto fail
:launch
".venv\Scripts\python.exe" console.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Could not start. Install Py 3.10+ and read start.log. plz
type start.log
pause
exit /b 1
