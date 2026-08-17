"""Regimi speciali: forfettario, patent box, ZES unica (port di RegimiSpecialiService.cs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import Contribuente, RegimeFiscale


@dataclass
class CalcoloRegimeSpeciale:
    regime: str = ""
    conveniente: bool = False
    risparmio: Decimal = Decimal(0)
    dettaglio: list = field(default_factory=list)


class RegimiSpecialiService:
    def calcola_regime_forfettario_2026(self, contribuente: Contribuente, ricavi: Decimal, regole) -> CalcoloRegimeSpeciale:
        if contribuente.regime_fiscale == RegimeFiscale.Forfettario:
            return CalcoloRegimeSpeciale(
                regime="FORFETTARIO",
                conveniente=True,
                risparmio=Decimal(0),
            )
        return CalcoloRegimeSpeciale()

    def calcola_patent_box(self, contribuente: Contribuente, reddito_qualificato: Decimal, anno: int, regole) -> CalcoloRegimeSpeciale:
        aliquota = regole.AliquotaPatentBox
        risparmio = round2(reddito_qualificato * aliquota)
        return CalcoloRegimeSpeciale(
            regime="PATENT_BOX",
            conveniente=risparmio > 0,
            risparmio=risparmio,
        )

    def calcola_zes_unica(self, contribuente: Contribuente, investimento: Decimal, regione: str, anno: int, regole) -> CalcoloRegimeSpeciale:
        aliquota = Decimal(0)
        for zes in regole.ZesUnicaAliquote:
            if zes.regione.upper() == (regione or "").upper():
                if investimento < regole.SogliaMinimaInvestimentoZES:
                    aliquota = zes.grandi
                else:
                    aliquota = zes.medie if investimento <= regole.LimiteMassimoInvestimentoZES else zes.piccole
                break

        credito = round2(investimento * aliquota)
        return CalcoloRegimeSpeciale(
            regime="ZES_UNICA",
            conveniente=credito > 0,
            risparmio=credito,
        )
