import os, sys

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from daemon_manager import get_python_executables

startup_dir = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
vbs_path = os.path.join(startup_dir, 'NetworkTracker.vbs')

python_exe, pythonw_exe = get_python_executables()
tracker_py = os.path.join(project_dir, 'tracker.py')
tray_py = os.path.join(project_dir, 'tray_app.py')

vbs_content = f'''Set objShell = WScript.CreateObject("WScript.Shell")
objShell.CurrentDirectory = "{project_dir}"

' Run tracker in background
objShell.Run """{pythonw_exe}"" ""{tracker_py}""", 0, False

' Run Streamlit backend silently (headless)
objShell.Run "streamlit run app.py --server.headless true", 0, False

' Run System Tray Icon (with continuous telemetry watchdog)
objShell.Run """{pythonw_exe}"" ""{tray_py}""", 0, False
'''

with open(vbs_path, 'w', encoding='utf-8') as f:
    f.write(vbs_content)

print(f"Successfully updated startup script with full pythonw paths at:\n{vbs_path}")
