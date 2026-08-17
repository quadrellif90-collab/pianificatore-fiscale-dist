"""Configurazione utente dell'app (tema, preferenze) in JSON locale."""
from __future__ import annotations

import json
import os

from appinfo import get_data_dir

_DEFAULT = {
    "tema": "beach",
    "aggiornamento_automatico": True,
    "backup_all_avvio": False,
}


def config_path() -> str:
    return os.path.join(get_data_dir(), "pianificatore_config.json")


def carica_config() -> dict:
    cfg = dict(_DEFAULT)
    try:
        if os.path.exists(config_path()):
            with open(config_path(), "r", encoding="utf-8") as fh:
                cfg.update(json.load(fh))
    except (ValueError, OSError):
        pass
    return cfg


def salva_config(cfg: dict) -> str:
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(config_path(), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    return config_path()
