from __future__ import annotations

from ._amount_data import COMBINATIONS as _COMBINATIONS

_COMBINATION_CACHE: set[tuple[str, str]] = set(_COMBINATIONS)


def load_amount_combinations() -> set[tuple[str, str]]:
    """Return the set of amount combinations ported from Jiten."""
    return _COMBINATION_CACHE
