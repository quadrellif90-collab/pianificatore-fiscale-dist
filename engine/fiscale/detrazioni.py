"""Detrazioni IRPEF su spese/oneri (port di DetrazioniService.cs)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .models import Contribuente, DetrazioneIrpef


@dataclass
class RisultatoDetrazioni:
    totale_detrazioni: Decimal = Decimal(0)
    detrazioni: list = None

    def __post_init__(self):
        if self.detrazioni is None:
            self.detrazioni = []


class DetrazioniService:
    def __init__(self, regole_service=None):
        self._regole_service = regole_service

    def calcola(self, contribuente: Contribuente, anno: int) -> RisultatoDetrazioni:
        detrazioni: list[DetrazioneIrpef] = []
        regole = self._regole_service.get_regole(anno) if self._regole_service is not None else None

        if contribuente.is_under31 and contribuente.spesa_affitto_annua > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="BONUS_AFFITTO_UNDER_31",
                descrizione="Bonus affitto under 31 (art. 2 D.L. 102/2013)",
                importo_spesa=contribuente.spesa_affitto_annua,
                percentuale_detrazione=Decimal("0.20"),
                limite_massimo=regole.BonusAffittoUnder31 if regole is not None else Decimal(2000),
                is_detraibile_irpef=True,
            ))

        if contribuente.spesa_psicologo_annua > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="BONUS_PSICOLOGO",
                descrizione="Bonus psicologo (art. 1-ter D.L. 4/2021)",
                importo_spesa=contribuente.spesa_psicologo_annua,
                percentuale_detrazione=Decimal("0.19"),
                limite_massimo=regole.BonusPsicologo if regole is not None else Decimal(1500),
                is_detraibile_irpef=True,
            ))

        if contribuente.spese_mediche_annue > 0:
            limite = Decimal("15493.71")
            if regole is not None:
                limite = regole.LimiteSpeseMediche
            detrazioni.append(DetrazioneIrpef(
                codice="SPESE_MEDICHE",
                descrizione="Spese mediche (art. 15 TUIR)",
                importo_spesa=contribuente.spese_mediche_annue,
                percentuale_detrazione=Decimal("0.19"),
                limite_massimo=limite,
                is_detraibile_irpef=True,
            ))

        if contribuente.spese_istruzione_annue > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="SPESE_ISTRUZIONE",
                descrizione="Spese istruzione (art. 15 TUIR)",
                importo_spesa=contribuente.spese_istruzione_annue,
                percentuale_detrazione=Decimal("0.19"),
                limite_massimo=None,
                is_detraibile_irpef=True,
            ))

        if contribuente.spese_sportive_annue > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="SPESE_SPORTIVE",
                descrizione="Spese sportive ragazzi (art. 15 TUIR)",
                importo_spesa=contribuente.spese_sportive_annue,
                percentuale_detrazione=Decimal("0.19"),
                limite_massimo=Decimal(210),
                is_detraibile_irpef=True,
            ))

        if contribuente.erogazioni_liberali_annue > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="EROGAZIONI_LIBERALI",
                descrizione="Erogazioni liberali (art. 15 TUIR)",
                importo_spesa=contribuente.erogazioni_liberali_annue,
                percentuale_detrazione=Decimal("0.19"),
                limite_massimo=None,
                is_detraibile_irpef=True,
            ))

        if contribuente.abbonamenti_tpl_annui > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="ABBONAMENTI_TPL",
                descrizione="Abbonamenti trasporto pubblico (art. 15 TUIR)",
                importo_spesa=contribuente.abbonamenti_tpl_annui,
                percentuale_detrazione=Decimal("0.19"),
                limite_massimo=Decimal(250),
                is_detraibile_irpef=True,
            ))

        if contribuente.spese_ristrutturazione_annue > 0:
            aliquota = Decimal("0.50")
            limite = Decimal(96000)
            if regole is not None:
                aliquota = regole.AliquotaCreditoRistrutturazione2026
                limite = regole.PlafondRistrutturazione2026
            detrazioni.append(DetrazioneIrpef(
                codice="BONUS_RISTRUTTURAZIONE",
                descrizione="Bonus ristrutturazione edilizia (art. 16-bis TUIR)",
                importo_spesa=contribuente.spese_ristrutturazione_annue,
                percentuale_detrazione=aliquota,
                limite_massimo=limite,
                is_detraibile_irpef=False,
            ))

        if contribuente.spese_efficientamento_annue > 0:
            aliquota = Decimal("0.50")
            if regole is not None:
                aliquota = regole.AliquotaCreditoEfficienzaEnergetica2026
            detrazioni.append(DetrazioneIrpef(
                codice="ECOBONUS",
                descrizione="Ecobonus (art. 1 L. 27/2019)",
                importo_spesa=contribuente.spese_efficientamento_annue,
                percentuale_detrazione=aliquota,
                limite_massimo=None,
                is_detraibile_irpef=False,
            ))

        if contribuente.spese_mobili_annue > 0:
            detrazioni.append(DetrazioneIrpef(
                codice="BONUS_MOBILI",
                descrizione="Bonus mobili (art. 16-ter D.L. 63/2013)",
                importo_spesa=contribuente.spese_mobili_annue,
                percentuale_detrazione=Decimal("0.50"),
                limite_massimo=Decimal(5000),
                is_detraibile_irpef=False,
            ))

        totale = sum((d.importo_spesa * d.percentuale_detrazione for d in detrazioni), Decimal(0))
        return RisultatoDetrazioni(totale_detrazioni=totale, detrazioni=detrazioni)
