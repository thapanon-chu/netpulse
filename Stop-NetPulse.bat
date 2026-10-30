@echo off
setlocal
title NetPulse Stopper
echo Stopping all NetPulse background services...

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'tracker.py' -or $_.CommandLine -match 'streamlit run app.py' -or $_.CommandLine -match 'tray_app.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo All NetPulse services have been stopped.
timeout /t 2 /nobreak >nul
exit /b 0
