"""Regime forfettario (port di ForfettarioCalculator.cs e ForfettarioPrecisioneService.cs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import CalcoloForfettarioPrecisione, Contribuente, RegimeSpeciale, TipoReddito


@dataclass
class CalcoloForfettario:
    reddito_imponibile: Decimal = Decimal(0)
    coefficiente_applicato: Decimal = Decimal(0)
    imposta_sostitutiva: Decimal = Decimal(0)
    contributi_dovuti: Decimal = Decimal(0)
    ritenute_subite: Decimal = Decimal(0)
    imposta_netta: Decimal = Decimal(0)
    dettaglio_operazioni: list = field(default_factory=list)


class ForfettarioCalculator:
    def calcola(self, contribuente: Contribuente, redditi, regole) -> CalcoloForfettario:
        imponibile = sum((r.importo_lordo for r in redditi), Decimal(0))
        coefficiente = regole.CoefficienteRedditivitaForfettario

        reddito_imponibile = imponibile * coefficiente

        aliquota = regole.AliquotaForfettario
        if _is_startup(contribuente):
            aliquota = regole.AliquotaForfettarioStartup

        imposta = reddito_imponibile * aliquota

        contributi = reddito_imponibile * regole.AliquotaContributiForfettario

        return CalcoloForfettario(
            reddito_imponibile=round2(reddito_imponibile),
            coefficiente_applicato=coefficiente,
            imposta_sostitutiva=round2(imposta),
            contributi_dovuti=round2(contributi),
            ritenute_subite=sum((r.ritenute_subite for r in redditi), Decimal(0)),
            imposta_netta=round2(imposta),
        )


class ForfettarioPrecisioneService:
    def __init__(self, tax_rule_service=None):
        self._tax_rule_service = tax_rule_service
        self._coefficienti_ateco: dict = {}

    def calcola(self, contribuente: Contribuente, anno: int) -> CalcoloForfettarioPrecisione:
        coefficiente = self._get_coefficiente(contribuente.codice_ateco, anno)
        da_tabella = coefficiente is not None
        if coefficiente is None:
            regole = self._tax_rule_service.get_regole(anno) if self._tax_rule_service else None
            coefficiente = (
                regole.CoefficienteRedditivitaForfettario
                if regole is not None else Decimal("0.78")
            )

        regole = self._tax_rule_service.get_regole(anno) if self._tax_rule_service else None

        ricavi = contribuente.ricavi_compensi_annui
        spese = contribuente.spese_deducibili_annue

        reddito_lordo = max(Decimal(0), ricavi - spese) * coefficiente

        imponibile_contributivo = max(Decimal(0), reddito_lordo)

        aliquota_contributi = regole.AliquotaContributiForfettario if regole is not None else Decimal("0.25")
        contributi = round2(imponibile_contributivo * aliquota_contributi)

        perdite_pregresse = contribuente.perdite_pregresse_forfettario or Decimal(0)
        perdite = min(perdite_pregresse, reddito_lordo)
        perdite_residue = max(Decimal(0), perdite_pregresse - perdite)
        reddito_netto = max(Decimal(0), reddito_lordo - perdite)

        aliquota = regole.AliquotaForfettario if regole is not None else Decimal("0.15")
        if _is_startup(contribuente):
            aliquota = regole.AliquotaForfettarioStartup if regole is not None else Decimal("0.05")

        imposta = round2(reddito_netto * aliquota)
        saldo = round2(imposta * Decimal("0.80"))
        acconto = round2(imposta * Decimal("0.80"))

        ricavi = Decimal(ricavi)
        incidenza = (imposta / ricavi) if ricavi > 0 else Decimal(0)

        return CalcoloForfettarioPrecisione(
            codice_ateco=contribuente.codice_ateco or "",
            settore="",
            coefficiente_applicato=coefficiente,
            coefficiente_da_tabella=da_tabella,
            ricavi=ricavi,
            reddito_imponibile=round2(reddito_lordo),
            aliquota_imposta=aliquota,
            anni_nuova_attivita=contribuente.anni_attivita_impresa,
            contributi_totali=contributi,
            contributi_deducibili=contributi,
            contributi_eccedenza=Decimal(0),
            contributi_minimo=Decimal(0),
            percentuale_riduzione_contributi=Decimal(0),
            riduzione_contributi=Decimal(0),
            reddito_imponibile_netto=round2(reddito_netto),
            imposta_sostitutiva=imposta,
            perdite_utilizzate=perdite,
            perdite_residue=perdite_residue,
            contributi_eccedenza_non_dedotti=Decimal(0),
            quota_contributi_rate_fisse=Decimal(0),
            quota_contributi_saldo_acconti=acconto + saldo,
            totale_versare=round2(saldo + acconto + contributi),
            carico_fiscale_totale=round2(imposta + contributi),
            incidenza_totale=round2(incidenza),
            fuoriuscita_immediata=False,
        )

    def _get_coefficiente(self, codice_ateco: str, anno: int) -> Decimal | None:
        if not codice_ateco:
            return None
        self._load_coefficienti(anno)
        tabella = self._coefficienti_ateco.get(anno) or {}
        return tabella.get(codice_ateco)

    def _load_coefficienti(self, anno: int) -> None:
        if anno in self._coefficienti_ateco:
            return
        import json
        import os

        regole_dir = os.path.join(os.path.dirname(__file__), "TaxRules")
        file_path = os.path.join(regole_dir, f"ateco_coefficienti_{anno}.json")
        tabella: dict = {}
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for codice, valore in (data.get("CoefficientiAteco") or {}).items():
                    tabella[codice] = Decimal(str(valore))
            except Exception:
                pass
        self._coefficienti_ateco[anno] = tabella


def _is_startup(contribuente: Contribuente) -> bool:
    return (
        contribuente.regime_speciale
        in (RegimeSpeciale.StartupInnovativa, RegimeSpeciale.StartupInnovativa2026,
            RegimeSpeciale.RegimeForfettario2026)
        and contribuente.eta() <= 35
        and contribuente.anni_attivita_impresa <= 5
    )

