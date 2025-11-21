"""OMEGA: strategic_stops is deprecated.

This module is kept only as a placeholder to avoid import errors.
All legacy volatility-range-based stop/target logic has been removed
to comply with institutional risk standards.

Use src/features/institutional_sl_tp.py instead.
"""

from typing import Any

def deprecated(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError(
        "strategic_stops is deprecated in PLAN OMEGA; use institutional_sl_tp instead."
    )
