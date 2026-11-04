@echo off
setlocal
cd /d "%~dp0"
echo === Installing Ticket Routing project ===
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.11 or 3.12 from https://www.python.org/downloads/
  echo         IMPORTANT: tick "Add python.exe to PATH" in the installer, then run this file again.
  pause & exit /b 1
)
python --version
if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 ( echo [ERROR] Could not create the virtual environment. & pause & exit /b 1 )
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Dependency installation failed. Check your internet connection and run again. & pause & exit /b 1 )
echo.
echo [OK] Installation finished. Next: double-click GENERATE_STARTER_DATA.bat (or RUN_DASHBOARD.bat).
pause
