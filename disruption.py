"""
Disruption simulation — models supply chain disruptions and computes re-routing.
"""
from __future__ import annotations

from model import solve


def simulate_disruption(
    supply:             dict[str, int],
    demand:             dict[str, int],
    cost:               dict[str, dict[str, float]],
    disabled_sources:   list[str]        = None,
    capacity_fractions: dict[str, float] = None,
) -> dict:
    """
    Compares the base optimal plan with a disrupted supply scenario.

    Parameters
    ----------
    disabled_sources   : sources with capacity forced to 0
    capacity_fractions : {source: fraction 0-1} for partial capacity cuts

    Returns
    -------
    {
        "base":             solve_result,
        "disrupted":        solve_result,
        "disrupted_supply": {source: int},
        "cost_delta":       float | None,
        "cost_delta_pct":   float | None,
        "lost_routes":      [(src, wh), ...],      # in base, gone in disrupted
        "new_routes":       [(src, wh), ...],      # appear in disrupted
        "unchanged_routes": [(src, wh), ...],
    }
    """
    disabled_sources   = disabled_sources   or []
    capacity_fractions = capacity_fractions or {}

    base_result = solve(supply, demand, cost)

    disrupted_supply = {
        s: (0 if s in disabled_sources
            else round(cap * capacity_fractions.get(s, 1.0)))
        for s, cap in supply.items()
    }
    disrupted_result = solve(disrupted_supply, demand, cost)

    base_ships      = set(base_result["shipments"])      if base_result["status"] == "Optimal" else set()
    disrupted_ships = set(disrupted_result["shipments"]) if disrupted_result["status"] == "Optimal" else set()

    cost_delta, cost_delta_pct = None, None
    if base_result["status"] == "Optimal" and disrupted_result["status"] == "Optimal":
        cost_delta     = disrupted_result["total_cost"] - base_result["total_cost"]
        cost_delta_pct = cost_delta / base_result["total_cost"] * 100

    return {
        "base":             base_result,
        "disrupted":        disrupted_result,
        "disrupted_supply": disrupted_supply,
        "cost_delta":       round(cost_delta, 2)     if cost_delta     is not None else None,
        "cost_delta_pct":   round(cost_delta_pct, 2) if cost_delta_pct is not None else None,
        "lost_routes":      list(base_ships - disrupted_ships),
        "new_routes":       list(disrupted_ships - base_ships),
        "unchanged_routes": list(base_ships & disrupted_ships),
    }
