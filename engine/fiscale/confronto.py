"""Confronto regimi fiscali (port di ConfrontoRegimiService.cs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import Contribuente


@dataclass
class AnnoProiezione:
    anno: int
    forfettario_imposta: Decimal = Decimal(0)
    ordinario_imposta: Decimal = Decimal(0)
    forfettario_cumulato: Decimal = Decimal(0)
    ordinario_cumulato: Decimal = Decimal(0)


@dataclass
class RisultatoConfronto:
    forfettario: Decimal = Decimal(0)
    ordinario: Decimal = Decimal(0)
    risparmio: Decimal = Decimal(0)
    break_even: int = 0
    forfettario_conveniente: bool = True
    anni_proiezione: list = field(default_factory=list)
    dettaglio: list = field(default_factory=list)


class ConfrontoRegimiService:
    def confronta(self, contribuente: Contribuente, ricavi: Decimal, spese: Decimal,
                  anno: int, anni_orizzonte: int = 5) -> RisultatoConfronto:
        regole = getattr(self, "_regole", None)

        # Regime ordinario (IRPEF)
        reddito_imponibile = max(Decimal(0), ricavi - spese)
        imposta_ordinario = self._irpef_semplificata(reddito_imponibile, anno)

        # Regime forfettario
        coefficiente = Decimal("0.78")
        reddito_forfettario = ricavi * coefficiente
        aliquota = Decimal("0.15")
        imposta_forfettario = reddito_forfettario * aliquota

        proiezioni: list[AnnoProiezione] = []
        for i in range(anni_orizzonte):
            anno_p = anno + i
            crescita = (Decimal(1) + Decimal("0.02")) ** i
            ricavi_p = ricavi * crescita
            spese_p = spese * crescita
            imponibile_p = max(Decimal(0), ricavi_p - spese_p)
            forf_p = ricavi_p * coefficiente * aliquota
            ord_p = self._irpef_semplificata(imponibile_p, anno_p)
            cum_forf = forf_p if i == 0 else proiezioni[i - 1].forfettario_cumulato + forf_p
            cum_ord = ord_p if i == 0 else proiezioni[i - 1].ordinario_cumulato + ord_p
            proiezioni.append(AnnoProiezione(
                anno=anno_p,
                forfettario_imposta=round2(forf_p),
                ordinario_imposta=round2(ord_p),
                forfettario_cumulato=round2(cum_forf),
                ordinario_cumulato=round2(cum_ord),
            ))

        risparmio = imposta_ordinario - imposta_forfettario
        conveniente = risparmio > 0
        break_even = 0
        if conveniente:
            for p in proiezioni:
                if p.forfettario_cumulato >= p.ordinario_cumulato:
                    break_even = p.anno
                    break

        return RisultatoConfronto(
            forfettario=round2(imposta_forfettario),
            ordinario=round2(imposta_ordinario),
            risparmio=round2(risparmio),
            break_even=break_even,
            forfettario_conveniente=conveniente,
            anni_proiezione=proiezioni,
        )

    def _irpef_semplificata(self, reddito: Decimal, anno: int) -> Decimal:
        imposta = Decimal(0)
        if reddito <= Decimal(28000):
            imposta = reddito * Decimal("0.23")
        elif reddito <= Decimal(50000):
            imposta = Decimal(28000) * Decimal("0.23") + (reddito - Decimal(28000)) * Decimal("0.35")
        else:
            imposta = (Decimal(28000) * Decimal("0.23") + Decimal(22000) * Decimal("0.35")
                       + (reddito - Decimal(50000)) * Decimal("0.43"))
        detrazione = Decimal(1910) * ((Decimal(50000) - reddito) / Decimal(22000))
        return max(Decimal(0), imposta - max(Decimal(0), detrazione))
