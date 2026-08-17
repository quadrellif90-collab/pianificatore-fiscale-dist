"""Imposte società: IRES e IRAP (port di SocietaCalculators.cs).

IRES: lorda = utile fiscale × 24%; si utilizzano i crediti compensabili maturati
nell'esercizio; netta = max(0, lorda − crediti); acconto = 90% della netta;
saldo = netta (imposte correnti, art. 6 D.P.R. 97/1973).
IRAP: base = valore della produzione (ricavi − costi − ammortamenti) ridotta
della deduzione per costo del personale (15.000 €/addetto, art. 11 D.Lgs. 446/97).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import BilancioSocieta, CreditoImposta


@dataclass
class CalcoloIres:
    reddito_imponibile: Decimal = Decimal(0)
    aliquota_ires: Decimal = Decimal("0.24")
    ires_lorda: Decimal = Decimal(0)
    crediti_imposta: Decimal = Decimal(0)
    ires_netta: Decimal = Decimal(0)
    acconto_ires: Decimal = Decimal(0)
    saldo_ires: Decimal = Decimal(0)
    crediti_utilizzati: list = field(default_factory=list)


class IresCalculator:
    def calcola(self, bilancio: BilancioSocieta, crediti: list[CreditoImposta] | None = None,
                regole=None) -> CalcoloIres:
        crediti = crediti or []
        aliquota = regole.AliquotaIres if regole is not None else Decimal("0.24")
        reddito = bilancio.utile_perdita_ante_imposte

        crediti_utilizzabili = [
            c for c in crediti
            if c.is_utilizzabile_in_compensazione and c.anno_maturazione == bilancio.anno
        ]
        importo_crediti = sum((c.importo_calcolato or Decimal(0) for c in crediti_utilizzabili), Decimal(0))

        lorda = reddito * aliquota
        netta = max(Decimal(0), lorda - importo_crediti)

        return CalcoloIres(
            reddito_imponibile=reddito,
            aliquota_ires=aliquota,
            ires_lorda=round2(lorda),
            crediti_imposta=round2(importo_crediti),
            ires_netta=round2(netta),
            acconto_ires=round2(netta * Decimal("0.90")),
            saldo_ires=round2(netta),
            crediti_utilizzati=crediti_utilizzabili,
        )


@dataclass
class CalcoloIrap:
    base_imponibile: Decimal = Decimal(0)
    aliquota_standard: Decimal = Decimal("0.039")
    aliquota_regionale: Decimal = Decimal(0)
    irap_lorda: Decimal = Decimal(0)
    deduzioni_personale: Decimal = Decimal(0)
    irap_netta: Decimal = Decimal(0)
    acconto_irap: Decimal = Decimal(0)
    saldo_irap: Decimal = Decimal(0)


class IrapCalculator:
    def calcola(self, bilancio: BilancioSocieta, redditi: list | None = None,
                regole=None) -> CalcoloIrap:
        aliquota = regole.AliquotaIrapBase if regole is not None else Decimal("0.039")
        deduzione_personale = (
            regole.DeduzioneIrapPersonaleUnitario
            if regole is not None else Decimal(15000)
        )

        costo_personale = bilancio.costo_personale
        deduzione = min(costo_personale, deduzione_personale)

        base = (
            bilancio.ricavi_vendite
            - bilancio.costi_produzione
            - bilancio.ammortamenti
            - (costo_personale - deduzione)
        )
        base = max(Decimal(0), base)

        lorda = base * aliquota

        return CalcoloIrap(
            base_imponibile=base,
            aliquota_standard=aliquota,
            irap_lorda=round2(lorda),
            deduzioni_personale=round2(deduzione),
            irap_netta=round2(lorda),
            acconto_irap=round2(lorda * Decimal("0.90")),
            saldo_irap=round2(lorda),
        )
