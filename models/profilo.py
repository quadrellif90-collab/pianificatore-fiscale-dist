"""Archivio profili contribuente salvati localmente (JSON, nessun account).

Un profilo è un insieme di dati anagrafici + fiscali (nome, tipo contribuente,
redditi, spese, ecc.) salvato in ``profili.json``. Un profilo alla volta è
"attivo" e viene usato come base per i calcoli.
"""
from __future__ import annotations

import json
import os
from decimal import Decimal

from appinfo import get_data_dir

_FILE = "profili.json"


def _path() -> str:
    return os.path.join(get_data_dir(), _FILE)


def _default_dati() -> dict:
    return {
        "nome": "", "cognome": "", "codice_fiscale": "", "data_nascita": "",
        "comune_residenza": "", "provincia_residenza": "",
        "tipo": "PersonaFisica", "regime": "Ordinario",
        "rendita_catastale_imu": 0, "figli_carico": 0, "figli_minori_tre_anni": 0,
        "figli_disabili": 0, "genitore_single": False, "coniuge_carico": False,
        "usa_cedolare_secca": False, "cedolare_concordato": False,
        "numero_immobili_locazione_breve": 0, "numero_mensilita_extra": 0,
        "incremento_retributivo_rinnovo": 0, "premio_produttivita": 0,
        "importo_maggiorazioni_lavoro": 0, "aderisce_bonus_mamme": False,
        "partita_iva": "", "codice_ateco": "", "regime_speciale": "Nessuno",
        "ricavi_compensi_annui": 0, "spese_deducibili_annue": 0,
        "anni_attivita_impresa": 0, "categoria_contributiva": "GestioneSeparata",
        "spese_mediche_annue": 0, "spese_istruzione_annue": 0,
        "spese_ristrutturazione_annue": 0, "spese_efficientamento_annue": 0,
        "spese_mobili_annue": 0, "welfare_annuo": 0,
        "previdenza_complementare_annua": 0, "perdite_pregresse_forfettario": 0,
    }


def _carica_bruto() -> dict:
    try:
        if os.path.exists(_path()):
            with open(_path(), "r", encoding="utf-8") as fh:
                return json.load(fh)
    except (ValueError, OSError):
        pass
    return {"attivo": "", "elenco": {}}


def carica_profili() -> dict:
    """Ritorna {nome: dati} di tutti i profili salvati."""
    bruto = _carica_bruto()
    elenco = bruto.get("elenco", {}) or {}
    return {k: v for k, v in elenco.items()}


def profilo_attivo() -> str:
    return (_carica_bruto().get("attivo") or "").strip()


def profilo_corrente() -> dict:
    """Dati del profilo attivo, o vuoto se nessuno."""
    nome = profilo_attivo()
    if not nome:
        return dict(_default_dati())
    return carica_profili().get(nome, dict(_default_dati()))


def salva_profilo(dati: dict | None = None) -> str:
    """Salva il profilo attivo (creandolo se mancante).
    
    Se ``dati`` è None, usa il profilo corrente in memoria.
    Se non esiste un profilo attivo, ne crea uno nuovo con il nome "Profilo".
    
    Nota: i valori Decimal vengono convertiti in float per la serializzazione JSON.
    """
    nome = profilo_attivo()
    if not nome:
        # Nessun profilo attivo: creiamo "Profilo" di default
        nome = "Profilo"
        crea_profilo(nome)
    if dati:
        # Aggiorna i dati del profilo attivo con quelli forniti
        # Converti Decimal in float per la serializzazione JSON
        dati_conv = {}
        for k, v in dati.items():
            if isinstance(v, Decimal):
                dati_conv[k] = float(v)
            elif isinstance(v, dict):
                dati_conv[k] = {
                    k2: float(v2) if isinstance(v2, Decimal) else v2
                    for k2, v2 in v.items()
                }
            else:
                dati_conv[k] = v
        bruto = _carica_bruto()
        elenco = dict(bruto.get("elenco", {}) or {})
        elenco[nome] = dati_conv
        bruto["elenco"] = elenco
        bruto["attivo"] = nome
        os.makedirs(get_data_dir(), exist_ok=True)
        with open(_path(), "w", encoding="utf-8") as fh:
            json.dump(bruto, fh, ensure_ascii=False, indent=2)
        return _path()
    # Modalità vecchia: salva il profilo corrente con nome attivo
    return _salva_named()


def _salva_named() -> str:
    nome = profilo_attivo()
    if not nome:
        return ""
    dati = _working
    os.makedirs(get_data_dir(), exist_ok=True)
    bruto = _carica_bruto()
    elenco = dict(bruto.get("elenco", {}) or {})
    elenco[nome] = dati
    bruto["elenco"] = elenco
    bruto["attivo"] = nome
    with open(_path(), "w", encoding="utf-8") as fh:
        json.dump(bruto, fh, ensure_ascii=False, indent=2)
    return _path()


def imposta_profilo_attivo(name: str) -> None:
    bruto = _carica_bruto()
    bruto["attivo"] = name
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as fh:
        json.dump(bruto, fh, ensure_ascii=False, indent=2)


def crea_profilo(name: str) -> bool:
    name = (name or "").strip()
    if not name:
        return False
    bruto = _carica_bruto()
    elenco = dict(bruto.get("elenco", {}) or {})
    if name in elenco:
        return False
    elenco[name] = dict(_default_dati())
    bruto["elenco"] = elenco
    bruto["attivo"] = name
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as fh:
        json.dump(bruto, fh, ensure_ascii=False, indent=2)
    return True


def elimina_profilo(name: str) -> None:
    bruto = _carica_bruto()
    elenco = dict(bruto.get("elenco", {}) or {})
    elenco.pop(name, None)
    bruto["elenco"] = elenco
    if bruto.get("attivo") == name:
        bruto["attivo"] = ""
    os.makedirs(get_data_dir(), exist_ok=True)
    with open(_path(), "w", encoding="utf-8") as fh:
        json.dump(bruto, fh, ensure_ascii=False, indent=2)


# --- Stato di lavoro in-memory (impostato dalla vista prima di salvare) ---
_working: dict = {}


def imposta_lavoro(dati: dict) -> None:
    global _working
    _working = dict(dati)


def leggi_lavoro() -> dict:
    return dict(_working)


def carica_profilo() -> dict:
    """Ritorna i dati del profilo attivo (compatibilità con la UI vecchia)."""
    return profilo_corrente()


def _carica_attivo_in_lavoro() -> None:
    global _working
    _working = dict(profilo_corrente())