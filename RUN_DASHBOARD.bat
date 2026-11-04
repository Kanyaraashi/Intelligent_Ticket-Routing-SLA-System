@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" ( echo [ERROR] Double-click INSTALL.bat first. & pause & exit /b 1 )
call ".venv\Scripts\activate.bat"
if not exist "data\starter.db" if not exist "data\full.db" python scripts/generate_data.py --mode starter

set "DASHBOARD_URL=http://localhost:8501"
echo Stopping any previous copy of this project's dashboard...
for /f "tokens=1" %%P in ('powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"') do taskkill /PID %%P /F >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$cwd=(Get-Location).Path; Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -match 'streamlit run app.py' -and $_.CommandLine -match [regex]::Escape($cwd) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Starting the updated dashboard on port 8501...
start "" powershell -NoProfile -Command "Start-Sleep -Seconds 4; Start-Process '%DASHBOARD_URL%'"
python -m streamlit run app.py --server.port 8501 --server.address localhost --server.fileWatcherType poll
if errorlevel 1 ( echo [ERROR] The dashboard failed to start. & pause & exit /b 1 )
pause
