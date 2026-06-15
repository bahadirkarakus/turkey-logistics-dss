"""
Central solver factory for all PuLP models.

Keeps solver selection in one place so every module (model, analytics,
multiperiod, pmedian, …) stays consistent and can switch backends without
edits scattered across the codebase.

The backend is chosen via the ``LP_SOLVER`` environment variable:

    LP_SOLVER=cbc     → CBC / COIN (PuLP's bundled default)
    LP_SOLVER=highs   → HiGHS (faster, modern; requires `highspy`)

Falls back to CBC if the requested backend is unavailable.
"""

from __future__ import annotations

import os

import pulp

_DEFAULT_BACKEND = os.getenv("LP_SOLVER", "cbc").strip().lower()


def get_solver(backend: str | None = None, msg: bool = False) -> pulp.LpSolver:
    """
    Returns a configured PuLP solver instance.

    Parameters
    ----------
    backend : "cbc" | "highs" | None
        Solver backend. ``None`` uses the ``LP_SOLVER`` env var (default "cbc").
    msg : bool
        Whether the solver prints its log to stdout.
    """
    name = (backend or _DEFAULT_BACKEND).strip().lower()

    if name in ("highs", "highspy"):
        try:
            return pulp.HiGHS_CMD(msg=msg)
        except (pulp.PulpError, AttributeError, Exception):
            # HiGHS not installed / not on PATH → fall back to CBC.
            pass

    return pulp.PULP_CBC_CMD(msg=msg)
