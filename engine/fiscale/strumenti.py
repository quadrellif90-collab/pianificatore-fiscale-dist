"""Strumenti di risparmio: welfare e previdenza complementare (port di StrumentiRisparmioService.cs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import Contribuente


@dataclass
class RisultatoWelfare:
    totale_welfare: Decimal = Decimal(0)
    soglia_figli: Decimal = Decimal(0)
    soglia_standard: Decimal = Decimal(0)
    reddito: Decimal = Decimal(0)
    dettaglio: list = field(default_factory=list)


@dataclass
class RisultatoPrevidenza:
    versamenti: Decimal = Decimal(0)
    limite: Decimal = Decimal(0)
    risparmio_fiscale: Decimal = Decimal(0)
    dettaglio: list = field(default_factory=list)


class StrumentiRisparmioService:
    def __init__(self, regole_service=None):
        self._regole_service = regole_service

    def calcola_welfare(self, contribuente: Contribuente, anno: int) -> RisultatoWelfare:
        regole = self._regole_service.get_regole(anno) if self._regole_service else None

        usaLegge2025 = regole is not None and regole.Anno >= 2025 and regole.SogliaWelfareStandard2025 > 0

        soglia_standard = Decimal(258.23)
        if usaLegge2025:
            soglia_standard = regole.SogliaWelfareStandard2025
            if contribuente.figli_carico > 0:
                soglia_standard += regole.SogliaWelfareFigliAnnua

        reddito = contribuente.reddito_complessivo_ultimo_anno
        welfare = contribuente.welfare_annuo or Decimal(0)

        limite = max(soglia_standard, welfare * Decimal("0.05"))
        totale = min(welfare, limite)

        return RisultatoWelfare(
            totale_welfare=round2(totale),
            soglia_figli=round2(regole.SogliaWelfareFigliAnnua if usaLegge2025 else Decimal(0)),
            soglia_standard=round2(soglia_standard),
            reddito=reddito,
        )

    def calcola_previdenza(self, contribuente: Contribuente, anno: int) -> RisultatoPrevidenza:
        regole = self._regole_service.get_regole(anno) if self._regole_service else None
        limite = regole.LimitePrevidenzaComplementareMax if regole is not None else Decimal("5164.57")
        versamenti = contribuente.previdenza_complementare_annua or Decimal(0)
        versamenti_effettivi = min(versamenti, limite)
        risparmio = round2(versamenti_effettivi * Decimal("0.23"))
        return RisultatoPrevidenza(
            versamenti=versamenti,
            limite=round2(limite),
            risparmio_fiscale=risparmio,
        )
