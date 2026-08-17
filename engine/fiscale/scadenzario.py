"""Scadenzario fiscale (port di ScadenzarioService.cs).

Calendario statico per anno con date tipiche: IVA, 770, INPS, CU, acconti IRES/IRPEF.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from .models import TipoScadenza


@dataclass
class Scadenza:
    data: date
    descrizione: str
    tipo: TipoScadenza = TipoScadenza.Fiscale
    importo: Decimal = Decimal(0)
    saldato: bool = False


class ScadenzarioService:
    def genera(self, anno: int) -> list[Scadenza]:
        scadenze: list[Scadenza] = []

        def aggiungi(mese: int, giorno: int, descrizione: str, tipo: TipoScadenza) -> None:
            try:
                scadenze.append(Scadenza(date(anno, mese, giorno), descrizione, tipo))
            except ValueError:
                pass

        # Fissi mensili/trimestrali IVA
        for mese in range(1, 13):
            aggiungi(mese, 16, f"Liquidazione IVA mese di {_nome_mese(mese - 1)}", TipoScadenza.Iva)

        # CU, 770, IVA annuale, redditi, F24
        aggiungi(1, 31, "Certificazione unica (CU) ai sostituti d'imposta", TipoScadenza.Irpef)
        aggiungi(2, 28, "Invio telematico CU", TipoScadenza.Irpef)
        aggiungi(2, 28, "Liquidazione IVA mese di gennaio (conguaglio)", TipoScadenza.Iva)
        aggiungi(3, 31, "Invio modello 770 enti non commerciali", TipoScadenza.Altro)
        aggiungi(4, 30, "Dichiarazione IVA annuale", TipoScadenza.Iva)
        aggiungi(6, 30, "Versamento saldo IVA da dichiarazione annuale", TipoScadenza.Iva)
        aggiungi(7, 31, "Primo acconto IRPEF/IRES 40%", TipoScadenza.Irpef)
        aggiungi(9, 30, "Modello 770 ordinario", TipoScadenza.Altro)
        aggiungi(11, 30, "Secondo acconto IRPEF/IRES 60%", TipoScadenza.Irpef)
        aggiungi(12, 16, "Liquidazione IVA mese di novembre", TipoScadenza.Iva)

        # Bilancio
        aggiungi(6, 30, "Deposito bilancio d'esercizio (società)", TipoScadenza.Altro)

        scadenze.sort(key=lambda s: s.data)
        return scadenze


def _nome_mese(numero: int) -> str:
    mesi = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
            "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
    if numero < 1:
        numero = 12
    return mesi[numero - 1]
