"""Percorsi dati di PianificatoreFiscale.

Se accanto all'eseguibile esiste una cartella ``data`` (modalità portabile),
i dati vengono salvati lì; altrimenti in ``~/PianificatoreFiscale``.
"""
import os
import sys


def get_app_dir() -> str:
    """Cartella dell'eseguibile/script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """Cartella dove salvare profilo e config (portabile o utente)."""
    app_dir = get_app_dir()
    portable = os.path.join(app_dir, "data")
    if os.path.isdir(portable):
        return portable
    user = os.path.join(os.path.expanduser("~"), "PianificatoreFiscale")
    os.makedirs(user, exist_ok=True)
    return user


DB_FILE = ""
CONFIG_FILE = "pianificatore_config.json"
BACKUP_DIR = "backups"
