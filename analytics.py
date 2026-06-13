"""
Analytics module — Sensitivity Analysis, Monte Carlo, Multi-Objective Pareto.
"""

from __future__ import annotations
import numpy as np
import pulp
from data import DISTANCES, WAREHOUSES, SOURCES, PARAMS


# ---------------------------------------------------------------------------
# SENSITIVITY ANALYSIS
# ---------------------------------------------------------------------------

def sensitivity_analysis(supply: dict, demand: dict, cost: dict) -> dict:
    """
    Returns shadow prices (dual variables) and reduced costs via PuLP/CBC.

    Shadow price of supply constraint i  : cost saving per extra unit of supply
    Shadow price of demand constraint j  : extra cost per extra unit of demand
    Reduced cost of non-basic route (i,j): how much cost[i][j] must drop
                                           before that route enters the solution
    """
    sources    = list(supply.keys())
    warehouses = list(demand.keys())

    prob = pulp.LpProblem("Sensitivity", pulp.LpMinimize)

    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
         for i in sources for j in warehouses}

    prob += pulp.lpSum(cost[i][j] * x[i, j]
                       for i in sources for j in warehouses)

    for i in sources:
        prob += (pulp.lpSum(x[i, j] for j in warehouses) <= supply[i],
                 f"supply_{i}")

    for j in warehouses:
        prob += (pulp.lpSum(x[i, j] for i in sources) >= demand[j],
                 f"demand_{j}")

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    shadow_supply, shadow_demand, reduced_costs, shipments = {}, {}, {}, {}

    for i in sources:
        pi = prob.constraints.get(f"supply_{i}")
        shadow_supply[i] = round(pi.pi or 0, 2) if pi else 0

    for j in warehouses:
        pi = prob.constraints.get(f"demand_{j}")
        shadow_demand[j] = round(pi.pi or 0, 2) if pi else 0

    for i in sources:
        for j in warehouses:
            val = x[i, j].varValue or 0
            dj  = x[i, j].dj      or 0
            if val > 0.001:
                shipments[(i, j)]    = round(val, 2)
            else:
                reduced_costs[(i, j)] = round(dj, 2)

    return {
        "status":        pulp.LpStatus[prob.status],
        "base_cost":     round(pulp.value(prob.objective), 2),
        "shadow_supply": shadow_supply,
        "shadow_demand": shadow_demand,
        "reduced_costs": reduced_costs,
        "shipments":     shipments,
    }


# ---------------------------------------------------------------------------
# MONTE CARLO SIMULATION
# ---------------------------------------------------------------------------

def monte_carlo(supply: dict, demand: dict, cost: dict,
                n_simulations: int = 300,
                demand_cv: float = 0.15) -> dict:
    """
    Runs N LP solves with normally distributed demand (coeff. of variation = cv).
    Returns cost distribution and per-route reliability.
    """
    from model import solve

    sources    = list(supply.keys())
    warehouses = list(demand.keys())
    base_dem   = np.array([demand[w] for w in warehouses], dtype=float)
    total_sup  = sum(supply.values())

    costs_list   = []
    route_counts = {(s, w): 0 for s in sources for w in warehouses}
    route_vols   = {(s, w): [] for s in sources for w in warehouses}
    n_infeasible = 0

    rng = np.random.default_rng(42)

    for _ in range(n_simulations):
        sampled = rng.normal(base_dem, demand_cv * base_dem)
        sampled = np.clip(sampled, 0, 2 * base_dem).astype(int)

        # Rescale if infeasible
        if sampled.sum() > total_sup:
            sampled = (sampled * total_sup / sampled.sum()).astype(int)

        sim_demand = {w: int(sampled[k]) for k, w in enumerate(warehouses)}

        result = solve(supply, sim_demand, cost)
        if result["status"] == "Optimal":
            costs_list.append(result["total_cost"])
            for (s, w), v in result["shipments"].items():
                route_counts[(s, w)] += 1
                route_vols[(s, w)].append(v)
        else:
            n_infeasible += 1

    n_ok = len(costs_list)
    arr  = np.array(costs_list)

    return {
        "n_simulations":    n_simulations,
        "n_feasible":       n_ok,
        "n_infeasible":     n_infeasible,
        "costs":            costs_list,
        "mean_cost":        round(float(np.mean(arr)), 2)           if n_ok else 0,
        "std_cost":         round(float(np.std(arr)), 2)            if n_ok else 0,
        "p5_cost":          round(float(np.percentile(arr, 5)), 2)  if n_ok else 0,
        "p95_cost":         round(float(np.percentile(arr, 95)), 2) if n_ok else 0,
        "route_reliability": {
            k: round(v / n_ok * 100, 1) if n_ok else 0
            for k, v in route_counts.items()
        },
        "route_avg_vol": {
            k: round(float(np.mean(v)), 1) if v else 0
            for k, v in route_vols.items()
        },
    }


# ---------------------------------------------------------------------------
# MULTI-OBJECTIVE PARETO FRONTIER
# ---------------------------------------------------------------------------

def multi_objective_pareto(supply: dict, demand: dict, cost: dict,
                            n_points: int = 12) -> dict:
    """
    Computes Pareto frontier: cost vs. total weighted travel time.
    Uses weighted-sum scalarisation with adaptive normalisation.
    """
    sources    = list(supply.keys())
    warehouses = list(WAREHOUSES.keys())
    speed      = PARAMS["avg_speed_kmh"]
    cap        = PARAMS["truck_capacity_units"]

    # Travel-time per unit (hours/unit) for each route
    time_per_unit = {
        i: {j: (DISTANCES[i][k] / speed) / cap
            for k, j in enumerate(warehouses)}
        for i in sources
    }

    def _solve(alpha: float):
        prob = pulp.LpProblem(f"mo_{alpha:.3f}", pulp.LpMinimize)
        x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
             for i in sources for j in warehouses}

        cost_obj = pulp.lpSum(cost[i][j] * x[i, j]
                              for i in sources for j in warehouses)
        time_obj = pulp.lpSum(time_per_unit[i][j] * x[i, j]
                              for i in sources for j in warehouses)

        # Normalise to [0,1] using rough scale factors
        prob += alpha * (cost_obj / 500_000) + (1 - alpha) * (time_obj / 2000)

        for i in sources:
            prob += pulp.lpSum(x[i, j] for j in warehouses) <= supply[i]
        for j in warehouses:
            prob += pulp.lpSum(x[i, j] for i in sources) >= demand[j]

        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        if pulp.LpStatus[prob.status] != "Optimal":
            return None, None

        tc = sum(cost[i][j] * (x[i, j].varValue or 0)
                 for i in sources for j in warehouses)
        tt = sum(time_per_unit[i][j] * (x[i, j].varValue or 0)
                 for i in sources for j in warehouses)
        return round(tc, 0), round(tt, 2)

    alphas = np.linspace(0.0, 1.0, n_points)
    points = []
    for a in alphas:
        c, t = _solve(float(a))
        if c is not None:
            points.append({"alpha": round(float(a), 3), "cost": c, "time": t})

    # Remove dominated points
    pareto = [
        p for p in points
        if not any(
            q["cost"] <= p["cost"] and q["time"] <= p["time"] and q != p
            for q in points
        )
    ]

    return {"pareto": pareto, "all_points": points}
