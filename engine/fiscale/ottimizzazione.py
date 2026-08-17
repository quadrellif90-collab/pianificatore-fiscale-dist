"""Ottimizzazione fiscale: welfare aziendale (port di OttimizzazioneService.cs).

Suggerimento: trasformare parte della retribuzione in welfare aziendale fino a
min(IRPEF lorda * 10%, 2.582,28 €) — art. 51 TUIR, D.L. 34/2019.
"""
from __future__ import annotations

from decimal import Decimal

from .money import round2
from .models import SuggerimentoOttimizzazione


class OttimizzazioneService:
    def analizza(self, c, risultato, regole) -> list:
        suggerimenti: list = []
        if risultato.irpef is not None:
            suggerimenti.extend(self.suggerisci_welfare(risultato.irpef.totale_irpef, regole))
        return suggerimenti

    def suggerisci_welfare(self, totale_irpef: Decimal, regole) -> list[SuggerimentoOttimizzazione]:
        if totale_irpef <= 0:
            return []

        soglia = Decimal("2582.28")
        limite = round2(totale_irpef * Decimal("0.10"))
        importo = min(limite, soglia)

        if importo <= 0:
            return []

        risparmio_irpef = round2(importo * Decimal("0.23"))

        return [SuggerimentoOttimizzazione(
            titolo="Welfare aziendale (art. 51 TUIR, D.L. 34/2019)",
            descrizione=(
                f"Trasformare fino a {importo:.2f} € di retribuzione in welfare aziendale "
                f"(buoni spesa, trasporto, istruzione). Esente da IRPEF e contributi."
            ),
            risparmio_stimato=risparmio_irpef,
            categoria="Welfare",
            difficolta="Media",
            riferimento_normativo="Art. 51 TUIR, D.L. 34/2019",
            richiede_consulente=True,
        )]
