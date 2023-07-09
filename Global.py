import sys, os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running in PyInstaller, assume running in development
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)