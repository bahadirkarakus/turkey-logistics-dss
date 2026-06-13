"""
P-Median Facility Location — finds p optimal hub locations from candidate cities
to minimise total demand-weighted distance (km · units).
"""
from __future__ import annotations
import math
import pulp
from data import SOURCES, WAREHOUSES

# All 13 cities as candidate facility locations
ALL_LOCATIONS: dict[str, dict] = {
    **{k: {"lat": v["lat"], "lon": v["lon"]} for k, v in SOURCES.items()},
    **{k: {"lat": v["lat"], "lon": v["lon"]} for k, v in WAREHOUSES.items()},
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R  = 6_371.0
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a  = math.sin(Δφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def solve_pmedian(
    p:          int,
    demand:     dict[str, int] | None = None,
    candidates: list[str]      | None = None,
) -> dict:
    """
    Binary P-Median MIP.

    Decision variables
    ------------------
    y[j]    : 1 if facility j is opened
    x[i,j]  : 1 if demand node i is served by facility j

    Objective
    ---------
    Minimise Σ_ij demand[i] * dist(i,j) * x[i,j]

    Constraints
    -----------
    Σ_j y[j] = p
    Σ_j x[i,j] = 1        ∀ i
    x[i,j] ≤ y[j]         ∀ i, j
    x, y ∈ {0, 1}

    Parameters
    ----------
    p          : number of facilities to open
    demand     : {city: demand_units}  (default: WAREHOUSES)
    candidates : candidate facility names (default: all 13 cities)

    Returns
    -------
    {
        "status": str,
        "selected": [str],                  # p opened locations
        "assignment": {demand_node: str},
        "total_weighted_dist": float,       # Σ demand * km
        "dist_matrix": {node: {cand: km}},
    }
    """
    if demand is None:
        demand = {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES}
    if candidates is None:
        candidates = list(ALL_LOCATIONS.keys())

    demand_nodes = list(demand.keys())

    dist: dict[str, dict[str, float]] = {}
    for i in demand_nodes:
        loc_i  = ALL_LOCATIONS[i]
        dist[i] = {}
        for j in candidates:
            loc_j      = ALL_LOCATIONS[j]
            dist[i][j] = haversine(loc_i["lat"], loc_i["lon"],
                                   loc_j["lat"], loc_j["lon"])

    prob = pulp.LpProblem("PMedian", pulp.LpMinimize)

    y = {j: pulp.LpVariable(f"y_{j}", cat="Binary") for j in candidates}
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary")
         for i in demand_nodes for j in candidates}

    prob += pulp.lpSum(
        demand[i] * dist[i][j] * x[(i, j)]
        for i in demand_nodes for j in candidates
    )
    prob += pulp.lpSum(y[j] for j in candidates) == p, "p_open"
    for i in demand_nodes:
        prob += pulp.lpSum(x[(i, j)] for j in candidates) == 1, f"assign_{i}"
        for j in candidates:
            prob += x[(i, j)] <= y[j], f"link_{i}_{j}"

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {
            "status": status, "selected": [], "assignment": {},
            "total_weighted_dist": 0.0, "dist_matrix": dist,
        }

    selected = [j for j in candidates if (y[j].varValue or 0) > 0.5]
    assignment: dict[str, str] = {}
    for i in demand_nodes:
        for j in candidates:
            if (x[(i, j)].varValue or 0) > 0.5:
                assignment[i] = j
                break

    total_wd = sum(demand[i] * dist[i][assignment[i]] for i in demand_nodes)

    return {
        "status":              status,
        "selected":            selected,
        "assignment":          assignment,
        "total_weighted_dist": round(total_wd, 1),
        "dist_matrix":         dist,
    }
