import os
import sys
import time
import subprocess
import psutil
import platform
import shutil
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'network_data.db')
LOG_FILE = os.path.join(BASE_DIR, 'daemon_manager.log')

def log_event(msg: str):
    """Appends diagnostic events to daemon_manager.log for troubleshooting."""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def get_python_executables():
    """
    Resolves the exact paths to python.exe and pythonw.exe regardless of
    whether invoked from streamlit runner, virtualenv, or subshell.
    """
    # 1. Base prefix (standard Python root)
    if hasattr(sys, 'base_prefix') and sys.base_prefix:
        py_cand = os.path.join(sys.base_prefix, 'python.exe')
        pyw_cand = os.path.join(sys.base_prefix, 'pythonw.exe')
        if os.path.exists(pyw_cand):
            return py_cand, pyw_cand

    # 2. Executable dirname
    exe_dir = os.path.dirname(sys.executable)
    py_cand = os.path.join(exe_dir, 'python.exe')
    pyw_cand = os.path.join(exe_dir, 'pythonw.exe')
    if os.path.exists(pyw_cand):
        return py_cand, pyw_cand

    # 3. Parent of Scripts directory (if sys.executable is in Scripts/)
    parent_dir = os.path.dirname(exe_dir)
    py_cand = os.path.join(parent_dir, 'python.exe')
    pyw_cand = os.path.join(parent_dir, 'pythonw.exe')
    if os.path.exists(pyw_cand):
        return py_cand, pyw_cand

    # 4. PATH lookup fallback
    pyw = shutil.which("pythonw") or shutil.which("python") or sys.executable
    py = shutil.which("python") or sys.executable
    return py, pyw

def is_tracker_running() -> bool:
    """
    Checks if a tracker.py process is currently running.
    Excludes the calling process if it shares the name.
    """
    current_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid:
                continue
            cmd = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmd).lower()
            if 'tracker.py' in cmd_str:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def start_tracker() -> bool:
    """
    Spawns tracker.py as an independent, fully detached background daemon.
    Guarantees no terminal windows flash on Windows.
    """
    if is_tracker_running():
        return True

    py_exe, pyw_exe = get_python_executables()
    tracker_script = os.path.join(BASE_DIR, 'tracker.py')

    log_event(f"Starting tracker via {pyw_exe} -> {tracker_script}")

    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_NO_WINDOW = 0x08000000

    try:
        if platform.system() == 'Windows':
            subprocess.Popen(
                [pyw_exe, tracker_script],
                cwd=BASE_DIR,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
                close_fds=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                [sys.executable, tracker_script],
                cwd=BASE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        # Verification grace window
        time.sleep(0.5)
        alive = is_tracker_running()
        log_event(f"Tracker startup result: alive={alive}")
        return alive
    except Exception as e:
        log_event(f"Failed to start tracker: {e}")
        return False

def ensure_tracker_running() -> bool:
    """
    Fast, idempotent self-healing entry point: checks if tracker is alive,
    and automatically restarts it if missing.
    """
    if is_tracker_running():
        return True
    return start_tracker()

def get_tracker_health() -> dict:
    """
    Returns structured diagnostic health metrics for UI telemetry status panels.
    """
    running = is_tracker_running()
    last_timestamp = None
    seconds_ago = None

    if os.path.exists(DB_FILE):
        try:
            conn = sqlite3.connect(DB_FILE, timeout=2)
            c = conn.cursor()
            row = c.execute("SELECT timestamp FROM bandwidth ORDER BY timestamp DESC LIMIT 1").fetchone()
            conn.close()
            if row:
                last_timestamp = row[0]
                last_dt = time.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")
                seconds_ago = int(time.time() - time.mktime(last_dt))
        except Exception:
            pass

    return {
        "running": running,
        "last_record": last_timestamp,
        "seconds_ago": seconds_ago,
        "healthy": running and (seconds_ago is not None and seconds_ago < 30)
    }

if __name__ == '__main__':
    health = get_tracker_health()
    print("Tracker Health:", health)
    if not health['running']:
        print("Starting tracker...")
        res = ensure_tracker_running()
        print("Start result:", res)
