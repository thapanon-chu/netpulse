import pystray
from PIL import Image
import webbrowser
import os

def open_app(icon, item):
    webbrowser.open("http://localhost:8501")

def exit_app(icon, item):
    icon.stop()
    # Note: this won't kill tracker or streamlit, which is fine, they are background services.
    # To fully kill them, the user would need to use Task Manager or a separate kill script.
    os._exit(0)

# Load the icon using absolute path so it never fails regardless of CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(BASE_DIR, "logo.png")
if not os.path.exists(logo_path):
    logo_path = os.path.join(BASE_DIR, "favicon.png")
icon_img = Image.open(logo_path)

# Create Menu
menu = pystray.Menu(
    pystray.MenuItem("Open Dashboard", open_app, default=True),
    pystray.MenuItem("Quit", exit_app)
)

# Create and run the icon
icon = pystray.Icon("NetPulse", icon_img, "NetPulse - Network Usage Tracker", menu)
icon.run()
