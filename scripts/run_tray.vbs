Set objFSO = CreateObject("Scripting.FileSystemObject")
strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strProjectDir = objFSO.GetParentFolderName(strScriptDir)

Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = strProjectDir
objShell.Run "pythonw tray_app.py", 0, False
