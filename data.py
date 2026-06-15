"""
Turkey Logistics Network — Data Layer

The network (production centres, warehouses, distances, tolls), cost parameters
and scenarios are **not hardcoded** here — they are loaded at import time from
editable files under ``network/`` (CSV + YAML). Point the ``NETWORK_DIR``
environment variable at another directory to model a completely different
network without touching any code.

Individual cost parameters can also be overridden via environment variables,
e.g. ``FUEL_PRICE_TL_PER_LITRE=55`` overrides ``fuel_price_tl_per_litre``.
"""

from __future__ import annotations

import csv
import functools
import os
from pathlib import Path

import requests
import yaml

# ---------------------------------------------------------------------------
# NETWORK DIRECTORY
# ---------------------------------------------------------------------------
NETWORK_DIR = Path(os.getenv("NETWORK_DIR", Path(__file__).parent / "network"))


# ---------------------------------------------------------------------------
# LOADERS
# ---------------------------------------------------------------------------
def _load_nodes(filename: str, value_key: str) -> dict:
    """
    Reads a node CSV (sources / warehouses) into the canonical dict shape:
        {name: {value_key: int, "lat": float, "lon": float, "color": str}}
    """
    nodes: dict[str, dict] = {}
    with open(NETWORK_DIR / filename, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            nodes[row["name"]] = {
                value_key: int(row[value_key]),
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "color": row["color"],
            }
    return nodes


def _load_matrix(filename: str, warehouse_order: list[str]) -> dict:
    """
    Reads a source×warehouse matrix CSV into ``{source: [values...]}`` with
    values ordered to match ``warehouse_order`` (so downstream integer indexing
    stays valid regardless of column order in the file).
    """
    matrix: dict[str, list[float]] = {}
    with open(NETWORK_DIR / filename, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            src = row["source"]
            matrix[src] = [float(row[wh]) for wh in warehouse_order]
    return matrix


def _env_param(key: str, default: float) -> float:
    """Returns a cost parameter, overridable via an UPPER_SNAKE env variable."""
    raw = os.getenv(key.upper())
    return float(raw) if raw is not None else float(default)


def _load_config() -> tuple[dict, dict]:
    """Loads (PARAMS, SCENARIOS) from config.yaml, applying env overrides to params."""
    with open(NETWORK_DIR / "config.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    params = {k: _env_param(k, v) for k, v in cfg["params"].items()}
    # truck_capacity_units is conceptually an int
    params["truck_capacity_units"] = int(params["truck_capacity_units"])
    return params, cfg["scenarios"]


# ---------------------------------------------------------------------------
# NETWORK DATA (loaded at import)
# ---------------------------------------------------------------------------
SOURCES = _load_nodes("sources.csv", "capacity")
WAREHOUSES = _load_nodes("warehouses.csv", "demand")

_WAREHOUSE_ORDER = list(WAREHOUSES.keys())
DISTANCES = _load_matrix("distances.csv", _WAREHOUSE_ORDER)   # km
TOLLS = _load_matrix("tolls.csv", _WAREHOUSE_ORDER)           # TL per truck

PARAMS, SCENARIOS = _load_config()


# ---------------------------------------------------------------------------
# DERIVED MATRICES
# ---------------------------------------------------------------------------
def compute_co2_matrix() -> dict:
    """Returns CO₂ emissions (kg per unit shipped) for each (source, warehouse) pair."""
    p          = PARAMS
    warehouses = list(WAREHOUSES.keys())
    sources    = list(SOURCES.keys())
    co2        = {}
    for src in sources:
        co2[src] = {}
        for j, wh in enumerate(warehouses):
            d               = DISTANCES[src][j]
            litres_per_trip = d * (p["fuel_consumption_per_100km"] / 100)
            kg_per_trip     = litres_per_trip * p["co2_kg_per_litre"]
            co2[src][wh]    = round(kg_per_trip / p["truck_capacity_units"], 3)
    return co2


def compute_cost_matrix(fuel_multiplier: float = 1.0) -> dict:
    """Returns cost (TL per unit) for each (source, warehouse) pair."""
    p = PARAMS
    warehouses = list(WAREHOUSES.keys())
    sources    = list(SOURCES.keys())
    cost = {}

    for src in sources:
        cost[src] = {}
        for j, wh in enumerate(warehouses):
            d   = DISTANCES[src][j]
            tol = TOLLS[src][j]
            fuel_cost   = d * (p["fuel_consumption_per_100km"] / 100) * p["fuel_price_tl_per_litre"]
            driver_cost = (d / p["avg_speed_kmh"]) * p["driver_wage_tl_per_hour"]
            total_trip  = (fuel_cost + driver_cost + tol + p["load_fee_tl"]) * fuel_multiplier
            cost[src][wh] = round(total_trip / p["truck_capacity_units"], 2)

    return cost


def get_scenario_data(scenario_name: str,
                      custom_supply: dict | None = None,
                      custom_demand: dict | None = None,
                      custom_fuel_mult: float | None = None):
    """
    Returns (supply, demand, cost_matrix) for the given scenario,
    with optional custom overrides.
    """
    scen = SCENARIOS[scenario_name]
    fuel_mult = custom_fuel_mult if custom_fuel_mult is not None else scen["fuel_multiplier"]

    supply = {s: (custom_supply[s] if custom_supply else SOURCES[s]["capacity"])
              for s in SOURCES}

    demand = {}
    for w in WAREHOUSES:
        base = custom_demand[w] if custom_demand else WAREHOUSES[w]["demand"]
        demand[w] = round(base * scen["demand_multipliers"][w])

    cost = compute_cost_matrix(fuel_mult)
    return supply, demand, cost


# ---------------------------------------------------------------------------
# OSRM — Real road distances (optional, falls back to DISTANCES on failure)
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=4)
def fetch_real_distances(timeout: int = 6) -> tuple[dict, dict]:
    """
    Fetches real road distances and durations via the public OSRM demo server.

    Uses a single OSRM ``/table`` request (one round-trip for the whole matrix
    instead of one request per source/warehouse pair) and caches the result for
    the process lifetime. Returns (distances_km, durations_h) in the same shape
    as DISTANCES. Falls back to the hardcoded DISTANCES on any error.
    """
    sources    = list(SOURCES.keys())
    warehouses = list(WAREHOUSES.keys())

    # OSRM expects lon,lat;lon,lat;... — sources first, then warehouses.
    coords = ";".join(
        f"{SOURCES[s]['lon']},{SOURCES[s]['lat']}" for s in sources
    ) + ";" + ";".join(
        f"{WAREHOUSES[w]['lon']},{WAREHOUSES[w]['lat']}" for w in warehouses
    )
    n_src = len(sources)
    src_idx = ";".join(str(i) for i in range(n_src))
    dst_idx = ";".join(str(n_src + j) for j in range(len(warehouses)))

    url = (
        f"http://router.project-osrm.org/table/v1/driving/{coords}"
        f"?sources={src_idx}&destinations={dst_idx}"
        f"&annotations=distance,duration"
    )

    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        dist_m = data["distances"]   # metres, [n_src][n_dst]
        dur_s  = data["durations"]   # seconds

        new_distances = {
            src: [round(dist_m[i][j] / 1000, 1) for j in range(len(warehouses))]
            for i, src in enumerate(sources)
        }
        new_durations = {
            src: [round(dur_s[i][j] / 3600, 2) for j in range(len(warehouses))]
            for i, src in enumerate(sources)
        }
        return new_distances, new_durations
    except Exception:
        # Hardcoded fallback (durations derived from distance / avg speed).
        durations = {
            src: [DISTANCES[src][j] / PARAMS["avg_speed_kmh"]
                  for j in range(len(warehouses))]
            for src in sources
        }
        return DISTANCES, durations
