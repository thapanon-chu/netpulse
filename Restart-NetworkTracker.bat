@echo off
powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -match 'tracker.py' -or $_.CommandLine -match 'tray_app.py' -or $_.CommandLine -match 'streamlit run app.py' } | ForEach-Object { $_.Terminate() }"
powershell -Command "Start-Sleep -s 2"
start "" wscript.exe "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NetworkTracker.vbs"
echo Network Tracker Restarted Successfully!
pause
