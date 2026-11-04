@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] The virtual environment is missing. Double-click INSTALL.bat first.
  pause & exit /b 1
)
call ".venv\Scripts\activate.bat"
echo === Generating FULL data (30,000 tickets - takes 2-5 minutes) ===
python scripts/generate_data.py --mode full
if errorlevel 1 (
  echo.
  echo [ERROR] The step above failed. Read the message above, fix it, and run this file again.
  pause & exit /b 1
)
echo.
echo [OK] Finished.
pause
