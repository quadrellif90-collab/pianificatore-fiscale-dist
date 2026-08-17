"""Regole fiscali annuali: dati di default (RegolaFiscale), FakeTaxRuleService
per i test (parità golden truth) e TaxRuleService che carica i JSON annuali.

Port di TaxPlanner Italia (RegolaFiscale, FakeTaxRuleService, TaxRuleService).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from .models import (
    AddizionaleComunale,
    AddizionaleRegionale,
    ScaglioneIrpef,
    ZesAliquota2026,
)

_TAXRULES_DIR_DEFAULT = os.path.join(os.path.dirname(__file__), "TaxRules")


def _base_dir() -> str:
    """Directory di lavoro: cartella TaxRules del pacchetto (dev o PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, "engine", "fiscale", "TaxRules")
    return _TAXRULES_DIR_DEFAULT


def _as_dec(value) -> Decimal:
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class RegolaFiscale:
    """Modello delle regole fiscali di un anno (default identici al C#)."""

    def __init__(self, anno: int = 2026):
        self.Anno = anno
        self.ScaglioniIrpef: List[ScaglioneIrpef] = []
        self.NoTaxAreaLavoroDipendente = Decimal(8500)
        self.NoTaxAreaPensione = Decimal(8500)
        self.DetrazioneLavoroDipendenteMax = Decimal(1910)
        self.DetrazioneConiugeCaricoMax = Decimal(800)
        self.DetrazioneFigliCaricoBase = Decimal(950)
        self.DetrazioneFigliCaricoMaggiorazione = Decimal(200)
        self.SoglieRedditoFigli: List[Decimal] = [Decimal(4000), Decimal(2840), Decimal(0)]
        self.AliquotaIres = Decimal("0.24")
        self.AliquotaIrapBase = Decimal("0.039")
        self.DeduzioneIrapPersonaleUnitario = Decimal(15000)
        self.LimiteForfettarioRicavi = Decimal(85000)
        self.CoefficienteRedditivitaForfettario = Decimal("0.78")
        self.AliquotaForfettario = Decimal("0.15")
        self.AliquotaForfettarioStartup = Decimal("0.05")

        self.EsoneroContributiSoglie: List[Decimal] = [Decimal(25000), Decimal(35000)]
        self.EsoneroContributiAliquote: List[Decimal] = [Decimal("0.07"), Decimal("0.06")]

        self.CuneoBonusSoglie: List[Decimal] = [Decimal(8500), Decimal(15000), Decimal(20000)]
        self.CuneoBonusAliquote: List[Decimal] = [Decimal("0.071"), Decimal("0.053"), Decimal("0.048")]
        self.CuneoUlterioreDetrazioneMax = Decimal(1000)
        self.CuneoUlterioreDetrazioneSogliaMin = Decimal(20000)
        self.CuneoUlterioreDetrazioneSogliaPiena = Decimal(32000)
        self.CuneoUlterioreDetrazioneSogliaMax = Decimal(40000)

        self.TrattamentoIntegrativoBase = Decimal(1200)
        self.TrattamentoIntegrativoSogliaMin = Decimal(15000)
        self.TrattamentoIntegrativoSogliaMax = Decimal(28000)

        self.AliquotaGestioneSeparata = Decimal("0.2607")
        self.AliquotaContributiArtigianiCommercianti = Decimal("0.24")
        self.AliquotaContributiForfettario = Decimal("0.25")

        self.DetrazionePensioneMax = Decimal(1955)
        self.DetrazionePensioneMinimo = Decimal(713)
        self.DetrazionePensioneBaseSecondaFascia = Decimal(700)
        self.DetrazionePensioneIncrementoSecondaFascia = Decimal(1255)
        self.SogliaPensioneSecondaFascia = Decimal(28000)
        self.SogliaPensioneTerzaFascia = Decimal(50000)
        self.BonusDetrazionePensione25_29 = Decimal(50)
        self.SogliaBonusDetrazionePensioneMin = Decimal(25000)
        self.SogliaBonusDetrazionePensioneMax = Decimal(29000)

        self.AliquotaUtilizzoPerditeForfettario = Decimal("0.80")
        self.AliquotaContributiDipendente = Decimal("0.0919")
        self.AliquotaContributiDipendentePubblico = Decimal("0.0880")
        self.AliquotaContributiDipendenteApprendista = Decimal("0.0584")

        self.LimiteRimborsoSmartWorkingMensile = Decimal(10)
        self.PercentualeAutoAziendale = Decimal("0.30")
        self.PercentualeAutoAziendaleElettrica = Decimal("0.10")
        self.EsenzioneImpatriatiPercentuale = Decimal("0.70")

        self.LimitePrevidenzaComplementareMax = Decimal("5164.57")
        self.SogliaWelfareStandardAnnua = Decimal("258.23")
        self.SogliaWelfareFigliAnnua = Decimal(2000)
        self.SogliaWelfareRedditoMax = Decimal(35000)
        self.SogliaWelfareStandard2025 = Decimal(1000)

        self.AliquotaCedolareSecca = Decimal("0.21")
        self.AliquotaCedolareSeccaConcordato = Decimal("0.10")
        self.AliquotaCedolareSeccaLocazioneBreve = Decimal("0.26")
        self.SogliaImmobiliPresunzioneImprenditorialita = 2
        self.CoefficienteImuRendita = Decimal("1.1667")
        self.AddizionaliRegionali: Dict[str, AddizionaleRegionale] = {}
        self.AddizionaliComunali: Dict[str, AddizionaleComunale] = {}
        self.DetrazioniStandard: List = []
        self.CreditiImpostaDisponibili: List = []
        self.UltimoAggiornamento: Optional[date] = None
        self.Fonte: str = ""

        self.DetrazioneLavoroPrimaFascia = Decimal(1955)
        self.DetrazioneLavoroBonus25_35 = Decimal(65)
        self.SogliaSterilizzazioneReddito = Decimal(200000)
        self.SterilizzazioneDetrazioniImporto = Decimal(440)

        self.AliquotaFlatTaxIncrementoRetributivo = Decimal("0.05")
        self.SogliaReddito2025FlatTaxRinnovi = Decimal(33000)
        self.AliquotaImpostaSostitutivaPremiProduttivita = Decimal("0.01")
        self.LimitePremiProduttivita = Decimal(5000)
        self.AliquotaImpostaSostitutivaMaggiorazioni = Decimal("0.15")
        self.LimiteMaggiorazioni = Decimal(1500)
        self.SogliaReddito2025Maggiorazioni = Decimal(40000)

        self.BonusMammeIntegrazioneMensile = Decimal(60)
        self.SogliaRedditoBonusMamme = Decimal(40000)
        self.SogliaBuoniPastoElettronici = Decimal(10)
        self.SogliaBuoniPastoCartacei = Decimal(4)

        self.AliquotaPlusvalenzeCripto = Decimal("0.26")
        self.AliquotaPlusvalenzeCriptoDal2026 = Decimal("0.33")
        self.SogliaPlusvalenzaCripto = Decimal(2000)

        self.AliquotaContributiDatore = Decimal("0.2381")
        self.AliquotaTfr = Decimal("0.0691")

        self.SogliaQuozienteFamiliareMax = Decimal(100000)
        self.SogliaQuozienteFamiliareMin = Decimal(0)
        self.BaseQuozienteFamiliareSotto75_100 = Decimal(0)
        self.BaseQuozienteFamiliareOltre100 = Decimal(0)
        self.QuozienteFamiliareCoefficienti: List[Decimal] = [Decimal(0)] * 4
        self.SogliaDecalageQuoziente = Decimal(120000)
        self.DecalageQuozienteMassimo = Decimal(240000)
        self.SogliaSterilizzazioneQuoziente = Decimal(200000)
        self.SterilizzazioneQuozienteImporto = Decimal(440)

        self.BonusAffittoUnder31 = Decimal(2000)
        self.BonusPsicologo = Decimal(1500)
        self.BonusMobilitaSostenibile = Decimal(0)
        self.AliquotaCreditoFormazione40 = Decimal(0)
        self.AliquotaCreditoRistrutturazione2026 = Decimal("0.50")
        self.AliquotaCreditoRistrutturazione2026Altre = Decimal("0.36")
        self.PlafondRistrutturazione2026 = Decimal(96000)
        self.AliquotaCreditoEfficienzaEnergetica2026 = Decimal("0.50")
        self.AliquotaCreditoEfficienzaEnergetica2026Altre = Decimal("0.36")
        self.AliquotaCreditoRS = Decimal("0.10")
        self.AliquotaCreditoBeniStrumentali = Decimal(0)
        self.AliquotaPatentBox = Decimal("0.30")
        self.AliquotaZESUnica = Decimal(0)
        self.ZesUnicaAliquote: List[ZesAliquota2026] = _zes_default()
        self.SogliaMinimaInvestimentoZES = Decimal(200000)
        self.LimiteMassimoInvestimentoZES = Decimal(100000000)
        self.AliquotaConcordatoPreventivo = Decimal("0.15")
        self.LimiteEsoneroUnder36 = Decimal(3000)
        self.IncentivoDonnePerUnita = Decimal(6000)
        self.DecontribuzioneDonne2026 = Decimal(0)
        self.IncentivoCIGS_NASpI = Decimal("0.50")
        self.IncentivoOver50 = Decimal("0.50")
        self.IncentivoApprendistato = Decimal(1.00)
        self.IncentivoZES = Decimal(0)

        self.LimiteSpeseMediche = Decimal("15493.71")
        self.LimiteCreditoRS = Decimal(5000000)
        self.LimiteCreditoFormazione40 = Decimal(300000)

        self.Iperammortamento2026Scaglione1 = Decimal(2500000)
        self.Iperammortamento2026Scaglione2 = Decimal(10000000)
        self.Iperammortamento2026Scaglione3 = Decimal(20000000)
        self.Iperammortamento2026Coefficiente1 = Decimal("2.80")
        self.Iperammortamento2026Coefficiente2 = Decimal(2.00)
        self.Iperammortamento2026Coefficiente3 = Decimal("1.50")

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _zes_default() -> List[ZesAliquota2026]:
    raw = [
        ("CALABRIA", 0.40, 0.50, 0.60), ("CAMPANIA", 0.40, 0.50, 0.60),
        ("PUGLIA", 0.40, 0.50, 0.60), ("SICILIA", 0.40, 0.50, 0.60),
        ("BASILICATA", 0.30, 0.40, 0.50), ("MOLISE", 0.30, 0.40, 0.50),
        ("SARDEGNA", 0.30, 0.40, 0.50), ("ABRUZZO", 0.15, 0.25, 0.35),
        ("TARANTO", 0.50, 0.60, 0.70), ("SULCIS", 0.50, 0.60, 0.70),
    ]
    return [
        ZesAliquota2026(regione=r, grandi=_as_dec(g), medie=_as_dec(m), piccole=_as_dec(p))
        for r, g, m, p in raw
    ]


class FakeTaxRuleService:
    """Regole deterministiche di test (parità con TestHelpers.cs).

    Rispecchia esattamente CreaRegole(int anno) dei test C#: aliquote 23/35/43
    (33% dal 2026), no-tax area 8.500, detrazione lavoro 1.880 (2024) / 1.955
    (2025+), bonus +65€ tra 25-35k (2025+), addizionali default 0,0123/0,002.
    """

    def __init__(self, anno: int = 2025):
        self._regole_per_anno: Dict[int, RegolaFiscale] = {}
        for a in (2024, 2025, 2026):
            self._regole_per_anno[a] = self._crea_regole(a)
        if anno not in (2024, 2025, 2026):
            self._regole_per_anno[anno] = self._crea_regole(anno)

    def _crea_regole(self, anno: int) -> RegolaFiscale:
        r = RegolaFiscale(anno)
        seconda_aliquota = Decimal("0.33") if anno >= 2026 else Decimal("0.35")
        r.ScaglioniIrpef = [
            ScaglioneIrpef(Decimal(0), Decimal(28000), Decimal("0.23"), Decimal(0)),
            ScaglioneIrpef(Decimal(28000), Decimal(50000), seconda_aliquota, Decimal(3360)),
            ScaglioneIrpef(Decimal(50000), None, Decimal("0.43"), Decimal(10360)),
        ]
        r.NoTaxAreaLavoroDipendente = Decimal(8500)
        r.DetrazioneLavoroDipendenteMax = Decimal(1910)
        r.DetrazioneLavoroPrimaFascia = Decimal(1955) if anno >= 2025 else Decimal(1880)
        r.DetrazioneLavoroBonus25_35 = Decimal(65) if anno >= 2025 else Decimal(0)
        r.NoTaxAreaPensione = Decimal(8500)
        r.DetrazionePensioneMax = Decimal(1955)
        r.DetrazionePensioneMinimo = Decimal(713)
        r.DetrazionePensioneBaseSecondaFascia = Decimal(700)
        r.DetrazionePensioneIncrementoSecondaFascia = Decimal(1255)
        r.SogliaPensioneSecondaFascia = Decimal(28000)
        r.SogliaPensioneTerzaFascia = Decimal(50000)
        r.BonusDetrazionePensione25_29 = Decimal(50)
        r.SogliaBonusDetrazionePensioneMin = Decimal(25000)
        r.SogliaBonusDetrazionePensioneMax = Decimal(29000)
        r.SogliaSterilizzazioneReddito = Decimal(200000) if anno >= 2026 else Decimal(0)
        r.SterilizzazioneDetrazioniImporto = Decimal(440)
        r.AliquotaCedolareSeccaLocazioneBreve = Decimal("0.26")
        r.SogliaImmobiliPresunzioneImprenditorialita = 2 if anno >= 2026 else 4
        r.AliquotaFlatTaxIncrementoRetributivo = Decimal("0.05")
        r.SogliaReddito2025FlatTaxRinnovi = Decimal(33000)
        r.AliquotaImpostaSostitutivaPremiProduttivita = Decimal("0.01")
        r.LimitePremiProduttivita = Decimal(5000)
        r.AliquotaImpostaSostitutivaMaggiorazioni = Decimal("0.15")
        r.LimiteMaggiorazioni = Decimal(1500)
        r.SogliaReddito2025Maggiorazioni = Decimal(40000)
        r.BonusMammeIntegrazioneMensile = Decimal(60)
        r.SogliaRedditoBonusMamme = Decimal(40000)
        r.AliquotaPlusvalenzeCripto = Decimal("0.26")
        r.AliquotaPlusvalenzeCriptoDal2026 = Decimal("0.33") if anno >= 2026 else Decimal(0)
        r.SogliaPlusvalenzaCripto = Decimal(2000) if anno <= 2024 else Decimal(0)
        r.AliquotaIres = Decimal("0.24")
        r.AliquotaIrapBase = Decimal("0.039")
        r.DeduzioneIrapPersonaleUnitario = Decimal(15000)
        r.LimiteForfettarioRicavi = Decimal(85000)
        r.CoefficienteRedditivitaForfettario = Decimal("0.78")
        r.AliquotaForfettario = Decimal("0.15")
        r.EsoneroContributiSoglie = [Decimal(25000), Decimal(35000)]
        r.EsoneroContributiAliquote = [Decimal("0.07"), Decimal("0.06")]
        r.CuneoBonusSoglie = [Decimal(8500), Decimal(15000), Decimal(20000)]
        r.CuneoBonusAliquote = [Decimal("0.071"), Decimal("0.053"), Decimal("0.048")]
        r.CuneoUlterioreDetrazioneMax = Decimal(1000)
        r.CuneoUlterioreDetrazioneSogliaMin = Decimal(20000)
        r.CuneoUlterioreDetrazioneSogliaPiena = Decimal(32000)
        r.CuneoUlterioreDetrazioneSogliaMax = Decimal(40000)
        r.TrattamentoIntegrativoBase = Decimal(1200)
        r.TrattamentoIntegrativoSogliaMin = Decimal(15000)
        r.TrattamentoIntegrativoSogliaMax = Decimal(28000)
        r.AliquotaContributiDipendente = Decimal("0.0919")
        r.AliquotaContributiDipendentePubblico = Decimal("0.0880")
        r.AliquotaContributiDipendenteApprendista = Decimal("0.0584")
        r.LimiteRimborsoSmartWorkingMensile = Decimal(10)
        r.PercentualeAutoAziendale = Decimal("0.30")
        r.PercentualeAutoAziendaleElettrica = Decimal("0.10")
        r.EsenzioneImpatriatiPercentuale = Decimal("0.70")
        r.AliquotaGestioneSeparata = Decimal("0.2607")
        r.AliquotaContributiForfettario = Decimal("0.25")
        r.LimitePrevidenzaComplementareMax = Decimal(5300)
        r.SogliaWelfareStandardAnnua = Decimal("258.23")
        r.SogliaWelfareFigliAnnua = Decimal(2000)
        r.SogliaWelfareRedditoMax = Decimal(35000)
        r.SogliaWelfareStandard2025 = Decimal(1000)
        r.AliquotaCedolareSecca = Decimal("0.21")
        r.AliquotaCedolareSeccaConcordato = Decimal("0.10")
        r.CoefficienteImuRendita = Decimal("1.1667")
        r.AddizionaliRegionali = {
            "Default": AddizionaleRegionale("Default", Decimal("0.0123"), [], [])
        }
        r.AddizionaliComunali = {
            "Default": AddizionaleComunale("Default", "", Decimal("0.002"))
        }
        return r

    def get_regole(self, anno: int) -> RegolaFiscale:
        if anno not in self._regole_per_anno:
            self._regole_per_anno[anno] = self._crea_regole(anno)
        return self._regole_per_anno[anno]

    def get_anni_disponibili(self) -> List[int]:
        return list(self._regole_per_anno.keys())


class TaxRuleService:
    """Carica le regole fiscali annuali dai JSON (fallback anno più recente).

    Port di TaxRuleService.cs: cache, file tax_rules_{anno}.json, fusione
    dell'archivio addizionali comunali e allineamento gestione separata dal file ATECO.
    """

    def __init__(self, rules_directory: Optional[str] = None):
        self._rules_directory = rules_directory or _base_dir()
        self._cache: Dict[int, RegolaFiscale] = {}
        if not os.path.isdir(self._rules_directory):
            os.makedirs(self._rules_directory, exist_ok=True)

    def get_regole(self, anno: int) -> RegolaFiscale:
        if anno in self._cache:
            return self._cache[anno]

        regole = self._carica_da_file(anno)
        if regole is None:
            for anno_disponibile in sorted(self.get_anni_disponibili(), reverse=True):
                regole = self._carica_da_file(anno_disponibile)
                if regole is not None:
                    regole.Anno = anno
                    break

        if regole is None:
            regole = RegolaFiscale(anno)
        self._fonde_addizionali_comunali(regole)
        self._allinea_contributi_inps_da_ateco(regole, anno)
        self._cache[anno] = regole
        return regole

    def _carica_da_file(self, anno: int) -> Optional[RegolaFiscale]:
        file_path = os.path.join(self._rules_directory, f"tax_rules_{anno}.json")
        if not os.path.isfile(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _regola_da_dict(data, anno)
        except Exception:
            return None

    def _fonde_addizionali_comunali(self, regole: RegolaFiscale) -> None:
        file_path = os.path.join(self._rules_directory, "addizionali_comunali.json")
        if not os.path.isfile(file_path):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        dataset = _regola_da_dict(data, regole.Anno)
        if not dataset.AddizionaliComunali:
            return
        for chiave, valore in dataset.AddizionaliComunali.items():
            if chiave == "Default":
                continue
            esistente = regole.AddizionaliComunali.get(chiave)
            codice = (
                esistente.codice_catastale
                if (not valore.codice_catastale and esistente is not None)
                else valore.codice_catastale
            )
            regole.AddizionaliComunali[chiave] = AddizionaleComunale(
                comune=valore.comune or chiave,
                codice_catastale=codice,
                aliquota=valore.aliquota,
                soglia_esenzione=valore.soglia_esenzione,
                scaglioni=valore.scaglioni,
                aliquote=valore.aliquote,
            )

    def _allinea_contributi_inps_da_ateco(self, regole: RegolaFiscale, anno: int) -> None:
        file_path = os.path.join(self._rules_directory, f"ateco_coefficienti_{anno}.json")
        if not os.path.isfile(file_path):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            inps = data.get("ContributiInps") or {}
            valore = inps.get("AliquotaGestioneSeparata")
            if valore is not None and _as_dec(valore) > 0:
                regole.AliquotaGestioneSeparata = _as_dec(valore)
        except Exception:
            return

    def get_anni_disponibili(self) -> List[int]:
        anni: List[int] = []
        if not os.path.isdir(self._rules_directory):
            return anni
        for nome in os.listdir(self._rules_directory):
            if nome.startswith("tax_rules_") and nome.endswith(".json"):
                try:
                    anni.append(int(nome[len("tax_rules_"):-len(".json")]))
                except ValueError:
                    continue
        return anni


def _regola_da_dict(data: dict, anno: int) -> RegolaFiscale:
    """Costruisce una RegolaFiscale da un dict JSON (chiavi PascalCase o snake_case)."""
    r = RegolaFiscale(anno if anno else int(data.get("Anno", 0) or 0))

    def dec(key: str) -> Optional[Decimal]:
        v = data.get(key) or data.get(_snake(key))
        return _as_dec(v) if v is not None else None

    for attr, key in [
        ("NoTaxAreaLavoroDipendente", "NoTaxAreaLavoroDipendente"),
        ("NoTaxAreaPensione", "NoTaxAreaPensione"),
        ("DetrazioneLavoroDipendenteMax", "DetrazioneLavoroDipendenteMax"),
        ("DetrazioneLavoroPrimaFascia", "DetrazioneLavoroPrimaFascia"),
        ("DetrazioneLavoroBonus25_35", "DetrazioneLavoroBonus25_35"),
        ("DetrazioneConiugeCaricoMax", "DetrazioneConiugeCaricoMax"),
        ("DetrazioneFigliCaricoBase", "DetrazioneFigliCaricoBase"),
        ("DetrazioneFigliCaricoMaggiorazione", "DetrazioneFigliCaricoMaggiorazione"),
        ("AliquotaIres", "AliquotaIres"),
        ("AliquotaIrapBase", "AliquotaIrapBase"),
        ("DeduzioneIrapPersonaleUnitario", "DeduzioneIrapPersonaleUnitario"),
        ("LimiteForfettarioRicavi", "LimiteForfettarioRicavi"),
        ("CoefficienteRedditivitaForfettario", "CoefficienteRedditivitaForfettario"),
        ("AliquotaForfettario", "AliquotaForfettario"),
        ("AliquotaForfettarioStartup", "AliquotaForfettarioStartup"),
        ("CuneoUlterioreDetrazioneMax", "CuneoUlterioreDetrazioneMax"),
        ("CuneoUlterioreDetrazioneSogliaMin", "CuneoUlterioreDetrazioneSogliaMin"),
        ("CuneoUlterioreDetrazioneSogliaPiena", "CuneoUlterioreDetrazioneSogliaPiena"),
        ("CuneoUlterioreDetrazioneSogliaMax", "CuneoUlterioreDetrazioneSogliaMax"),
        ("TrattamentoIntegrativoBase", "TrattamentoIntegrativoBase"),
        ("TrattamentoIntegrativoSogliaMin", "TrattamentoIntegrativoSogliaMin"),
        ("TrattamentoIntegrativoSogliaMax", "TrattamentoIntegrativoSogliaMax"),
        ("AliquotaGestioneSeparata", "AliquotaGestioneSeparata"),
        ("AliquotaContributiArtigianiCommercianti", "AliquotaContributiArtigianiCommercianti"),
        ("AliquotaContributiForfettario", "AliquotaContributiForfettario"),
        ("AliquotaContributiDipendente", "AliquotaContributiDipendente"),
        ("AliquotaContributiDipendentePubblico", "AliquotaContributiDipendentePubblico"),
        ("AliquotaContributiDipendenteApprendista", "AliquotaContributiDipendenteApprendista"),
        ("LimitePrevidenzaComplementareMax", "LimitePrevidenzaComplementareMax"),
        ("SogliaWelfareStandardAnnua", "SogliaWelfareStandardAnnua"),
        ("SogliaWelfareFigliAnnua", "SogliaWelfareFigliAnnua"),
        ("SogliaWelfareRedditoMax", "SogliaWelfareRedditoMax"),
        ("SogliaWelfareStandard2025", "SogliaWelfareStandard2025"),
        ("AliquotaCedolareSecca", "AliquotaCedolareSecca"),
        ("AliquotaCedolareSeccaConcordato", "AliquotaCedolareSeccaConcordato"),
        ("AliquotaCedolareSeccaLocazioneBreve", "AliquotaCedolareSeccaLocazioneBreve"),
        ("CoefficienteImuRendita", "CoefficienteImuRendita"),
        ("SogliaSterilizzazioneReddito", "SogliaSterilizzazioneReddito"),
        ("SterilizzazioneDetrazioniImporto", "SterilizzazioneDetrazioniImporto"),
        ("AliquotaFlatTaxIncrementoRetributivo", "AliquotaFlatTaxIncrementoRetributivo"),
        ("SogliaReddito2025FlatTaxRinnovi", "SogliaReddito2025FlatTaxRinnovi"),
        ("AliquotaImpostaSostitutivaPremiProduttivita", "AliquotaImpostaSostitutivaPremiProduttivita"),
        ("LimitePremiProduttivita", "LimitePremiProduttivita"),
        ("AliquotaImpostaSostitutivaMaggiorazioni", "AliquotaImpostaSostitutivaMaggiorazioni"),
        ("LimiteMaggiorazioni", "LimiteMaggiorazioni"),
        ("SogliaReddito2025Maggiorazioni", "SogliaReddito2025Maggiorazioni"),
        ("BonusMammeIntegrazioneMensile", "BonusMammeIntegrazioneMensile"),
        ("SogliaRedditoBonusMamme", "SogliaRedditoBonusMamme"),
        ("SogliaBuoniPastoElettronici", "SogliaBuoniPastoElettronici"),
        ("SogliaBuoniPastoCartacei", "SogliaBuoniPastoCartacei"),
        ("AliquotaPlusvalenzeCripto", "AliquotaPlusvalenzeCripto"),
        ("AliquotaPlusvalenzeCriptoDal2026", "AliquotaPlusvalenzeCriptoDal2026"),
        ("SogliaPlusvalenzaCripto", "SogliaPlusvalenzaCripto"),
        ("AliquotaContributiDatore", "AliquotaContributiDatore"),
        ("AliquotaTfr", "AliquotaTfr"),
        ("DetrazionePensioneMax", "DetrazionePensioneMax"),
        ("DetrazionePensioneMinimo", "DetrazionePensioneMinimo"),
        ("DetrazionePensioneBaseSecondaFascia", "DetrazionePensioneBaseSecondaFascia"),
        ("DetrazionePensioneIncrementoSecondaFascia", "DetrazionePensioneIncrementoSecondaFascia"),
        ("SogliaPensioneSecondaFascia", "SogliaPensioneSecondaFascia"),
        ("SogliaPensioneTerzaFascia", "SogliaPensioneTerzaFascia"),
        ("BonusDetrazionePensione25_29", "BonusDetrazionePensione25_29"),
        ("SogliaBonusDetrazionePensioneMin", "SogliaBonusDetrazionePensioneMin"),
        ("SogliaBonusDetrazionePensioneMax", "SogliaBonusDetrazionePensioneMax"),
        ("AliquotaUtilizzoPerditeForfettario", "AliquotaUtilizzoPerditeForfettario"),
        ("SogliaQuozienteFamiliareMin", "SogliaQuozienteFamiliareMin"),
        ("SogliaQuozienteFamiliareMax", "SogliaQuozienteFamiliareMax"),
        ("BaseQuozienteFamiliareSotto75_100", "BaseQuozienteFamiliareSotto75_100"),
        ("BaseQuozienteFamiliareOltre100", "BaseQuozienteFamiliareOltre100"),
        ("BonusAffittoUnder31", "BonusAffittoUnder31"),
        ("BonusPsicologo", "BonusPsicologo"),
        ("BonusMobilitaSostenibile", "BonusMobilitaSostenibile"),
        ("AliquotaCreditoFormazione40", "AliquotaCreditoFormazione40"),
        ("AliquotaCreditoRistrutturazione2026", "AliquotaCreditoRistrutturazione2026"),
        ("AliquotaCreditoRistrutturazione2026Altre", "AliquotaCreditoRistrutturazione2026Altre"),
        ("PlafondRistrutturazione2026", "PlafondRistrutturazione2026"),
        ("AliquotaCreditoEfficienzaEnergetica2026", "AliquotaCreditoEfficienzaEnergetica2026"),
        ("AliquotaCreditoEfficienzaEnergetica2026Altre", "AliquotaCreditoEfficienzaEnergetica2026Altre"),
        ("AliquotaCreditoRS", "AliquotaCreditoRS"),
        ("AliquotaCreditoBeniStrumentali", "AliquotaCreditoBeniStrumentali"),
        ("AliquotaPatentBox", "AliquotaPatentBox"),
        ("AliquotaZESUnica", "AliquotaZESUnica"),
        ("SogliaMinimaInvestimentoZES", "SogliaMinimaInvestimentoZES"),
        ("LimiteMassimoInvestimentoZES", "LimiteMassimoInvestimentoZES"),
        ("AliquotaConcordatoPreventivo", "AliquotaConcordatoPreventivo"),
        ("LimiteEsoneroUnder36", "LimiteEsoneroUnder36"),
        ("IncentivoDonnePerUnita", "IncentivoDonnePerUnita"),
        ("DecontribuzioneDonne2026", "DecontribuzioneDonne2026"),
        ("IncentivoCIGS_NASpI", "IncentivoCIGS_NASpI"),
        ("IncentivoOver50", "IncentivoOver50"),
        ("IncentivoApprendistato", "IncentivoApprendistato"),
        ("IncentivoZES", "IncentivoZES"),
        ("LimiteSpeseMediche", "LimiteSpeseMediche"),
        ("LimiteCreditoRS", "LimiteCreditoRS"),
        ("LimiteCreditoFormazione40", "LimiteCreditoFormazione40"),
        ("Iperammortamento2026Scaglione1", "Iperammortamento2026Scaglione1"),
        ("Iperammortamento2026Scaglione2", "Iperammortamento2026Scaglione2"),
        ("Iperammortamento2026Scaglione3", "Iperammortamento2026Scaglione3"),
        ("Iperammortamento2026Coefficiente1", "Iperammortamento2026Coefficiente1"),
        ("Iperammortamento2026Coefficiente2", "Iperammortamento2026Coefficiente2"),
        ("Iperammortamento2026Coefficiente3", "Iperammortamento2026Coefficiente3"),
    ]:
        v = dec(key)
        if v is not None:
            setattr(r, attr, v)

    if data.get("SogliaImmobiliPresunzioneImprenditorialita") is not None:
        r.SogliaImmobiliPresunzioneImprenditorialita = int(
            data["SogliaImmobiliPresunzioneImprenditorialita"]
        )

    scaglioni = data.get("ScaglioniIrpef")
    if scaglioni:
        r.ScaglioniIrpef = [
            ScaglioneIrpef(
                minimo=_as_dec(s.get("Minimo", 0)),
                massimo=_as_dec(s["Massimo"]) if s.get("Massimo") is not None else None,
                aliquota=_as_dec(s.get("Aliquota", 0)),
                detrazione=_as_dec(s.get("Detrazione", 0)),
            )
            for s in scaglioni
        ]

    for key in ("EsoneroContributiSoglie", "EsoneroContributiAliquote",
                "CuneoBonusSoglie", "CuneoBonusAliquote", "SoglieRedditoFigli",
                "QuozienteFamiliareCoefficienti"):
        v = data.get(key)
        if v:
            setattr(r, key, [_as_dec(x) for x in v])

    add_reg = data.get("AddizionaliRegionali") or {}
    r.AddizionaliRegionali = {
        k: AddizionaleRegionale(
            regione=v.get("Regione") or k,
            aliquota_base=_as_dec(v.get("AliquotaBase", 0)),
            scaglioni=[_as_dec(x) for x in (v.get("Scaglioni") or [])],
            aliquote=[_as_dec(x) for x in (v.get("Aliquote") or [])],
        )
        for k, v in add_reg.items()
    }
    if not r.AddizionaliRegionali:
        r.AddizionaliRegionali["Default"] = AddizionaleRegionale(
            "Default", Decimal("0.0123"), [], []
        )

    add_com = data.get("AddizionaliComunali") or {}
    r.AddizionaliComunali = {
        k: AddizionaleComunale(
            comune=v.get("Comune") or k,
            codice_catastale=v.get("CodiceCatastale") or "",
            aliquota=_as_dec(v.get("Aliquota", 0)),
            soglia_esenzione=_as_dec(v.get("SogliaEsenzione", 0)),
            scaglioni=[_as_dec(x) for x in v["Scaglioni"]] if v.get("Scaglioni") else None,
            aliquote=[_as_dec(x) for x in v["Aliquote"]] if v.get("Aliquote") else None,
        )
        for k, v in add_com.items()
    }
    if not r.AddizionaliComunali:
        r.AddizionaliComunali["Default"] = AddizionaleComunale("Default", "", Decimal("0.002"))

    zes = data.get("ZesUnicaAliquote")
    if zes:
        r.ZesUnicaAliquote = [
            ZesAliquota2026(
                regione=z.get("Regione") or "",
                grandi=_as_dec(z.get("Grandi", 0)),
                medie=_as_dec(z.get("Medie", 0)),
                piccole=_as_dec(z.get("Piccole", 0)),
            )
            for z in zes
        ]

    r.Fonte = data.get("Fonte") or ""
    return r


def _snake(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)
