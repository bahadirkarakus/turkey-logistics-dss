"""
Multi-Period Transportation LP — 4-quarter planning horizon.

Decision variables
------------------
x[i, j, t]  : units shipped from source i to warehouse j in quarter t
inv[i, t]    : inventory held at source i at end of quarter t

Objective
---------
Minimize  Σ_t Σ_ij  c_ij * x_ijt   (transport cost)
        + Σ_t Σ_i   h   * inv_it   (holding cost)

Constraints
-----------
Inventory balance  : inv[i,t] = inv[i,t-1] + prod[i] - Σ_j x[i,j,t]
Demand fulfilment  : Σ_i x[i,j,t] >= d[j,t]   ∀ j, t
Non-negativity     : x[i,j,t], inv[i,t] >= 0
Initial inventory  : inv[i,0] = 0
"""

from __future__ import annotations
import pulp
from data import SOURCES, WAREHOUSES, SCENARIOS, compute_cost_matrix

# Quarterly demand multipliers per scenario
# Format: {scenario_name: [Q1_mult, Q2_mult, Q3_mult, Q4_mult]}
QUARTER_MULTIPLIERS: dict[str, list[float]] = {
    "Normal Season":       [1.00, 1.00, 1.00, 1.00],
    "Summer Season":       [0.85, 1.25, 1.40, 0.80],
    "Fuel Increase (+20%)": [1.00, 1.00, 1.00, 1.00],
    "Winter Season":       [1.20, 0.90, 0.75, 1.15],
}

HOLDING_COST_PER_UNIT_PER_QUARTER = 5.0   # TL
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]


def solve_multiperiod(
    scenario: str = "Normal Season",
    holding_cost: float = HOLDING_COST_PER_UNIT_PER_QUARTER,
    custom_supply: dict | None = None,
    custom_demand: dict | None = None,
) -> dict:
    """
    Solves the 4-quarter transportation LP.

    Returns
    -------
    {
        "status": str,
        "total_cost": float,
        "transport_cost": float,
        "holding_cost": float,
        "quarters": [
            {
                "period": "Q1",
                "shipments": {(src, wh): units},
                "inventory": {src: units},
                "transport_cost": float,
                "demand": {wh: units},
            }, ...
        ]
    }
    """
    sources    = list(SOURCES.keys())
    warehouses = list(WAREHOUSES.keys())
    T          = len(QUARTERS)

    scen       = SCENARIOS[scenario]
    base_cost  = compute_cost_matrix(scen["fuel_multiplier"])

    base_supply = custom_supply or {s: SOURCES[s]["capacity"] for s in sources}
    base_demand = custom_demand or {w: WAREHOUSES[w]["demand"] for w in warehouses}

    # Production per quarter = annual capacity / 4
    prod = {s: base_supply[s] / T for s in sources}

    # Quarterly demand = base_demand * warehouse_multiplier * quarter_multiplier
    q_mult = QUARTER_MULTIPLIERS.get(scenario, [1.0] * T)
    wh_mult = scen["demand_multipliers"]

    demand_qt: dict[tuple[str, int], float] = {}
    for t, qm in enumerate(q_mult):
        for w in warehouses:
            # Annual demand split into quarters with seasonal multiplier
            demand_qt[(w, t)] = round(base_demand[w] / T * wh_mult[w] * qm)

    # ── Build LP ─────────────────────────────────────────────────────────────
    prob = pulp.LpProblem("MultiPeriodLogistics", pulp.LpMinimize)

    x = {
        (i, j, t): pulp.LpVariable(f"x_{i}_{j}_{t}", lowBound=0)
        for i in sources
        for j in warehouses
        for t in range(T)
    }

    inv = {
        (i, t): pulp.LpVariable(f"inv_{i}_{t}", lowBound=0)
        for i in sources
        for t in range(T)
    }

    # Objective
    transport_obj = pulp.lpSum(
        base_cost[i][j] * x[i, j, t]
        for i in sources for j in warehouses for t in range(T)
    )
    holding_obj = pulp.lpSum(
        holding_cost * inv[i, t]
        for i in sources for t in range(T)
    )
    prob += transport_obj + holding_obj

    # Inventory balance
    for i in sources:
        for t in range(T):
            shipped = pulp.lpSum(x[i, j, t] for j in warehouses)
            if t == 0:
                prob += inv[i, t] == prod[i] - shipped, f"invbal_{i}_0"
            else:
                prob += inv[i, t] == inv[i, t-1] + prod[i] - shipped, \
                       f"invbal_{i}_{t}"

    # Demand constraints
    for j in warehouses:
        for t in range(T):
            prob += (
                pulp.lpSum(x[i, j, t] for i in sources) >= demand_qt[(j, t)],
                f"demand_{j}_{t}",
            )

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {"status": status, "total_cost": None, "quarters": []}

    # ── Extract results ───────────────────────────────────────────────────────
    quarters = []
    total_transport = 0.0
    total_holding   = 0.0

    for t, qname in enumerate(QUARTERS):
        shipments = {}
        qt_cost   = 0.0
        for i in sources:
            for j in warehouses:
                v = x[i, j, t].varValue or 0.0
                if v > 0.001:
                    shipments[(i, j)] = round(v, 2)
                    qt_cost += base_cost[i][j] * v

        inventory = {
            i: round(inv[i, t].varValue or 0.0, 2)
            for i in sources
        }
        qt_hold = sum(holding_cost * v for v in inventory.values())
        total_transport += qt_cost
        total_holding   += qt_hold

        quarters.append({
            "period":         qname,
            "shipments":      shipments,
            "inventory":      inventory,
            "transport_cost": round(qt_cost, 2),
            "holding_cost":   round(qt_hold, 2),
            "demand":         {w: demand_qt[(w, t)] for w in warehouses},
        })

    return {
        "status":         status,
        "total_cost":     round(total_transport + total_holding, 2),
        "transport_cost": round(total_transport, 2),
        "holding_cost":   round(total_holding, 2),
        "quarters":       quarters,
    }
