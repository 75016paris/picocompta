# utils.py
import sys
import os

def resource_path(relative_path):
    """Obtenir le chemin absolu vers les ressources, compatible avec PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)