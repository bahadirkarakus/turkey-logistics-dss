"""Tests for data layer — network topology, cost/CO₂ matrices, scenarios."""

import pytest

from data import (
    DISTANCES,
    PARAMS,
    SCENARIOS,
    SOURCES,
    TOLLS,
    WAREHOUSES,
    compute_co2_matrix,
    compute_cost_matrix,
    get_scenario_data,
)


class TestNetworkStructure:
    def test_source_count(self):
        assert len(SOURCES) == 5

    def test_warehouse_count(self):
        assert len(WAREHOUSES) == 8

    def test_distance_matrix_shape(self):
        assert len(DISTANCES) == 5
        assert all(len(row) == 8 for row in DISTANCES.values())

    def test_toll_matrix_shape(self):
        assert len(TOLLS) == 5
        assert all(len(row) == 8 for row in TOLLS.values())

    def test_all_distances_positive(self):
        for src, row in DISTANCES.items():
            for d in row:
                assert d > 0, f"Non-positive distance for {src}"

    def test_all_tolls_non_negative(self):
        for src, row in TOLLS.items():
            for t in row:
                assert t >= 0, f"Negative toll for {src}"

    def test_supply_exceeds_demand(self):
        total_supply = sum(s["capacity"] for s in SOURCES.values())
        total_demand = sum(w["demand"] for w in WAREHOUSES.values())
        assert total_supply > total_demand, "Supply must exceed demand (unbalanced problem)"

    def test_total_supply(self):
        assert sum(s["capacity"] for s in SOURCES.values()) == 2650

    def test_total_demand(self):
        assert sum(w["demand"] for w in WAREHOUSES.values()) == 1610


class TestCostMatrix:
    def test_shape(self):
        cost = compute_cost_matrix()
        assert len(cost) == 5
        assert all(len(v) == 8 for v in cost.values())

    def test_all_positive(self):
        cost = compute_cost_matrix()
        for src, row in cost.items():
            for wh, c in row.items():
                assert c > 0, f"Non-positive cost: {src} → {wh}"

    def test_fuel_multiplier_scales_linearly(self):
        base = compute_cost_matrix(fuel_multiplier=1.0)
        up20 = compute_cost_matrix(fuel_multiplier=1.2)
        for src in base:
            for wh in base[src]:
                ratio = up20[src][wh] / base[src][wh]
                assert abs(ratio - 1.2) < 0.01, \
                    f"Fuel multiplier not applied linearly on {src}→{wh}"

    def test_closer_city_cheaper(self):
        """Ankara→Eskişehir should be cheaper than Ankara→Diyarbakır."""
        cost = compute_cost_matrix()
        assert cost["Ankara"]["Eskişehir"] < cost["Ankara"]["Diyarbakır"]


class TestCO2Matrix:
    def test_shape(self, co2_matrix):
        assert len(co2_matrix) == 5
        assert all(len(v) == 8 for v in co2_matrix.values())

    def test_all_positive(self, co2_matrix):
        for row in co2_matrix.values():
            for v in row.values():
                assert v > 0

    def test_proportional_to_distance(self, co2_matrix):
        """İstanbul→Diyarbakır CO₂ > İstanbul→Eskişehir CO₂ (longer route)."""
        assert co2_matrix["İstanbul"]["Diyarbakır"] > co2_matrix["İstanbul"]["Eskişehir"]

    def test_ipcc_factor(self):
        """Manually verify IPCC CO₂ factor is applied correctly."""
        from data import DISTANCES
        warehouses = list(WAREHOUSES.keys())
        co2 = compute_co2_matrix()
        src = "Adana"
        wh  = "Gaziantep"
        j   = warehouses.index(wh)
        d   = DISTANCES[src][j]
        expected = round(
            d * (PARAMS["fuel_consumption_per_100km"] / 100)
            * PARAMS["co2_kg_per_litre"]
            / PARAMS["truck_capacity_units"],
            3,
        )
        assert co2[src][wh] == expected


class TestScenarios:
    def test_scenario_count(self):
        assert len(SCENARIOS) == 4

    def test_scenario_names(self):
        assert set(SCENARIOS.keys()) == {
            "Normal Season", "Summer Season",
            "Fuel Increase (+20%)", "Winter Season",
        }

    @pytest.mark.parametrize("scenario", list(SCENARIOS.keys()))
    def test_scenario_returns_valid_data(self, scenario):
        supply, demand, cost = get_scenario_data(scenario)
        assert len(supply) == 5
        assert len(demand) == 8
        assert all(v > 0 for v in supply.values())
        assert all(v > 0 for v in demand.values())

    def test_summer_season_antalya_higher(self):
        _, demand_normal, _ = get_scenario_data("Normal Season")
        _, demand_summer, _ = get_scenario_data("Summer Season")
        assert demand_summer["Antalya"] > demand_normal["Antalya"]

    def test_fuel_increase_higher_cost(self):
        _, _, cost_normal = get_scenario_data("Normal Season")
        _, _, cost_fuel   = get_scenario_data("Fuel Increase (+20%)")
        for src in cost_normal:
            for wh in cost_normal[src]:
                assert cost_fuel[src][wh] > cost_normal[src][wh]
