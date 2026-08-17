"""Calcolatore IRPEF (port di IrpefCalculator.cs).

Seguenza esatta del C#: scaglioni progressivi, detrazione lavoro/pensione
(art. 13 TUIR), detrazioni famiglia (art. 12), detrazioni oneri con cap
quoziente familiare (art. 16-ter), sterilizzazione >200.000 €, addizionali
regionale e comunale. Ogni arrotondamento è banker's rounding (ROUND_HALF_EVEN).
"""
from __future__ import annotations

from decimal import Decimal

from .money import round2
from .models import (
    AddizionaleComunale,
    CalcoloIrpef,
    Contribuente,
    DetrazioneApplicata,
    DetrazioneIrpef,
    Reddito,
    ScaglioneCalcolato,
    TipoContribuente,
    TipoReddito,
)

MAX_VALUE = Decimal("99999999999999999999")

# Mappa sigla provincia -> regione (da IrpefCalculator.cs)
_PROVINCIA_REGIONE = {
    "TO": "Piemonte", "VC": "Piemonte", "NO": "Piemonte", "CN": "Piemonte",
    "AL": "Piemonte", "BI": "Piemonte", "VB": "Piemonte", "AT": "Piemonte",
    "AO": "ValleDAosta",
    "MI": "Lombardia", "BG": "Lombardia", "BS": "Lombardia", "CO": "Lombardia",
    "CR": "Lombardia", "LC": "Lombardia", "LO": "Lombardia", "MN": "Lombardia",
    "PV": "Lombardia", "SO": "Lombardia", "VA": "Lombardia", "MB": "Lombardia",
    "BZ": "TrentinoAltoAdige", "TN": "TrentinoAltoAdige",
    "VR": "Veneto", "VI": "Veneto", "BL": "Veneto", "TV": "Veneto",
    "VE": "Veneto", "PD": "Veneto", "RO": "Veneto",
    "UD": "FriuliVeneziaGiulia", "GO": "FriuliVeneziaGiulia", "TS": "FriuliVeneziaGiulia",
    "PN": "FriuliVeneziaGiulia",
    "GE": "Liguria", "IM": "Liguria", "SP": "Liguria", "SV": "Liguria",
    "BO": "EmiliaRomagna", "FE": "EmiliaRomagna", "FO": "EmiliaRomagna",
    "MO": "EmiliaRomagna", "PR": "EmiliaRomagna", "PC": "EmiliaRomagna",
    "RA": "EmiliaRomagna", "RE": "EmiliaRomagna", "RN": "EmiliaRomagna",
    "FC": "EmiliaRomagna",
    "FI": "Toscana", "AR": "Toscana", "GR": "Toscana", "LI": "Toscana",
    "LU": "Toscana", "MS": "Toscana", "PI": "Toscana", "PT": "Toscana",
    "PO": "Toscana", "SI": "Toscana",
    "PG": "Umbria", "TR": "Umbria",
    "AN": "Marche", "AP": "Marche", "FM": "Marche", "MC": "Marche", "PU": "Marche",
    "VT": "Lazio", "RI": "Lazio", "LT": "Lazio", "RM": "Lazio", "FR": "Lazio",
    "AQ": "Abruzzo", "PE": "Abruzzo", "TE": "Abruzzo", "CH": "Abruzzo",
    "CB": "Molise", "IS": "Molise",
    "NA": "Campania", "AV": "Campania", "BN": "Campania", "CE": "Campania", "SA": "Campania",
    "BA": "Puglia", "BT": "Puglia", "BR": "Puglia", "FG": "Puglia",
    "LE": "Puglia", "TA": "Puglia",
    "PZ": "Basilicata", "MT": "Basilicata",
    "CS": "Calabria", "CZ": "Calabria", "KR": "Calabria", "RC": "Calabria",
    "VV": "Calabria",
    "PA": "Sicilia", "AG": "Sicilia", "CL": "Sicilia", "CT": "Sicilia",
    "EN": "Sicilia", "ME": "Sicilia", "RG": "Sicilia", "SR": "Sicilia", "TP": "Sicilia",
    "CA": "Sardegna", "SS": "Sardegna", "OR": "Sardegna", "NU": "Sardegna", "SU": "Sardegna",
}


class IrpefCalculator:
    def calcola(self, contribuente: Contribuente, redditi, detrazioni, regole) -> CalcoloIrpef:
        # Con cedolare secca i canoni di locazione NON concorrono al reddito IRPEF
        if contribuente.usa_cedolare_secca:
            redditi_irpef = [r for r in redditi if r.tipo != TipoReddito.Fondiaria]
        else:
            redditi_irpef = list(redditi)

        reddito_complessivo = sum((r.importo_lordo for r in redditi_irpef), Decimal(0))
        contributi_deducibili = sum((r.contributi_previdenziali for r in redditi_irpef), Decimal(0))
        deduzioni_specifiche = sum((r.deduzioni_specifiche for r in redditi_irpef), Decimal(0))

        reddito_imponibile = max(Decimal(0), reddito_complessivo - contributi_deducibili - deduzioni_specifiche)

        risultato = CalcoloIrpef(
            reddito_complessivo=reddito_complessivo,
            reddito_imponibile=reddito_imponibile,
        )

        # Scaglioni
        imposta_lorda = Decimal(0)
        scaglioni_ordinati = sorted(regole.ScaglioniIrpef, key=lambda s: s.minimo)
        for scaglione in scaglioni_ordinati:
            if reddito_imponibile <= scaglione.minimo:
                break
            massimo = scaglione.massimo if scaglione.massimo is not None else MAX_VALUE
            base = min(reddito_imponibile, massimo) - scaglione.minimo
            imposta_scaglione = base * scaglione.aliquota
            risultato.dettaglio_scaglioni.append(ScaglioneCalcolato(
                da=scaglione.minimo,
                a=massimo,
                aliquota=scaglione.aliquota,
                imponibile_nel_scaglione=base,
                imposta_nel_scaglione=imposta_scaglione,
            ))
            imposta_lorda += imposta_scaglione

        risultato.imposta_lorda = imposta_lorda

        # Detrazioni lavoro / pensione
        ha_lavoro = any(r.tipo == TipoReddito.LavoroDipendente for r in redditi_irpef)
        ha_pensione = any(r.tipo == TipoReddito.Pensione for r in redditi_irpef)
        if ha_pensione and not ha_lavoro:
            risultato.detrazioni_pensione = self._calcola_detrazione_pensione(reddito_imponibile, regole)
        else:
            risultato.detrazioni_lavoro = self._calcola_detrazione_lavoro(contribuente, reddito_imponibile, regole)

        # Detrazioni familiari
        risultato.detrazioni_famiglia = self._calcola_detrazioni_famiglia(contribuente, reddito_imponibile)

        # Detrazioni oneri
        for d in detrazioni:
            if not d.is_detraibile_irpef:
                continue
            importo_detrazione = self._calcola_detrazione_oneri(d)
            if importo_detrazione > 0:
                risultato.detrazioni_applicate.append(DetrazioneApplicata(
                    codice=d.codice,
                    descrizione=d.descrizione,
                    importo_spesa=d.importo_spesa,
                    percentuale=d.percentuale_detrazione,
                    importo_detrazione=importo_detrazione,
                ))
                risultato.detrazioni_oneri += importo_detrazione

        risultato.detrazioni_totali = (
            risultato.detrazioni_lavoro
            + risultato.detrazioni_pensione
            + risultato.detrazioni_famiglia
            + risultato.detrazioni_oneri
        )

        # Cap quoziente familiare (art. 16-ter TUIR)
        risultato.detrazioni_oneri = self._cap_quoziente_familiare(
            contribuente, reddito_complessivo, risultato.detrazioni_oneri, regole
        )
        risultato.detrazioni_totali = (
            risultato.detrazioni_lavoro
            + risultato.detrazioni_pensione
            + risultato.detrazioni_famiglia
            + risultato.detrazioni_oneri
        )
        risultato.detrazioni_totali = min(risultato.detrazioni_totali, risultato.imposta_lorda)

        # Sterilizzazione > 200.000 €
        if regole.SogliaSterilizzazioneReddito > 0 and reddito_complessivo > regole.SogliaSterilizzazioneReddito:
            risultato.detrazioni_lavoro = Decimal(0)
            risultato.detrazioni_pensione = Decimal(0)
            risultato.detrazioni_famiglia = Decimal(0)
            detrazioni_ridotte = max(Decimal(0), risultato.detrazioni_totali - regole.SterilizzazioneDetrazioniImporto)
            risultato.sterilizzazione_detrazioni = risultato.detrazioni_totali - detrazioni_ridotte
            risultato.detrazioni_totali = detrazioni_ridotte

        risultato.imposta_netta = max(Decimal(0), risultato.imposta_lorda - risultato.detrazioni_totali)

        # Addizionali
        risultato.addizionale_regionale = self._calcola_addizionale_regionale(contribuente, reddito_imponibile, regole)
        risultato.addizionale_comunale = self._calcola_addizionale_comunale(contribuente, reddito_imponibile, regole)
        risultato.totale_irpef = risultato.imposta_netta + risultato.addizionale_regionale + risultato.addizionale_comunale

        return risultato

    def _calcola_detrazione_lavoro(self, c: Contribuente, reddito_imponibile: Decimal, regole) -> Decimal:
        if c.tipo not in (TipoContribuente.PersonaFisica, TipoContribuente.PartitaIvaOrdinaria):
            return Decimal(0)

        no_tax_area = regole.NoTaxAreaLavoroDipendente
        if reddito_imponibile <= no_tax_area:
            return Decimal(0)

        if reddito_imponibile <= Decimal(15000):
            detrazione = regole.DetrazioneLavoroPrimaFascia
            if detrazione < Decimal(690):
                detrazione = Decimal(690)
        elif reddito_imponibile <= Decimal(28000):
            detrazione = Decimal(1910) + Decimal(1190) * ((Decimal(28000) - reddito_imponibile) / Decimal(13000))
        elif reddito_imponibile <= Decimal(50000):
            detrazione = Decimal(1910) * ((Decimal(50000) - reddito_imponibile) / Decimal(22000))
        else:
            detrazione = Decimal(0)

        # Bonus +65 € tra 25.000 e 35.000 € (dal 2025)
        if Decimal(25000) < reddito_imponibile < Decimal(35000):
            detrazione += regole.DetrazioneLavoroBonus25_35

        return round2(max(Decimal(0), detrazione))

    def _calcola_detrazione_pensione(self, reddito_imponibile: Decimal, regole) -> Decimal:
        if reddito_imponibile <= Decimal(0) or regole.DetrazionePensioneMax <= 0:
            return Decimal(0)

        if reddito_imponibile <= regole.NoTaxAreaPensione:
            detrazione = regole.DetrazionePensioneMax
            detrazione = max(detrazione, regole.DetrazionePensioneMinimo)
        elif reddito_imponibile <= regole.SogliaPensioneSecondaFascia:
            ampiezza = regole.SogliaPensioneSecondaFascia - regole.NoTaxAreaPensione
            if ampiezza <= 0:
                ampiezza = Decimal(19500)
            detrazione = regole.DetrazionePensioneBaseSecondaFascia + regole.DetrazionePensioneIncrementoSecondaFascia * (
                (regole.SogliaPensioneSecondaFascia - reddito_imponibile) / ampiezza
            )
        elif reddito_imponibile <= regole.SogliaPensioneTerzaFascia:
            ampiezza = regole.SogliaPensioneTerzaFascia - regole.SogliaPensioneSecondaFascia
            if ampiezza <= 0:
                ampiezza = Decimal(22000)
            detrazione = regole.DetrazionePensioneBaseSecondaFascia * (
                (regole.SogliaPensioneTerzaFascia - reddito_imponibile) / ampiezza
            )
        else:
            return Decimal(0)

        if (regole.SogliaBonusDetrazionePensioneMin < reddito_imponibile <= regole.SogliaBonusDetrazionePensioneMax
                and regole.BonusDetrazionePensione25_29 > 0):
            detrazione += regole.BonusDetrazionePensione25_29

        return round2(max(Decimal(0), detrazione))

    def _calcola_detrazioni_famiglia(self, c: Contribuente, reddito_imponibile: Decimal) -> Decimal:
        if c.tipo not in (TipoContribuente.PersonaFisica, TipoContribuente.PartitaIvaOrdinaria):
            return Decimal(0)

        detrazioni = Decimal(0)

        if c.coniuge_carico:
            if reddito_imponibile <= Decimal(15000):
                coniuge = Decimal(800)
            elif reddito_imponibile <= Decimal(40000):
                coniuge = Decimal(800) - Decimal(110) * ((reddito_imponibile - Decimal(15000)) / Decimal(25000))
            elif reddito_imponibile <= Decimal(80000):
                coniuge = Decimal(690) * ((Decimal(80000) - reddito_imponibile) / Decimal(40000))
            else:
                coniuge = Decimal(0)
            detrazioni += max(Decimal(0), coniuge)

        if c.figli_carico > 0:
            base_figlio = Decimal(1220) if c.figli_carico > 3 else Decimal(950)
            detrazione_figli = base_figlio * c.figli_carico

            figli_minori = min(c.figli_minori_tre_anni, c.figli_carico)
            detrazione_figli += Decimal(200) * figli_minori

            if c.figli_carico > 3:
                detrazione_figli += Decimal(400) * (c.figli_carico - 3)

            detrazione_figli += Decimal(400) * min(c.figli_disabili, c.figli_carico)

            if reddito_imponibile > Decimal(95000):
                coeff = max(Decimal(0), (Decimal(125000) - reddito_imponibile) / Decimal(30000))
                detrazione_figli = Decimal(200) * figli_minori + (detrazione_figli - Decimal(200) * figli_minori) * coeff

            detrazioni += max(Decimal(0), detrazione_figli)

        return round2(detrazioni)

    def _calcola_detrazione_oneri(self, d: DetrazioneIrpef) -> Decimal:
        spesa_ammessa = min(d.importo_spesa, d.limite_massimo) if d.limite_massimo is not None else d.importo_spesa
        return max(Decimal(0), spesa_ammessa * d.percentuale_detrazione)

    def _cap_quoziente_familiare(self, c: Contribuente, reddito_complessivo: Decimal, detrazioni_oneri: Decimal, regole) -> Decimal:
        if regole.SogliaQuozienteFamiliareMin <= 0:
            return detrazioni_oneri
        if reddito_complessivo <= regole.SogliaQuozienteFamiliareMin:
            return detrazioni_oneri

        base_spesa = (
            regole.BaseQuozienteFamiliareSotto75_100
            if reddito_complessivo <= regole.SogliaQuozienteFamiliareMax
            else regole.BaseQuozienteFamiliareOltre100
        )

        if c.figli_carico >= 3 or c.figli_disabili > 0:
            coeff = regole.QuozienteFamiliareCoefficienti[3] if len(regole.QuozienteFamiliareCoefficienti) > 3 else Decimal(1)
        else:
            idx = c.figli_carico if c.figli_carico >= 0 else 0
            coeff = regole.QuozienteFamiliareCoefficienti[idx] if len(regole.QuozienteFamiliareCoefficienti) > idx else Decimal(1)

        limite_spesa = base_spesa * coeff

        if (regole.SogliaDecalageQuoziente > 0
                and reddito_complessivo > regole.SogliaDecalageQuoziente
                and regole.DecalageQuozienteMassimo > regole.SogliaDecalageQuoziente):
            quota = (regole.DecalageQuozienteMassimo - reddito_complessivo) / (
                regole.DecalageQuozienteMassimo - regole.SogliaDecalageQuoziente
            )
            limite_spesa = max(Decimal(0), limite_spesa * quota)

        limite_detrazione = limite_spesa * Decimal("0.19")
        return min(detrazioni_oneri, round2(limite_detrazione))

    def _calcola_addizionale_regionale(self, c: Contribuente, reddito_imponibile: Decimal, regole) -> Decimal:
        chiave_regione = _PROVINCIA_REGIONE.get((c.provincia_residenza or "").upper())
        if chiave_regione is None:
            chiave_regione = c.provincia_residenza or ""

        addizionale = regole.AddizionaliRegionali.get(chiave_regione) or regole.AddizionaliRegionali.get("Default")

        if addizionale is None or reddito_imponibile <= 0:
            return Decimal(0)

        aliquota = addizionale.aliquota_base
        if len(addizionale.scaglioni) > 0 and len(addizionale.aliquote) > len(addizionale.scaglioni):
            indice = sum(1 for s in addizionale.scaglioni if reddito_imponibile > s)
            aliquota = addizionale.aliquote[min(indice, len(addizionale.aliquote) - 1)]

        return round2(reddito_imponibile * aliquota)

    def _calcola_addizionale_comunale(self, c: Contribuente, reddito_imponibile: Decimal, regole) -> Decimal:
        comune = self._risolvi_addizionale_comunale(c.comune_residenza or "", regole)

        if comune is None or reddito_imponibile <= 0:
            return Decimal(0)

        if comune.soglia_esenzione > 0 and reddito_imponibile <= comune.soglia_esenzione:
            return Decimal(0)

        aliquota = comune.aliquota
        if (comune.scaglioni and comune.aliquote and len(comune.aliquote) > len(comune.scaglioni)):
            indice = sum(1 for s in comune.scaglioni if reddito_imponibile > s)
            aliquota = comune.aliquote[min(indice, len(comune.aliquote) - 1)]

        return round2(reddito_imponibile * aliquota)

    def _risolvi_addizionale_comunale(self, comune_inserito: str, regole) -> AddizionaleComunale | None:
        if not comune_inserito or not comune_inserito.strip():
            return regole.AddizionaliComunali.get("Default")

        target = self._normalizza_nome_comune(comune_inserito)

        # 1. Match esatto normalizzato
        for chiave, valore in regole.AddizionaliComunali.items():
            if self._normalizza_nome_comune(chiave) == target:
                return valore

        # 2. Match "inizia con"
        for chiave, valore in regole.AddizionaliComunali.items():
            chiave_norm = self._normalizza_nome_comune(chiave)
            if len(chiave_norm) > 0 and target.startswith(chiave_norm):
                return valore

        # 3. Fallback
        return regole.AddizionaliComunali.get("Default")

    @staticmethod
    def _normalizza_nome_comune(nome: str) -> str:
        s = nome.strip().lower()
        for sep in ("(", ","):
            idx = s.find(sep)
            if idx > 0:
                s = s[:idx].rstrip()
        s = s.replace("l'", "").replace("L'", "")
        while "  " in s:
            s = s.replace("  ", " ")
        s = (s.replace("à", "a").replace("á", "a").replace("â", "a")
              .replace("è", "e").replace("é", "e").replace("ê", "e").replace("ë", "e")
              .replace("ì", "i").replace("í", "i").replace("î", "i")
              .replace("ò", "o").replace("ó", "o").replace("ô", "o")
              .replace("ù", "u").replace("ú", "u").replace("û", "u"))
        return s
