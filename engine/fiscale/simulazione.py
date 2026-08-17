"""Servizio di simulazione fiscale (port di SimulazioneService.cs).

Esegue l'intera pipeline: deduzioni, IRPEF/IRES/IRAP/forfettario, benefici cuneo,
cedolare secca, IMU, agevolazioni 2026, crediti, netto stimato, busta paga,
suggerimenti e decomposizione del cuneo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal

from .benefici import BeneficiLavoratoreCalculator
from .confronto import ConfrontoRegimiService
from .crediti import CreditiImpostaService
from .cuneo import CuneoFiscaleService
from .detrazioni import DetrazioniService
from .forfettario import ForfettarioCalculator, ForfettarioPrecisioneService
from .irpef import IrpefCalculator
from .money import round0, round2
from .models import (
    BilancioSocieta,
    Contribuente,
    CreditoImposta,
    DetrazioneIrpef,
    Reddito,
    RisultatoSimulazione,
    SpesaDeducibile,
    TipoContribuente,
    TipoDipendenteInps,
    TipoReddito,
    TipoSpesa,
    VoceBusta,
    VoceCuneo,
)
from .ottimizzazione import OttimizzazioneService
from .regimi import RegimiSpecialiService
from .societa import IrapCalculator, IresCalculator


class SimulazioneService:
    def __init__(self, rule_service, irpef_calc=None, ires_calc=None, irap_calc=None,
                 forfettario_calc=None, ottimizzazione=None, benefici=None,
                 forfettario_precisione=None, detrazioni_service=None,
                 crediti_service=None, regimi_service=None, cuneo_service=None):
        self._rule_service = rule_service
        self._irpef_calc = irpef_calc or IrpefCalculator()
        self._ires_calc = ires_calc or IresCalculator()
        self._irap_calc = irap_calc or IrapCalculator()
        self._forfettario_calc = forfettario_calc or ForfettarioCalculator()
        self._forfettario_precisione = forfettario_precisione
        self._detrazioni_service = detrazioni_service or DetrazioniService(rule_service)
        self._crediti_service = crediti_service or CreditiImpostaService()
        self._regimi_service = regimi_service or RegimiSpecialiService()
        self._cuneo_service = cuneo_service or CuneoFiscaleService()
        self._ottimizzazione = ottimizzazione or OttimizzazioneService()
        self._benefici = benefici or BeneficiLavoratoreCalculator()

    def esegui(self, c: Contribuente, redditi, spese=None, detrazioni=None, crediti=None,
               bilancio: BilancioSocieta | None = None, numero_dipendenti: int = 0) -> RisultatoSimulazione:
        spese = spese or []
        detrazioni = detrazioni or []
        crediti = crediti or []

        reddito_complessivo = sum((r.importo_lordo for r in redditi), Decimal(0))
        regole = self._rule_service.get_regole(c.anno_riferimento)

        risultato = RisultatoSimulazione(
            contribuente=c,
            anno=c.anno_riferimento,
        )

        deduzioni = self._calcola_deduzioni(c, redditi, spese, regole)
        redditi_deducibili = self._applica_deduzioni(redditi, deduzioni, c.usa_cedolare_secca)

        if c.tipo in (TipoContribuente.PersonaFisica, TipoContribuente.PartitaIvaOrdinaria):
            risultato.irpef = self._irpef_calc.calcola(c, redditi_deducibili, detrazioni, regole)

        elif c.tipo == TipoContribuente.PartitaIvaForfettaria:
            calcolo_f = self._forfettario_calc.calcola(c, redditi, regole)
            risultato.irpef = self._calcolo_forfettario_semplificato(
                reddito_complessivo, calcolo_f.reddito_imponibile, calcolo_f.imposta_sostitutiva)
            if calcolo_f.reddito_imponibile > regole.LimiteForfettarioRicavi:
                risultato.nota_fuoriuscita_forfettario = (
                    f"Ricavi oltre il limite del regime forfettario "
                    f"({regole.LimiteForfettarioRicavi:,.0f} €): il regime cessa dall'anno successivo; "
                    f"l'imposta sostitutiva calcolata è solo indicativa."
                )
            if self._forfettario_precisione is not None:
                fp = self._forfettario_precisione.calcola(c, c.anno_riferimento)
                risultato.forfettario_precisione = fp
                risultato.irpef.reddito_imponibile = fp.reddito_imponibile_netto
                risultato.irpef.imposta_netta = fp.imposta_sostitutiva
                risultato.irpef.totale_irpef = fp.imposta_sostitutiva

        elif c.tipo == TipoContribuente.SocietaDiCapitali and bilancio is not None:
            risultato.ires = self._ires_calc.calcola(bilancio, crediti, regole)
            risultato.irap = self._irap_calc.calcola(bilancio, redditi, regole)
            risultato.utile_netto_dopo_tasse = (
                bilancio.utile_perdita_ante_imposte - risultato.ires.ires_netta - risultato.irap.irap_netta
            )

        risultato.totale_tasse += (
            (risultato.irpef.totale_irpef if risultato.irpef else Decimal(0))
            + (risultato.ires.ires_netta if risultato.ires else Decimal(0))
            + (risultato.irap.irap_netta if risultato.irap else Decimal(0))
        )

        risultato.totale_contributi_previdenziali = sum((r.contributi_previdenziali for r in redditi), Decimal(0))
        if c.tipo == TipoContribuente.PartitaIvaForfettaria and risultato.forfettario_precisione is not None:
            risultato.totale_contributi_previdenziali += risultato.forfettario_precisione.contributi_totali

        risultato.contributi_inps_dipendente = self._calcola_contributi_inps_dipendente(c, redditi, regole)
        if c.tipo_dipendente_inps != TipoDipendenteInps.Privato:
            contributi_passati = sum(
                (r.contributi_previdenziali for r in redditi if r.tipo == TipoReddito.LavoroDipendente),
                Decimal(0),
            )
            risultato.totale_contributi_previdenziali = (
                risultato.totale_contributi_previdenziali - contributi_passati + risultato.contributi_inps_dipendente
            )

        benefici = self._benefici.calcola(c, redditi, risultato.irpef, regole)
        risultato.esonero_contributi = benefici.esonero_contributi
        risultato.bonus_cuneo = benefici.bonus_cuneo
        risultato.ulteriore_detrazione_cuneo = benefici.ulteriore_detrazione
        risultato.trattamento_integrativo = benefici.trattamento_integrativo

        risultato.cedolare_secca = self._calcola_cedolare_secca(c, redditi, regole)
        risultato.imu_stimata = self._calcola_imu(c, regole)
        risultato.totale_tasse += risultato.cedolare_secca

        risultato.ritenuta_intermediari_locazioni_brevi = self._calcola_ritenuta_locazioni_brevi(c, redditi)

        risultato.presunzione_imprenditorialita = self._verifica_presunzione_impresa(c, redditi, regole)
        if risultato.presunzione_imprenditorialita:
            risultato.nota_presunzione_impresa = (
                "Dal 2026 la concessione in locazione breve di più di 2 appartamenti determina la "
                "presunzione di esercizio di impresa: il reddito non è più tassato in cedolare secca "
                "ma rileva come reddito d'impresa (art. 1 c. 19 L. 199/2025)."
            )

        self._calcola_agevolazioni_2026(c, reddito_complessivo, regole, risultato)
        self._calcola_buoni_pasto(c, regole, risultato)
        self._calcola_cripto(c, regole, risultato)
        self._calcola_costo_azienda(c, reddito_complessivo, regole, risultato)

        crediti_totali = self._crediti_service.calcola(crediti).totale_crediti
        risultato.totale_tasse -= crediti_totali

        risultato.totale_tasse = max(Decimal(0), risultato.totale_tasse - risultato.ulteriore_detrazione_cuneo)
        risultato.totale_tasse += risultato.totale_imposte_sostitutive_2026
        risultato.totale_tasse += risultato.imposta_cripto

        self._calcola_rimborso_smart_working(c, regole, risultato)
        self._calcola_auto_aziendale(c, regole, risultato)
        self._calcola_impatriati(c, redditi, regole, risultato)

        risultato.reddito_netto_stimato = (
            reddito_complessivo
            - risultato.totale_tasse
            - risultato.totale_contributi_previdenziali
            + risultato.trattamento_integrativo
            + risultato.bonus_cuneo
            + risultato.bonus_mamme_annuale
            + risultato.rimborso_smart_working_annuale
            + risultato.esenzione_impatriati_annuale
            - risultato.imu_stimata
        )

        mensilita = 12 + max(0, c.numero_mensilita_extra)
        if mensilita <= 0:
            mensilita = 12
        risultato.netto_mensile_base = round2(risultato.reddito_netto_stimato / mensilita)
        risultato.netto_mensilita_extra = round2(
            risultato.netto_mensile_base * max(0, c.numero_mensilita_extra)
        )

        self._calcola_part_time(c, risultato)

        risultato.voci_busta = self._costruisci_busta_paga(c, redditi, risultato)

        risultato.suggerimenti = self._ottimizzazione.analizza(c, risultato, regole)
        risultato.risparmio_stimato = sum((s.risparmio_stimato for s in risultato.suggerimenti), Decimal(0))
        risultato.decomposizione_cuneo = self._costruisci_cuneo(risultato)

        return risultato

    def _calcola_deduzioni(self, c, redditi, spese, regole) -> Decimal:
        deduzioni = Decimal(0)
        deduzioni += sum(
            (min(s.importo, regole.LimitePrevidenzaComplementareMax)
             for s in spese if s.tipo == TipoSpesa.PrevidenzaComplementare),
            Decimal(0),
        )
        deduzioni += sum(
            (s.importo * s.percentuale_deducibilita / Decimal(100)
             for s in spese if s.is_deducibile_da_reddito_impresa),
            Decimal(0),
        )
        return deduzioni

    def _applica_deduzioni(self, redditi, deduzioni, escludi_fondiaria_cedolare) -> list:
        if deduzioni <= 0:
            return list(redditi)
        residuo = deduzioni
        ridotti = []
        for r in redditi:
            if escludi_fondiaria_cedolare and r.tipo == TipoReddito.Fondiaria:
                ridotti.append(r)
                continue
            if residuo <= 0:
                ridotti.append(r)
                continue
            da_ridurre = min(r.importo_lordo, residuo)
            ridotti.append(Reddito(
                tipo=r.tipo,
                descrizione=r.descrizione,
                importo_lordo=r.importo_lordo - da_ridurre,
                importo_netto=r.importo_netto,
                contributi_previdenziali=r.contributi_previdenziali,
                deduzioni_specifiche=r.deduzioni_specifiche,
                anno_competenza=r.anno_competenza,
                is_locazione_breve=r.is_locazione_breve,
            ))
            residuo -= da_ridurre
        return ridotti

    def _calcolo_forfettario_semplificato(self, reddito_complessivo, imponibile, imposta):
        from .models import CalcoloIrpef
        r = CalcoloIrpef(
            reddito_complessivo=reddito_complessivo,
            reddito_imponibile=imponibile,
            imposta_netta=imposta,
            totale_irpef=imposta,
        )
        return r

    def _calcola_contributi_inps_dipendente(self, c, redditi, regole) -> Decimal:
        if c.tipo_dipendente_inps == TipoDipendenteInps.Privato:
            return sum(
                (r.contributi_previdenziali for r in redditi if r.tipo == TipoReddito.LavoroDipendente),
                Decimal(0),
            )
        aliquote = {
            TipoDipendenteInps.Pubblico: regole.AliquotaContributiDipendentePubblico,
            TipoDipendenteInps.Apprendista: regole.AliquotaContributiDipendenteApprendista,
        }
        aliquota = aliquote.get(c.tipo_dipendente_inps, regole.AliquotaContributiDipendente)
        base = sum(
            (r.importo_lordo for r in redditi if r.tipo == TipoReddito.LavoroDipendente),
            Decimal(0),
        )
        return round2(base * aliquota)

    def _calcola_cedolare_secca(self, c, redditi, regole) -> Decimal:
        if not c.usa_cedolare_secca:
            return Decimal(0)
        locazioni_brevi = [r for r in redditi if r.tipo == TipoReddito.Fondiaria and r.is_locazione_breve]
        locazioni_ordinarie = sum(
            (r.importo_lordo for r in redditi if r.tipo == TipoReddito.Fondiaria and not r.is_locazione_breve),
            Decimal(0),
        )
        totale = locazioni_ordinarie * (
            regole.AliquotaCedolareSeccaConcordato if c.cedolare_concordato else regole.AliquotaCedolareSecca
        )
        for i, r in enumerate(locazioni_brevi):
            aliquota = regole.AliquotaCedolareSecca if i == 0 else regole.AliquotaCedolareSeccaLocazioneBreve
            totale += r.importo_lordo * aliquota
        return round2(totale)

    def _verifica_presunzione_impresa(self, c, redditi, regole) -> bool:
        if not c.usa_cedolare_secca:
            return False
        immobili = c.numero_immobili_locazione_breve
        if immobili <= 0:
            immobili = sum(1 for r in redditi if r.tipo == TipoReddito.Fondiaria and r.is_locazione_breve)
        return immobili > regole.SogliaImmobiliPresunzioneImprenditorialita

    def _calcola_ritenuta_locazioni_brevi(self, c, redditi) -> Decimal:
        if not c.usa_cedolare_secca:
            return Decimal(0)
        locazioni = sum(
            (r.importo_lordo for r in redditi if r.tipo == TipoReddito.Fondiaria and r.is_locazione_breve),
            Decimal(0),
        )
        return round2(locazioni * Decimal("0.21"))

    def _calcola_agevolazioni_2026(self, c, reddito_complessivo, regole, risultato) -> None:
        if c.anno_riferimento < 2026:
            return
        risultato.imposta_sostitutiva_flat_tax_rinnovi = (
            round2(c.incremento_retributivo_rinnovo * regole.AliquotaFlatTaxIncrementoRetributivo)
            if reddito_complessivo <= regole.SogliaReddito2025FlatTaxRinnovi else Decimal(0)
        )
        risultato.imposta_sostitutiva_premi_produttivita = round2(
            min(c.premio_produttivita, regole.LimitePremiProduttivita)
            * regole.AliquotaImpostaSostitutivaPremiProduttivita
        )
        maggiorazioni = (
            min(c.importo_maggiorazioni_lavoro, regole.LimiteMaggiorazioni)
            if reddito_complessivo <= regole.SogliaReddito2025Maggiorazioni else Decimal(0)
        )
        risultato.imposta_sostitutiva_maggiorazioni = round2(
            maggiorazioni * regole.AliquotaImpostaSostitutivaMaggiorazioni
        )
        risultato.totale_imposte_sostitutive_2026 = (
            risultato.imposta_sostitutiva_flat_tax_rinnovi
            + risultato.imposta_sostitutiva_premi_produttivita
            + risultato.imposta_sostitutiva_maggiorazioni
        )
        if (c.aderisce_bonus_mamme and c.sesso == "F" and c.figli_carico >= 2
                and reddito_complessivo <= regole.SogliaRedditoBonusMamme):
            risultato.bonus_mamme_annuale = round2(regole.BonusMammeIntegrazioneMensile * 12)

    def _calcola_imu(self, c, regole) -> Decimal:
        return round2(c.rendita_catastale_imu * regole.CoefficienteImuRendita * c.aliquota_imu)

    def _calcola_buoni_pasto(self, c, regole, risultato) -> None:
        if c.anno_riferimento < 2026:
            return
        giornate = max(0, c.giorni_buoni_pasto_elettronici)
        giornate_cartacee = max(0, c.giorni_buoni_pasto_cartacei)
        risultato.beneficio_buoni_pasto = round2(
            giornate * regole.SogliaBuoniPastoElettronici + giornate_cartacee * regole.SogliaBuoniPastoCartacei
        )

    def _calcola_cripto(self, c, regole, risultato) -> None:
        if not c.ha_redditi_cripto or c.anno_riferimento < 2023:
            return
        risultato.ha_redditi_cripto = True
        plusvalenze = max(Decimal(0), c.plusvalenze_cripto - c.minusvalenze_cripto)
        aliquota = (
            regole.AliquotaPlusvalenzeCriptoDal2026
            if c.anno_riferimento >= 2026 and regole.AliquotaPlusvalenzeCriptoDal2026 > 0
            else regole.AliquotaPlusvalenzeCripto
        )
        if plusvalenze > regole.SogliaPlusvalenzaCripto:
            risultato.imposta_cripto = round2(plusvalenze * aliquota)

    def _calcola_costo_azienda(self, c, reddito_complessivo, regole, risultato) -> None:
        if reddito_complessivo <= 0:
            return
        inps_datoriale = reddito_complessivo * regole.AliquotaContributiDatore
        tfr = reddito_complessivo * regole.AliquotaTfr
        risultato.costo_totale_lavoro = round2(reddito_complessivo + inps_datoriale + tfr)

    def _calcola_rimborso_smart_working(self, c, regole, risultato) -> None:
        if c.rimborso_smart_working_mensile <= 0:
            return
        mensile = min(c.rimborso_smart_working_mensile, regole.LimiteRimborsoSmartWorkingMensile)
        risultato.rimborso_smart_working_annuale = round2(mensile * 12)

    def _calcola_auto_aziendale(self, c, regole, risultato) -> None:
        if not c.ha_auto_aziendale or c.valore_auto_aziendale <= 0:
            return
        percentuale = (
            regole.PercentualeAutoAziendaleElettrica
            if c.auto_aziendale_elettrica else regole.PercentualeAutoAziendale
        )
        risultato.auto_aziendale_fringe_annuale = round2(c.valore_auto_aziendale * percentuale)

    def _calcola_impatriati(self, c, redditi, regole, risultato) -> None:
        if not c.usa_regime_impatriati:
            return
        reddito_lavoro = sum(
            (r.importo_lordo for r in redditi
             if r.tipo in (TipoReddito.LavoroDipendente, TipoReddito.LavoroAutonomo)),
            Decimal(0),
        )
        risultato.esenzione_impatriati_annuale = round2(reddito_lavoro * regole.EsenzioneImpatriatiPercentuale)

    def _calcola_part_time(self, c, risultato) -> None:
        full_time = c.ore_settimanali_full_time if c.ore_settimanali_full_time > 0 else 40
        fattore = (
            round4(Decimal(c.ore_settimanali_part_time) / Decimal(full_time))
            if c.is_part_time and full_time > 0 else Decimal(1)
        )
        fattore = max(Decimal(0), fattore)
        risultato.fattore_part_time = fattore
        risultato.netto_part_time_mensile = round2(risultato.netto_mensile_base * fattore)

    def _costruisci_busta_paga(self, c, redditi, r) -> list:
        voci: list[VoceBusta] = []
        redditi_dipendente = [x for x in redditi if x.tipo == TipoReddito.LavoroDipendente]
        if not redditi_dipendente:
            return voci

        lordo = sum((x.importo_lordo for x in redditi_dipendente), Decimal(0))
        voci.append(VoceBusta("Retribuzione annua lorda (RAL)", lordo, "Retribuzione"))

        if r.contributi_inps_dipendente > 0:
            voci.append(VoceBusta(
                "Contributi INPS a carico del lavoratore", -r.contributi_inps_dipendente, "Contributo"))

        imponibile = r.irpef.reddito_imponibile if r.irpef else max(Decimal(0), lordo - r.contributi_inps_dipendente)
        voci.append(VoceBusta("Reddito imponibile IRPEF", imponibile, "Retribuzione"))

        if r.irpef is not None:
            voci.append(VoceBusta("IRPEF lorda (scaglioni)", -r.irpef.imposta_lorda, "Imposta"))
            if r.irpef.detrazioni_totali > 0:
                voci.append(VoceBusta("Detrazioni lavoro/dipendente", r.irpef.detrazioni_totali, "Detrazione"))
            if r.irpef.addizionale_regionale > 0:
                voci.append(VoceBusta("Addizionale regionale IRPEF", -r.irpef.addizionale_regionale, "Imposta"))
            if r.irpef.addizionale_comunale > 0:
                voci.append(VoceBusta("Addizionale comunale IRPEF", -r.irpef.addizionale_comunale, "Imposta"))

        if r.bonus_cuneo > 0:
            voci.append(VoceBusta("Bonus cuneo fiscale (esente)", r.bonus_cuneo, "Bonus", True))
        if r.esonero_contributi > 0:
            voci.append(VoceBusta("Esonero contributivo (cuneo)", r.esonero_contributi, "Bonus", True))
        if r.ulteriore_detrazione_cuneo > 0:
            voci.append(VoceBusta("Ulteriore detrazione cuneo (2025)", r.ulteriore_detrazione_cuneo, "Detrazione"))
        if r.trattamento_integrativo > 0:
            voci.append(VoceBusta("Trattamento integrativo (bonus 100 €)", r.trattamento_integrativo, "Bonus", True))
        if r.beneficio_buoni_pasto > 0:
            voci.append(VoceBusta("Buoni pasto esenti (fringe benefit)", r.beneficio_buoni_pasto, "Esenzione", True))
        if r.rimborso_smart_working_annuale > 0:
            voci.append(VoceBusta("Rimborso smart working esente", r.rimborso_smart_working_annuale, "Esenzione", True))
        if r.auto_aziendale_fringe_annuale > 0:
            voci.append(VoceBusta("Auto aziendale (fringe benefit)", r.auto_aziendale_fringe_annuale, "Retribuzione"))
        if r.esenzione_impatriati_annuale > 0:
            voci.append(VoceBusta("Esenzione impatriati (rientro cervelli)", r.esenzione_impatriati_annuale, "Esenzione", True))

        if c.is_part_time and r.fattore_part_time < 1:
            voci.append(VoceBusta(
                f"Riduzione part-time ({(r.fattore_part_time * 100):.0f}%)",
                -round2(lordo * (Decimal(1) - r.fattore_part_time)), "Retribuzione"))

        if r.ritenuta_intermediari_locazioni_brevi > 0:
            voci.append(VoceBusta("Ritenuta 21% intermediari locazioni brevi", -r.ritenuta_intermediari_locazioni_brevi, "Imposta"))
        if r.cedolare_secca > 0:
            voci.append(VoceBusta("Cedolare secca (immobili)", -r.cedolare_secca, "Imposta"))

        if c.is_part_time and r.fattore_part_time < 1:
            voci.append(VoceBusta("Netto mensile part-time", r.netto_part_time_mensile, "Totale"))

        voci.append(VoceBusta("Netto annuo stimato", r.reddito_netto_stimato, "Totale"))
        return voci

    def _costruisci_cuneo(self, r) -> list:
        voci = [
            VoceCuneo("IRPEF", r.irpef.totale_irpef if r.irpef else Decimal(0), "#FF5722", 0.0, True),
            VoceCuneo("Contributi Previdenziali", r.totale_contributi_previdenziali, "#FF9800", 0.0, True),
            VoceCuneo("IRES", r.ires.imposta_netta if r.ires else Decimal(0), "#4CAF50", 0.0, True),
            VoceCuneo("IRAP", r.irap.irap_netta if r.irap else Decimal(0), "#2196F3", 0.0, True),
            VoceCuneo("Bonus cuneo (IRPEF esente)", r.bonus_cuneo, "#4CAF50", 0.0, False),
            VoceCuneo("Esonero Contributivo (2024)", r.esonero_contributi, "#8BC34A", 0.0, False),
            VoceCuneo("Ulteriore detrazione cuneo", r.ulteriore_detrazione_cuneo, "#8BC34A", 0.0, False),
        ]
        totale_cuneo = sum((v.valore for v in voci if v.is_costo), Decimal(0))
        for v in voci:
            v.percentuale = float(v.valore / max(totale_cuneo, Decimal(1)) * 100)
        return voci


def round4(x):
    return Decimal(x).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def _as_decimal(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))
