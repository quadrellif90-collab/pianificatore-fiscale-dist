"""Cuneo fiscale: esoneri contributivi per datori di lavoro (port di CuneoFiscaleService.cs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import VoceCuneo


@dataclass
class CalcoloCuneoFiscale:
    esonero_totale: Decimal = Decimal(0)
    voci: list = field(default_factory=list)
    dettaglio: list = field(default_factory=list)


class CuneoFiscaleService:
    def calcola(self, costo_annuale: Decimal, anno: int, regole,
                tipo_dipendente: str = "ORDINARIO", eta: int = 0,
                sesso: str = "", percepisce_cigs_naspi: bool = False,
                mese_assunzione: int = 1, regime_precedente: str = "") -> CalcoloCuneoFiscale:
        voci: list[VoceCuneo] = []
        esonero_totale = Decimal(0)

        if anno == 2024 and costo_annuale <= regole.EsoneroContributiSoglie[0]:
            esonero = round2(costo_annuale * Decimal("0.07"))
            esonero_totale += esonero
            voci.append(VoceCuneo(
                etichetta="Esonero contributivo 2024 (7%)", valore=esonero,
                colore="", percentuale=0.0, is_costo=False))

        elif anno == 2025:
            if costo_annuale <= regole.EsoneroContributiSoglie[0]:
                esonero = round2(costo_annuale * Decimal("0.05"))
            elif costo_annuale <= regole.EsoneroContributiSoglie[1]:
                esonero = round2(costo_annuale * Decimal("0.03"))
            else:
                esonero = Decimal(0)
            esonero_totale += esonero
            voci.append(VoceCuneo(
                etichetta="Sgravio contributivo 2025", valore=esonero,
                colore="", percentuale=0.0, is_costo=False))

        elif anno in (2026, 2027):
            if tipo_dipendente == "UNDER_36":
                if not percepisce_cigs_naspi:
                    limite = regole.LimiteEsoneroUnder36
                    base = min(costo_annuale, limite)
                    esonero = round2(base * regole.AliquotaContributiDatore)
                    esonero_totale += esonero
                    voci.append(VoceCuneo(
                        etichetta="Esonero under 36 (max 3.000 €/anno)", valore=esonero,
                        colore="", percentuale=0.0, is_costo=False))
                else:
                    voci.append(VoceCuneo(
                        etichetta="Esonero under 36 (escluso CIGS/NASpI)", valore=Decimal(0),
                        colore="", percentuale=0.0, is_costo=False))
            elif tipo_dipendente == "DONNE":
                if not percepisce_cigs_naspi:
                    esonero = round2(costo_annuale * regole.DecontribuzioneDonne2026)
                    esonero_totale += esonero
                    voci.append(VoceCuneo(
                        etichetta="Decontribuzione donne 2026", valore=esonero,
                        colore="", percentuale=0.0, is_costo=False))
                else:
                    voci.append(VoceCuneo(
                        etichetta="Decontribuzione donne 2026 (escluso CIGS/NASpI)", valore=Decimal(0),
                        colore="", percentuale=0.0, is_costo=False))
            elif tipo_dipendente == "CIGS_NASPI":
                esonero = round2(costo_annuale * regole.IncentivoCIGS_NASpI)
                esonero_totale += esonero
                voci.append(VoceCuneo(
                    etichetta="Incentivo CIGS/NASpI", valore=esonero,
                    colore="", percentuale=0.0, is_costo=False))
            elif tipo_dipendente == "OVER_50":
                esonero = round2(costo_annuale * regole.IncentivoOver50)
                esonero_totale += esonero
                voci.append(VoceCuneo(
                    etichetta="Incentivo over 50", valore=esonero,
                    colore="", percentuale=0.0, is_costo=False))
            elif tipo_dipendente == "ZES":
                esonero = round2(costo_annuale * regole.IncentivoZES)
                esonero_totale += esonero
                voci.append(VoceCuneo(
                    etichetta="Incentivo ZES", valore=esonero,
                    colore="", percentuale=0.0, is_costo=False))
            else:
                voci.append(VoceCuneo(
                    etichetta="Nessun incentivo applicabile", valore=Decimal(0),
                    colore="", percentuale=0.0, is_costo=False))

        else:
            voci.append(VoceCuneo(
                etichetta="Nessun incentivo per l'anno selezionato", valore=Decimal(0),
                colore="", percentuale=0.0, is_costo=False))

        return CalcoloCuneoFiscale(esonero_totale=esonero_totale, voci=voci)
