"""Liquidazione IVA (port di LiquidazioneIvaService.cs)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import round2
from .models import TipologiaMovimentoIva, TipoScadenza


@dataclass
class MovimentoIva:
    data: object = None
    imponibile: Decimal = Decimal(0)
    aliquota: Decimal = Decimal(0)
    tipologia: TipologiaMovimentoIva = TipologiaMovimentoIva.Vendita
    descrizione: str = ""


@dataclass
class DettaglioIva:
    aliquota: Decimal = Decimal(0)
    tipologia: str = ""
    imponibile: Decimal = Decimal(0)
    iva: Decimal = Decimal(0)


@dataclass
class RisultatoLiquidazioneIva:
    periodo: str = ""
    iva_debito: Decimal = Decimal(0)
    iva_credito: Decimal = Decimal(0)
    iva_da_versare: Decimal = Decimal(0)
    dettaglio: list = field(default_factory=list)


class LiquidazioneIvaService:
    def calcola(self, movimenti: list[MovimentoIva], periodo: str = "") -> RisultatoLiquidazioneIva:
        iva_debito = Decimal(0)
        iva_credito = Decimal(0)
        dettaglio_raggruppato: dict = {}

        for m in movimenti:
            imponibile = m.imponibile
            iva = round2(imponibile * m.aliquota)

            chiave = (m.aliquota, m.tipologia.value)
            if chiave not in dettaglio_raggruppato:
                dettaglio_raggruppato[chiave] = {"imponibile": Decimal(0), "iva": Decimal(0)}
            dettaglio_raggruppato[chiave]["imponibile"] += imponibile
            dettaglio_raggruppato[chiave]["iva"] += iva

            if m.tipologia == TipologiaMovimentoIva.Vendita:
                iva_debito += iva
            elif m.tipologia == TipologiaMovimentoIva.Acquisto:
                iva_credito += iva

        dettaglio = [
            DettaglioIva(
                aliquota=aliquota,
                tipologia=tipologia,
                imponibile=round2(v["imponibile"]),
                iva=round2(v["iva"]),
            )
            for (aliquota, tipologia), v in sorted(dettaglio_raggruppato.items(), key=lambda kv: (str(kv[0][1]), kv[0][0]))
        ]

        iva_debito = round2(iva_debito)
        iva_credito = round2(iva_credito)
        iva_da_versare = max(Decimal(0), iva_debito - iva_credito)

        return RisultatoLiquidazioneIva(
            periodo=periodo,
            iva_debito=iva_debito,
            iva_credito=iva_credito,
            iva_da_versare=iva_da_versare,
            dettaglio=dettaglio,
        )
