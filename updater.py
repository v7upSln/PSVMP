import requests
from packaging import version

try:
    from psvmp.VERSION import VERSION
except ImportError:
    from VERSION import VERSION

PACKAGE_NAME = "psvmp"
PYPI_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"

def check_for_update():
    current = str(VERSION)
    try:
        resp = requests.get(PYPI_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        latest = data["info"]["version"]

        if version.parse(current) < version.parse(latest):
            return True, latest  # Update available
        return False, latest  # Up to date
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"
    except Exception as e:
        return None, str(e)