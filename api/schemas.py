"""Pydantic request/response models for the Turkey Logistics API."""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Shared types ─────────────────────────────────────────────────────────────

Supply = dict[str, float]   # {source: capacity}
Demand = dict[str, float]   # {warehouse: demand}
Cost   = dict[str, dict[str, float]]  # {source: {warehouse: cost}}


# ── /solve ───────────────────────────────────────────────────────────────────

class SolveRequest(BaseModel):
    scenario:        str   = Field("Normal Season", description="Scenario name from SCENARIOS")
    fuel_multiplier: float = Field(1.0, ge=0.5, le=3.0)
    custom_supply:   Optional[Supply] = None
    custom_demand:   Optional[Demand] = None

class ShipmentItem(BaseModel):
    source:     str
    warehouse:  str
    units:      float
    unit_cost:  float
    total_cost: float
    co2_kg:     float

class SolveResponse(BaseModel):
    status:      str
    total_cost:  Optional[float]
    total_co2:   Optional[float]
    active_routes: int
    shipments:   list[ShipmentItem]
    slack:       dict[str, float]
    demand_met:  dict[str, float]


# ── /sensitivity ─────────────────────────────────────────────────────────────

class SensitivityRequest(BaseModel):
    scenario:        str   = "Normal Season"
    fuel_multiplier: float = Field(1.0, ge=0.5, le=3.0)

class SensitivityResponse(BaseModel):
    status:         str
    base_cost:      float
    shadow_supply:  dict[str, float]
    shadow_demand:  dict[str, float]
    reduced_costs:  dict[str, float]


# ── /monte-carlo ─────────────────────────────────────────────────────────────

class MonteCarloRequest(BaseModel):
    scenario:      str   = "Normal Season"
    n_simulations: int   = Field(300, ge=10, le=2000)
    demand_cv:     float = Field(0.15, ge=0.01, le=0.50)

class MonteCarloResponse(BaseModel):
    n_simulations:    int
    n_feasible:       int
    n_infeasible:     int
    mean_cost:        float
    std_cost:         float
    p5_cost:          float
    p95_cost:         float
    route_reliability: dict[str, float]


# ── /pareto ───────────────────────────────────────────────────────────────────

class ParetoRequest(BaseModel):
    scenario: str = "Normal Season"
    n_points: int = Field(12, ge=3, le=30)

class ParetoPoint(BaseModel):
    alpha: float
    cost:  float
    time:  float

class ParetoResponse(BaseModel):
    pareto:     list[ParetoPoint]
    all_points: list[ParetoPoint]


# ── /scenarios ────────────────────────────────────────────────────────────────

class ScenarioInfo(BaseModel):
    name:        str
    description: str
    fuel_multiplier: float
