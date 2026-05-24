"""Pure settlement calculations (no DB / settings imports)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def split_prize_pool_rupees(total: Decimal, winner_count: int) -> list[Decimal]:
    """Split ``total`` rupees across ``winner_count`` winners; remainder goes to lowest ranks in 1-paisa steps."""
    if winner_count <= 0:
        return []
    if total <= 0:
        return [Decimal("0")] * winner_count
    total_paise = int((total * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP))
    base = total_paise // winner_count
    remainder = total_paise % winner_count
    return [Decimal(base + (1 if i < remainder else 0)) / Decimal("100") for i in range(winner_count)]
