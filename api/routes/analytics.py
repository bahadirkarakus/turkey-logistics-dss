"""Analytics endpoints — sensitivity, Monte Carlo, Pareto."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import APIRouter, HTTPException

from analytics import monte_carlo, multi_objective_pareto, sensitivity_analysis
from api.schemas import (
    MonteCarloRequest,
    MonteCarloResponse,
    ParetoPoint,
    ParetoRequest,
    ParetoResponse,
    SensitivityRequest,
    SensitivityResponse,
)
from data import SCENARIOS, get_scenario_data

router = APIRouter(tags=["Analytics"])


@router.post("/sensitivity", response_model=SensitivityResponse)
def sensitivity_endpoint(req: SensitivityRequest):
    if req.scenario not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}")
    supply, demand, cost = get_scenario_data(req.scenario,
                            custom_fuel_mult=req.fuel_multiplier if req.fuel_multiplier != 1.0 else None)
    result = sensitivity_analysis(supply, demand, cost)
    # Flatten (src,wh) tuple keys to "src→wh" strings
    rc = {f"{s}→{w}": v for (s, w), v in result["reduced_costs"].items()}
    return SensitivityResponse(
        status=result["status"],
        base_cost=result["base_cost"],
        shadow_supply=result["shadow_supply"],
        shadow_demand=result["shadow_demand"],
        reduced_costs=rc,
    )


@router.post("/monte-carlo", response_model=MonteCarloResponse)
def monte_carlo_endpoint(req: MonteCarloRequest):
    if req.scenario not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}")
    supply, demand, cost = get_scenario_data(req.scenario)
    mc = monte_carlo(supply, demand, cost, req.n_simulations, req.demand_cv)
    # Flatten route keys
    reliability = {f"{s}→{w}": v for (s, w), v in mc["route_reliability"].items()}
    return MonteCarloResponse(
        n_simulations=mc["n_simulations"],
        n_feasible=mc["n_feasible"],
        n_infeasible=mc["n_infeasible"],
        mean_cost=mc["mean_cost"],
        std_cost=mc["std_cost"],
        p5_cost=mc["p5_cost"],
        p95_cost=mc["p95_cost"],
        route_reliability=reliability,
    )


@router.post("/pareto", response_model=ParetoResponse)
def pareto_endpoint(req: ParetoRequest):
    if req.scenario not in SCENARIOS:
        raise HTTPException(400, f"Unknown scenario: {req.scenario}")
    supply, demand, cost = get_scenario_data(req.scenario)
    result = multi_objective_pareto(supply, demand, cost, req.n_points)
    return ParetoResponse(
        pareto=[ParetoPoint(**p) for p in result["pareto"]],
        all_points=[ParetoPoint(**p) for p in result["all_points"]],
    )
