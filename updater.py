import requests
from VERSION import VERSION

PACKAGE_NAME = "psvmp"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"

def check_for_update():
    """Check PyPI for the latest version"""
    try:
        resp = requests.get(PYPI_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        latest = data["info"]["version"]
        if str(VERSION) < str(latest):
            return (True, latest)   # Update available
        return (False, latest)      # Already up to date
    except Exception as e:
        return (None, str(e))       # Error case
