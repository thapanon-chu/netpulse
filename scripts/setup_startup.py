import os

startup_dir = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
vbs_path = os.path.join(startup_dir, 'NetworkTracker.vbs')
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create a VBScript that runs everything in hidden windows
vbs_content = f'''Set objShell = WScript.CreateObject("WScript.Shell")
' Run tracker
objShell.Run "cmd /c cd /d ""{project_dir}"" && python tracker.py", 0, False
' Run Streamlit backend silently (headless)
objShell.Run "cmd /c cd /d ""{project_dir}"" && streamlit run app.py --server.headless true", 0, False
' Run System Tray Icon
objShell.Run "cmd /c cd /d ""{project_dir}"" && pythonw tray_app.py", 0, False
'''

with open(vbs_path, 'w') as f:
    f.write(vbs_content)

print(f"Successfully updated startup script at:\n{vbs_path}")
