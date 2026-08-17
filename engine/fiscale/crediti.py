"""Crediti d'imposta (port di CreditiImpostaService.cs).

I crediti si maturano da spese agevolate (spesa × aliquota del tipo di spesa)
e sono utilizzabili in compensazione se l'anno di maturazione coincide con
l'anno di riferimento e la spesa genera un credito compensabile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .models import CreditoImposta, SpesaDeducibile, TipoCreditoImposta, TipoSpesa


@dataclass
class RisultatoCrediti:
    totale_crediti: Decimal = Decimal(0)
    crediti_compensabili: list = field(default_factory=list)
    crediti: list = field(default_factory=list)


# Mappa tipo spesa -> aliquota credito d'imposta (valori indicativi vigenti)
_ALIQUOTE_SPESE = {
    TipoSpesa.BonusEdilizio: Decimal("0.50"),
    TipoSpesa.RicercaSviluppo: Decimal("0.20"),
    TipoSpesa.InnovazioneTecnologica: Decimal("0.10"),
    TipoSpesa.Formazione40: Decimal("0.40"),
    TipoSpesa.InvestimentiSud: Decimal("0.10"),
    TipoSpesa.EfficienzaEnergetica2026: Decimal("0.50"),
    TipoSpesa.RistrutturazioneEdilizia2026: Decimal("0.50"),
    TipoSpesa.BeniStrumentali: Decimal("0.40"),
    TipoSpesa.Design: Decimal("0.10"),
}


class CreditiImpostaService:
    def __init__(self, regole_service=None):
        self._regole_service = regole_service

    def calcola_crediti_imposta(self, spese: list[SpesaDeducibile], anno: int) -> Decimal:
        crediti = self._maturati_da_spese(spese, anno)
        return sum((c.importo_calcolato for c in crediti), Decimal(0))

    def calcola(self, crediti_input: list[CreditoImposta] | None = None) -> RisultatoCrediti:
        crediti = list(crediti_input or [])
        totale = Decimal(0)
        for c in crediti:
            importo = max(Decimal(0), c.spesa * c.aliquota)
            c.importo_calcolato = importo
            totale += importo
        compensabili = [c for c in crediti if c.is_utilizzabile_in_compensazione]
        return RisultatoCrediti(
            totale_crediti=totale,
            crediti_compensabili=compensabili,
            crediti=crediti,
        )

    def _maturati_da_spese(self, spese: list[SpesaDeducibile], anno: int) -> list[CreditoImposta]:
        crediti: list[CreditoImposta] = []
        for s in spese:
            aliquota = _ALIQUOTE_SPESE.get(s.tipo)
            if aliquota is None:
                continue
            importo = max(Decimal(0), s.importo * aliquota)
            c = CreditoImposta(
                descrizione=s.descrizione,
                importo=importo,
                is_utilizzabile_in_compensazione=True,
                anno_maturazione=anno,
            )
            c.spesa = s.importo
            c.aliquota = aliquota
            c.importo_calcolato = importo
            crediti.append(c)
        return crediti
