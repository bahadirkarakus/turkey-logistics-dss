"""
Turkey Logistics Network — Data Layer
Production centres → Warehouses transportation problem data.
"""

from __future__ import annotations
import requests

# ---------------------------------------------------------------------------
# NETWORK NODES
# ---------------------------------------------------------------------------

SOURCES = {
    "İstanbul": {"capacity": 800, "lat": 41.0082, "lon": 28.9784, "color": "#E74C3C"},
    "Ankara":   {"capacity": 600, "lat": 39.9334, "lon": 32.8597, "color": "#E74C3C"},
    "İzmir":    {"capacity": 500, "lat": 38.4189, "lon": 27.1287, "color": "#E74C3C"},
    "Bursa":    {"capacity": 400, "lat": 40.1885, "lon": 29.0610, "color": "#E74C3C"},
    "Adana":    {"capacity": 350, "lat": 37.0000, "lon": 35.3213, "color": "#E74C3C"},
}

WAREHOUSES = {
    "Konya":      {"demand": 250, "lat": 37.8667, "lon": 32.4833, "color": "#2ECC71"},
    "Kayseri":    {"demand": 200, "lat": 38.7312, "lon": 35.4787, "color": "#2ECC71"},
    "Trabzon":    {"demand": 150, "lat": 41.0015, "lon": 39.7178, "color": "#2ECC71"},
    "Gaziantep":  {"demand": 220, "lat": 37.0662, "lon": 37.3833, "color": "#2ECC71"},
    "Antalya":    {"demand": 280, "lat": 36.8969, "lon": 30.7133, "color": "#2ECC71"},
    "Samsun":     {"demand": 180, "lat": 41.2867, "lon": 36.3300, "color": "#2ECC71"},
    "Eskişehir":  {"demand": 160, "lat": 39.7767, "lon": 30.5206, "color": "#2ECC71"},
    "Diyarbakır": {"demand": 170, "lat": 37.9144, "lon": 40.2306, "color": "#2ECC71"},
}

# ---------------------------------------------------------------------------
# DISTANCES (km) — Google Maps approximations
# ---------------------------------------------------------------------------
#           Konya  Kayseri  Trabzon  Gaziantep  Antalya  Samsun  Eskişehir  Diyarbakır
DISTANCES = {
    "İstanbul": [550,  770,  1100,  1130,  730,  730,  335,  1400],
    "Ankara":   [260,  340,   780,   660,  545,  420,  235,   940],
    "İzmir":    [560,  760,  1350,   980,  440, 1100,  535,  1250],
    "Bursa":    [510,  730,  1000,  1060,  680,  660,  155,  1330],
    "Adana":    [340,  330,   870,   220,  555,  760,  750,   430],
}

# HGS/OGS toll estimates per route (TL per truck)
TOLLS = {
    "İstanbul": [120, 180, 250, 260, 200, 200,  80, 320],
    "Ankara":   [ 60,  80, 180, 160, 140, 100,  50, 220],
    "İzmir":    [130, 180, 300, 230, 100, 260, 120, 290],
    "Bursa":    [110, 170, 230, 240, 180, 200,  40, 310],
    "Adana":    [ 80,  75, 200,  50, 130, 175, 170, 100],
}

# ---------------------------------------------------------------------------
# COST PARAMETERS
# ---------------------------------------------------------------------------
PARAMS = {
    "fuel_price_tl_per_litre": 40.0,     # TL/litre (motorin)
    "fuel_consumption_per_100km": 30.0,  # litre/100 km (TIR)
    "driver_wage_tl_per_hour": 150.0,    # TL/h
    "avg_speed_kmh": 80.0,               # km/h
    "load_fee_tl": 200.0,                # TL fixed loading/unloading
    "truck_capacity_units": 25,          # units per truck
}

# ---------------------------------------------------------------------------
# SCENARIOS
# ---------------------------------------------------------------------------
SCENARIOS = {
    "Normal Season": {
        "demand_multipliers": {w: 1.0 for w in WAREHOUSES},
        "fuel_multiplier": 1.0,
        "description": "Base scenario — standard demand and costs.",
    },
    "Summer Season": {
        "demand_multipliers": {
            "Konya": 1.0, "Kayseri": 1.0, "Trabzon": 1.20,
            "Gaziantep": 1.0, "Antalya": 1.40, "Samsun": 1.15,
            "Eskişehir": 1.0, "Diyarbakır": 1.0,
        },
        "fuel_multiplier": 1.0,
        "description": "Tourism season — Antalya +40%, Trabzon +20%, Samsun +15%.",
    },
    "Fuel Increase (+20%)": {
        "demand_multipliers": {w: 1.0 for w in WAREHOUSES},
        "fuel_multiplier": 1.20,
        "description": "All route costs increased by 20%.",
    },
    "Winter Season": {
        "demand_multipliers": {
            "Konya": 1.10, "Kayseri": 1.15, "Trabzon": 0.80,
            "Gaziantep": 1.05, "Antalya": 0.70, "Samsun": 0.90,
            "Eskişehir": 1.10, "Diyarbakır": 1.20,
        },
        "fuel_multiplier": 1.05,
        "description": "Winter season — inland cities up, coastal resorts down.",
    },
}


def compute_cost_matrix(fuel_multiplier: float = 1.0) -> dict:
    """
    Returns cost (TL per unit) for each (source, warehouse) pair.
    """
    p = PARAMS
    warehouses = list(WAREHOUSES.keys())
    sources    = list(SOURCES.keys())
    cost = {}

    for i, src in enumerate(sources):
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

def fetch_real_distances(timeout: int = 6) -> tuple[dict, dict]:
    """
    Fetches real road distances and durations via the public OSRM demo server.
    Returns (distances_km, durations_h) in the same shape as DISTANCES.
    Falls back to the hardcoded DISTANCES on any error.
    """
    sources    = list(SOURCES.keys())
    warehouses = list(WAREHOUSES.keys())
    base_url   = "http://router.project-osrm.org/route/v1/driving"

    new_distances: dict[str, list[float]] = {s: [] for s in sources}
    new_durations: dict[str, list[float]] = {s: [] for s in sources}

    try:
        for src in sources:
            src_lat = SOURCES[src]["lat"]
            src_lon = SOURCES[src]["lon"]
            for wh in warehouses:
                wh_lat = WAREHOUSES[wh]["lat"]
                wh_lon = WAREHOUSES[wh]["lon"]
                url = (f"{base_url}/{src_lon},{src_lat};"
                       f"{wh_lon},{wh_lat}?overview=false")
                r = requests.get(url, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                route = data["routes"][0]
                new_distances[src].append(round(route["distance"] / 1000, 1))  # m → km
                new_durations[src].append(round(route["duration"] / 3600, 2))  # s → h
    except Exception:
        # Return hardcoded fallback
        durations = {
            src: [DISTANCES[src][j] / PARAMS["avg_speed_kmh"]
                  for j in range(len(warehouses))]
            for src in sources
        }
        return DISTANCES, durations

    return new_distances, new_durations
