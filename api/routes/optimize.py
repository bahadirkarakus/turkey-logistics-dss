"""Optimization endpoints."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import APIRouter, HTTPException

from api.schemas import ShipmentItem, SolveRequest, SolveResponse
from data import SCENARIOS, compute_co2_matrix, get_scenario_data
from model import solve

router = APIRouter(prefix="/solve", tags=["Optimization"])


@router.post("", response_model=SolveResponse)
def solve_endpoint(req: SolveRequest):
    if req.scenario not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}. "
                                 f"Valid: {list(SCENARIOS.keys())}")

    supply, demand, cost = get_scenario_data(
        req.scenario,
        custom_supply=req.custom_supply,
        custom_demand=req.custom_demand,
        custom_fuel_mult=req.fuel_multiplier if req.fuel_multiplier != 1.0 else None,
    )

    result = solve(supply, demand, cost)
    co2    = compute_co2_matrix()

    if result["status"] != "Optimal":
        return SolveResponse(
            status=result["status"],
            total_cost=None, total_co2=None, active_routes=0,
            shipments=[], slack={}, demand_met={},
        )

    items = []
    total_co2 = 0.0
    for (s, w), units in result["shipments"].items():
        uc      = cost[s][w]
        tc      = round(uc * units, 2)
        co2_kg  = round(co2[s][w] * units, 2)
        total_co2 += co2_kg
        items.append(ShipmentItem(
            source=s, warehouse=w, units=units,
            unit_cost=uc, total_cost=tc, co2_kg=co2_kg,
        ))

    return SolveResponse(
        status=result["status"],
        total_cost=result["total_cost"],
        total_co2=round(total_co2, 2),
        active_routes=len(items),
        shipments=sorted(items, key=lambda x: -x.units),
        slack=result["slack"],
        demand_met=result["demand_met"],
    )
