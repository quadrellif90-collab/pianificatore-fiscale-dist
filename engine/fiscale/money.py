"""Helper aritmetici per il motore fiscale.

Il motore C# usa `decimal` con `Math.Round(x, 2)` che applica il banker's
rounding (round-half-even). Per replicare esattamente la golden truth di
TaxPlanner Italia ogni arrotondamento usa Decimal + ROUND_HALF_EVEN.
"""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


def d(value) -> Decimal:
    """Converte un valore in Decimal nel modo più fedele possibile."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def round2(value) -> Decimal:
    """Math.Round(x, 2) in banker's rounding (ROUND_HALF_EVEN)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_EVEN)


def round0(value) -> Decimal:
    """Arrotondamento a intero (banker's rounding), usato per il break-even."""
    return Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
