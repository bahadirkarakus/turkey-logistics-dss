"""
Transportation LP Model — PuLP solver wrapper.
"""

from __future__ import annotations
import pulp


def solve(supply: dict, demand: dict, cost: dict) -> dict:
    """
    Solves the transportation problem.

    Parameters
    ----------
    supply : {source: capacity}
    demand : {warehouse: demand}
    cost   : {source: {warehouse: cost_per_unit}}

    Returns
    -------
    {
        "status": str,
        "total_cost": float,
        "shipments": {(source, warehouse): units},
        "slack": {source: unused_capacity},
        "demand_met": {warehouse: units_received},
        "lp_model": pulp.LpProblem   (for sensitivity / debug)
    }
    """
    sources    = list(supply.keys())
    warehouses = list(demand.keys())

    prob = pulp.LpProblem("TurkeyLogistics", pulp.LpMinimize)

    # Decision variables: x[i][j] >= 0
    x = {
        (i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0)
        for i in sources
        for j in warehouses
    }

    # Objective: minimise total transportation cost
    prob += pulp.lpSum(cost[i][j] * x[i, j]
                       for i in sources for j in warehouses)

    # Supply constraints (<=)
    for i in sources:
        prob += pulp.lpSum(x[i, j] for j in warehouses) <= supply[i], f"supply_{i}"

    # Demand constraints (>=)
    for j in warehouses:
        prob += pulp.lpSum(x[i, j] for i in sources) >= demand[j], f"demand_{j}"

    # Solve (suppress solver output)
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {
            "status": status,
            "total_cost": None,
            "shipments": {},
            "slack": {},
            "demand_met": {},
            "lp_model": prob,
        }

    shipments  = {}
    for i in sources:
        for j in warehouses:
            val = x[i, j].varValue or 0.0
            if val > 0.001:
                shipments[(i, j)] = round(val, 2)

    slack = {
        i: round(supply[i] - sum(
            (x[i, j].varValue or 0) for j in warehouses
        ), 2)
        for i in sources
    }

    demand_met = {
        j: round(sum((x[i, j].varValue or 0) for i in sources), 2)
        for j in warehouses
    }

    return {
        "status": status,
        "total_cost": round(pulp.value(prob.objective), 2),
        "shipments": shipments,
        "slack": slack,
        "demand_met": demand_met,
        "lp_model": prob,
    }


def formulation_text(supply: dict, demand: dict) -> str:
    """Returns a readable LP formulation string."""
    sources    = list(supply.keys())
    warehouses = list(demand.keys())
    n, m       = len(sources), len(warehouses)

    lines = [
        "**Matematiksel Formülasyon — Ulaştırma Problemi (LP)**",
        "",
        f"**Kümeler:**  I = {{{', '.join(sources)}}}",
        f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        f"J = {{{', '.join(warehouses)}}}",
        "",
        "**Parametreler:**",
        "- $c_{ij}$ = birim taşıma maliyeti (TL/birim), kaynak $i$ → depo $j$",
        "- $s_i$   = arz kapasitesi, kaynak $i$",
        "- $d_j$   = talep, depo $j$",
        "",
        "**Karar Değişkenleri:**",
        "$$x_{ij} \\geq 0 \\quad \\forall i \\in I, j \\in J$$",
        "",
        "**Amaç Fonksiyonu (Minimize):**",
        "$$Z = \\sum_{i \\in I} \\sum_{j \\in J} c_{ij} x_{ij}$$",
        "",
        "**Arz Kısıtları:**",
        "$$\\sum_{j \\in J} x_{ij} \\leq s_i \\quad \\forall i \\in I$$",
        "",
        "**Talep Kısıtları:**",
        "$$\\sum_{i \\in I} x_{ij} \\geq d_j \\quad \\forall j \\in J$$",
        "",
        f"**Model Boyutu:** {n*m} karar değişkeni, "
        f"{n} arz + {m} talep = {n+m} kısıt",
        "",
        f"**Toplam Arz:** {sum(supply.values())} birim",
        f"**Toplam Talep:** {sum(demand.values())} birim",
        f"**Fazla Kapasite:** {sum(supply.values()) - sum(demand.values())} birim",
    ]
    return "\n".join(lines)
