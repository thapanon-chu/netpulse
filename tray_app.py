import pystray
from PIL import Image
import webbrowser
import os
import sys
import time
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from daemon_manager import ensure_tracker_running, is_tracker_running

def open_app(icon, item):
    ensure_tracker_running()
    webbrowser.open("http://localhost:8501")

def restart_tracker_action(icon, item):
    ensure_tracker_running()

def exit_app(icon, item):
    icon.stop()
    os._exit(0)

# Continuous Background Watchdog:
# Silently verifies every 30 seconds that the telemetry daemon is healthy.
# If tracker stopped due to OS sleep/wake, crash, or manual termination, auto-resurrects it.
def _watchdog_loop():
    time.sleep(2)
    ensure_tracker_running()
    while True:
        try:
            time.sleep(30)
            ensure_tracker_running()
        except Exception:
            pass

watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
watchdog_thread.start()

# Load the icon using absolute path so it never fails regardless of CWD
logo_candidates = [
    os.path.join(BASE_DIR, "assets", "logo.png"),
    os.path.join(BASE_DIR, "logo.png"),
    os.path.join(BASE_DIR, "assets", "favicon.png"),
    os.path.join(BASE_DIR, "favicon.png"),
]
logo_path = next((p for p in logo_candidates if os.path.exists(p)), None)
icon_img = Image.open(logo_path) if logo_path else Image.new("RGB", (64, 64), color=(30, 41, 59))

# Create Menu
menu = pystray.Menu(
    pystray.MenuItem("Open Dashboard", open_app, default=True),
    pystray.MenuItem("Verify Telemetry Daemon", restart_tracker_action),
    pystray.MenuItem("Quit", exit_app)
)

# Create and run the icon
icon = pystray.Icon("NetPulse", icon_img, "NetPulse - Network Usage Tracker", menu)
icon.run()
