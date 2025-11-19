import os

# Default configuration
DEFAULT_CONFIG = {
    "vita_ip": "192.168.1.7",
    "vita_port": 1337,
    "video_path": "ux0:/video/shows/",
    "music_path": "ux0:/music/",
    "max_retries": 5,
    "retry_delay": 3
}

USER_DOCS = os.path.join(os.path.expanduser("~"), "Documents")
BASE_DOCS_DIR = os.path.join(USER_DOCS, "PSvita media processer")

TEMP_FOLDER = os.path.join(BASE_DOCS_DIR, "temp")
CONVERTED_FOLDER = os.path.join(BASE_DOCS_DIR, "converted")

# AppData/Local/PSVMP   on Windows
if os.name == 'nt':  # Windows
    PSVMP_DIR = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'PSVMP')
else:  # Linux/macOS
    PSVMP_DIR = os.path.join(os.path.expanduser('~'), '.local', 'share', 'PSVMP')

LOG_FOLDER = os.path.join(PSVMP_DIR, "logs")
HISTORY_FILE = os.path.join(PSVMP_DIR, "history.log")

DEFAULT_VITA_IP = DEFAULT_CONFIG["vita_ip"]
DEFAULT_VITA_PORT = DEFAULT_CONFIG["vita_port"]
VITA_VIDEO_PATH = DEFAULT_CONFIG["video_path"]
VITA_MUSIC_PATH = DEFAULT_CONFIG["music_path"]
MAX_RETRIES = DEFAULT_CONFIG["max_retries"]
RETRY_DELAY = DEFAULT_CONFIG["retry_delay"]

os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
os.makedirs(PSVMP_DIR, exist_ok=True)