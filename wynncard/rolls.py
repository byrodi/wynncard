"""Identification rolls the way Wynntils works them out, so an editor only offers values the game can roll.

An identification has a base value, the item API's `raw`. Identifying the item rolls an internal
percentage, 30 to 130 for a positive base and 70 to 130 for a negative one, and the value is the base
scaled by it, rounded and never zero. The roll percentage the mod prints is where the value sits
between the worst and the best value the base can give. Spell costs are worked out on the negated base
and turned back for display, which only changes the way halves round.

After Wynntils' StatCalculator (calculatePossibleValuesRange, calculateStatValue, getPercentage).
"""
from decimal import ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal


def values(base: int, inverted: bool = False) -> list[int]:
    """Every value an identification with this base can roll, as printed, from the worst roll to the best.

    `inverted` is the stat table's flag for spell costs. A base of 0 means the item has no such stat.
    """
    stored = -base if inverted else base
    rolls = range(30, 131) if stored > 0 else range(70, 131)
    found = sorted({_scaled(stored, roll, inverted) for roll in rolls})
    return [-value if inverted else value for value in found]


def percentage(value: int, base: int, inverted: bool = False) -> float | None:
    """The roll percentage Wynntils prints for `value`; None for a base that can only roll one value."""
    possible = values(base, inverted)
    worst, best = possible[0], possible[-1]
    if worst == best:
        return None
    return (value - worst) / (best - worst) * 100


def _scaled(stored: int, roll: int, inverted: bool) -> int:
    """`stored * roll / 100` rounded like Wynntils: half away from zero for positive bases, towards zero
    for negative ones, the other way round for spell costs."""
    mode = ROUND_HALF_UP if (stored > 0) != inverted else ROUND_HALF_DOWN
    value = int((Decimal(stored) * roll / 100).quantize(Decimal(1), rounding=mode))
    return value or (1 if stored > 0 else -1)
