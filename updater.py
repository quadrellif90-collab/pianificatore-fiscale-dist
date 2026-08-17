"""
PianificatoreFiscale - Updater esterno dedicato.

Scarica l'ultima release da GitHub e sostituisce l'eseguibile mentre
l'applicazione è chiusa. Pensato per essere lanciato dall'app stessa
(pulsante "Aggiorna") o manualmente.

Uso:
    python updater.py                # aggiorna l'app nella stessa cartella
    python updater.py --check        # solo controllo versione (exit 0=ok,1=disponibile)

Il repository e l'asset atteso sono configurabili sotto.
"""
import os
import sys
import json
import time
import shutil
import argparse

try:
    import urllib.request
    import urllib.error
    import ssl
    try:
        import certifi
        _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        _SSL_CTX = None
    _HAVE_URLLIB = True
except Exception:
    _HAVE_URLLIB = False
    _SSL_CTX = None

# Configurazione: repo pubblico di distribuzione (leggibile senza token)
DIST_REPO = "quadrellif90-collab/pianificatore-fiscale-dist"
UPDATE_JSON_URL = f"https://raw.githubusercontent.com/{DIST_REPO}/main/update.json"
ASSET_NAME = "PianificatoreFiscale.exe"   # nome dell'eseguibile

APP_NAME = "PianificatoreFiscale"


def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _current_version():
    """Legge la versione corrente da version.txt se presente."""
    p = os.path.join(_app_dir(), "version.txt")
    if os.path.exists(p):
        try:
            return open(p, "r", encoding="utf-8").read().strip()
        except OSError:
            return ""
    return ""


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
    ctx = _SSL_CTX if _SSL_CTX is not None else ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def get_latest():
    """Ritorna (versione, download_url) dal file update.json pubblico.

    Il file è hostato su un repo pubblico, quindi leggibile senza token.
    Ritorna (None, None) in caso di errore rete.
    """
    if not _HAVE_URLLIB:
        return None, None
    try:
        data = _fetch_json(UPDATE_JSON_URL)
    except Exception:
        return None, None
    win = data.get("windows", {})
    ver = data.get("version", "")
    url = win.get("release_url", "")
    return ver, url


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
    ctx = _SSL_CTX if _SSL_CTX is not None else ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        with open(dest, "wb") as f:
            shutil.copyfileobj(r, f)


def check_only():
    tag, _ = get_latest()
    cur = _current_version()
    if not tag:
        print("Impossibile contattare GitHub.")
        return 1
    if tag and tag != cur:
        print(f"Aggiornamento disponibile: {cur or '?'} -> {tag}")
        return 1
    print(f"Sei aggiornato ({cur or tag}).")
    return 0


def update():
    tag, url = get_latest()
    cur = _current_version()
    if not tag or not url:
        print("Nessun aggiornamento disponibile o errore di rete.")
        return 1
    if tag == cur:
        print(f"Già aggiornato ({cur}).")
        return 0

    print(f"Aggiornamento {cur or '?'} -> {tag} ...")
    dest_dir = _app_dir()
    target = os.path.join(dest_dir, ASSET_NAME)
    tmp = os.path.join(dest_dir, ASSET_NAME + ".new")

    # backup dell'eseguibile attuale
    backup = os.path.join(dest_dir, ASSET_NAME + ".bak")
    if os.path.exists(target):
        shutil.copy2(target, backup)

    _download(url, tmp)

    # sostituisce
    if os.path.exists(target):
        os.remove(target)
    os.rename(tmp, target)

    # salva la nuova versione
    with open(os.path.join(dest_dir, "version.txt"), "w", encoding="utf-8") as f:
        f.write(tag)

    print(f"Aggiornamento completato alla versione {tag}.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="solo controllo")
    args = ap.parse_args()
    if args.check:
        sys.exit(check_only())
    sys.exit(update())


if __name__ == "__main__":
    main()
