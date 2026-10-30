@echo off
setlocal
title NetPulse Launcher
cd /d "%~dp0"

:: Check if standalone runtime exists
if exist "runtime\python.exe" (
    set "PYTHON_EXE=%~dp0runtime\python.exe"
    set "STREAMLIT_EXE=%~dp0runtime\python.exe -m streamlit"
) else (
    set "PYTHON_EXE=python"
    set "STREAMLIT_EXE=streamlit"
)

echo Starting NetPulse Telemetry Daemon...
start "NetPulse Tracker" /min %PYTHON_EXE% tracker.py

echo Starting NetPulse Web Dashboard...
start "NetPulse Dashboard" /min %STREAMLIT_EXE% run app.py --server.headless=true --server.port=8501

:: Wait for server initialization then launch browser
timeout /t 3 /nobreak >nul
start "" "http://localhost:8501"

echo NetPulse is active.
echo Dashboard URL: http://localhost:8501
echo To stop services, execute Stop-NetPulse.bat.
timeout /t 3 /nobreak >nul
exit /b 0
