"""Benefici per il lavoratore dipendente (port di BeneficiLavoratoreCalculator.cs).

- 2024: esonero contributivo 7%/6% su soglie 25k/35k (non entra nel netto);
- dal 2025: bonus IRPEF esente progressivo (7,1/5,3/4,8% su 8.500/15.000/20.000)
  + ulteriore detrazione 1.000 € (20-40k);
- trattamento integrativo (ex bonus 100 €, art. 1 D.L. 3/2020) per tutte le annualità.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import round2
from .models import Contribuente, TipoReddito


@dataclass
class RisultatoBenefici:
    esonero_contributi: Decimal = Decimal(0)
    bonus_cuneo: Decimal = Decimal(0)
    ulteriore_detrazione: Decimal = Decimal(0)
    trattamento_integrativo: Decimal = Decimal(0)


class BeneficiLavoratoreCalculator:
    def calcola(self, contribuente: Contribuente, redditi, irpef, regole) -> RisultatoBenefici:
        redditi_da_lavoro = [r for r in redditi if r.tipo == TipoReddito.LavoroDipendente]
        if not redditi_da_lavoro or irpef is None:
            return RisultatoBenefici()

        reddito_complessivo = sum((r.importo_lordo for r in redditi), Decimal(0))

        esonero = Decimal(0)
        bonus_cuneo = Decimal(0)
        ulteriore_detrazione = Decimal(0)
        if regole.Anno >= 2025 and len(regole.CuneoBonusAliquote) > 0:
            bonus_cuneo = self._calcola_bonus_cuneo(reddito_complessivo, regole)
            ulteriore_detrazione = self._calcola_ulteriore_detrazione(reddito_complessivo, regole)
        else:
            esonero = self._calcola_esonero(redditi_da_lavoro, regole)

        trattamento = self._calcola_trattamento(reddito_complessivo, irpef, regole)

        return RisultatoBenefici(
            esonero_contributi=round2(esonero),
            bonus_cuneo=round2(bonus_cuneo),
            ulteriore_detrazione=round2(ulteriore_detrazione),
            trattamento_integrativo=round2(trattamento),
        )

    def _calcola_bonus_cuneo(self, reddito_complessivo: Decimal, regole) -> Decimal:
        soglie = regole.CuneoBonusSoglie
        aliquote = regole.CuneoBonusAliquote
        if not soglie or not aliquote or reddito_complessivo > soglie[-1]:
            return Decimal(0)

        bonus = Decimal(0)
        precedente = Decimal(0)
        for i in range(min(len(soglie), len(aliquote))):
            massimo = min(reddito_complessivo, soglie[i])
            if massimo > precedente:
                bonus += (massimo - precedente) * aliquote[i]
            precedente = massimo

        return round2(bonus)

    def _calcola_ulteriore_detrazione(self, reddito_complessivo: Decimal, regole) -> Decimal:
        if reddito_complessivo <= regole.CuneoUlterioreDetrazioneSogliaMin:
            return Decimal(0)

        if reddito_complessivo <= regole.CuneoUlterioreDetrazioneSogliaPiena:
            return regole.CuneoUlterioreDetrazioneMax

        if reddito_complessivo < regole.CuneoUlterioreDetrazioneSogliaMax:
            riduzione = regole.CuneoUlterioreDetrazioneSogliaMax - reddito_complessivo
            ampiezza = regole.CuneoUlterioreDetrazioneSogliaMax - regole.CuneoUlterioreDetrazioneSogliaPiena
            return regole.CuneoUlterioreDetrazioneMax * riduzione / ampiezza

        return Decimal(0)

    def _calcola_esonero(self, redditi_da_lavoro, regole) -> Decimal:
        soglie = regole.EsoneroContributiSoglie or []
        aliquote = regole.EsoneroContributiAliquote or []
        if not soglie or not aliquote:
            return Decimal(0)

        totale = Decimal(0)
        for reddito in redditi_da_lavoro:
            aliquota = Decimal(0)
            for i in range(len(soglie)):
                if i == 0:
                    if reddito.importo_lordo <= soglie[i] and aliquote:
                        aliquota = aliquote[0]
                elif reddito.importo_lordo > soglie[i - 1] and reddito.importo_lordo <= soglie[i] and len(aliquote) > i:
                    aliquota = aliquote[i]

            if aliquota <= 0:
                continue

            importo_massimo = round2(reddito.importo_lordo * aliquota)
            esonero_reddito = min(reddito.contributi_previdenziali, importo_massimo)
            totale += max(Decimal(0), esonero_reddito)

        return round2(min(totale, sum((r.contributi_previdenziali for r in redditi_da_lavoro), Decimal(0))))

    def _calcola_trattamento(self, reddito_complessivo: Decimal, irpef, regole) -> Decimal:
        base_bonus = regole.TrattamentoIntegrativoBase
        if base_bonus <= 0 or reddito_complessivo > regole.TrattamentoIntegrativoSogliaMax or irpef is None:
            return Decimal(0)

        detrazione = irpef.detrazioni_lavoro
        capienza = max(Decimal(0), irpef.imposta_lorda - detrazione)
        importo = min(base_bonus, capienza)

        return round2(max(Decimal(0), importo))
