"""Tests for the LP transportation model."""

import pytest

from data import SOURCES, WAREHOUSES, get_scenario_data
from model import formulation_text, solve


class TestSolveOptimality:
    def test_status_optimal(self, normal_result):
        assert normal_result["status"] == "Optimal"

    def test_total_cost_positive(self, normal_result):
        assert normal_result["total_cost"] > 0

    def test_active_routes_exist(self, normal_result):
        assert len(normal_result["shipments"]) > 0

    def test_active_routes_at_most_40(self, normal_result):
        assert len(normal_result["shipments"]) <= 40

    def test_demand_fully_met(self, normal_result, normal_season):
        _, demand, _ = normal_season
        for wh, met in normal_result["demand_met"].items():
            assert met >= demand[wh] - 0.01, \
                f"Demand not met at {wh}: need {demand[wh]}, got {met}"

    def test_supply_not_exceeded(self, normal_result, normal_season):
        supply, _, _ = normal_season
        for src, slack in normal_result["slack"].items():
            assert slack >= -0.01, f"Supply exceeded at {src}"

    def test_all_shipments_positive(self, normal_result):
        for (s, w), v in normal_result["shipments"].items():
            assert v > 0, f"Non-positive shipment on {s}→{w}"

    def test_slack_non_negative(self, normal_result):
        for src, slack in normal_result["slack"].items():
            assert slack >= -0.01, f"Negative slack at {src}"


class TestSolveCost:
    def test_known_cost_range(self, normal_result):
        """Normal Season total cost should be in a plausible range."""
        assert 50_000 < normal_result["total_cost"] < 1_000_000

    def test_fuel_increase_costs_more(self):
        _, d, c_normal = get_scenario_data("Normal Season")
        s, _, _ = get_scenario_data("Normal Season")
        _, _, c_fuel = get_scenario_data("Fuel Increase (+20%)")
        r_normal = solve(s, d, c_normal)
        r_fuel   = solve(s, d, c_fuel)
        assert r_fuel["total_cost"] > r_normal["total_cost"]

    @pytest.mark.parametrize("scenario", [
        "Normal Season", "Summer Season",
        "Fuel Increase (+20%)", "Winter Season",
    ])
    def test_all_scenarios_optimal(self, scenario):
        supply, demand, cost = get_scenario_data(scenario)
        result = solve(supply, demand, cost)
        assert result["status"] == "Optimal"


class TestSolveInfeasible:
    def test_infeasible_when_demand_exceeds_supply(self):
        supply = {s: 10 for s in SOURCES}
        demand = {w: 1000 for w in WAREHOUSES}
        _, _, cost = get_scenario_data("Normal Season")
        result = solve(supply, demand, cost)
        assert result["status"] != "Optimal"
        assert result["total_cost"] is None
        assert result["shipments"] == {}


class TestFormulationText:
    def test_returns_string(self, normal_season):
        supply, demand, _ = normal_season
        text = formulation_text(supply, demand)
        assert isinstance(text, str)
        assert len(text) > 100

    def test_contains_key_terms(self, normal_season):
        supply, demand, _ = normal_season
        text = formulation_text(supply, demand)
        assert "Minimize" in text or "minimize" in text.lower()
        assert "Supply" in text or "supply" in text.lower()
        assert "Demand" in text or "demand" in text.lower()


class TestCO2Budget:
    def test_no_budget_still_optimal(self, normal_result):
        assert normal_result["status"] == "Optimal"

    def test_tight_budget_makes_infeasible(self, normal_season, co2_matrix):
        supply, demand, cost = normal_season
        result = solve(supply, demand, cost,
                       co2_matrix=co2_matrix, co2_budget=1.0)
        assert result["status"] != "Optimal"

    def test_loose_budget_stays_optimal(self, normal_season, co2_matrix):
        supply, demand, cost = normal_season
        result = solve(supply, demand, cost,
                       co2_matrix=co2_matrix, co2_budget=999_999)
        assert result["status"] == "Optimal"

    def test_budget_respected(self, normal_season, co2_matrix):
        supply, demand, cost = normal_season
        # Compute baseline CO₂
        base = solve(supply, demand, cost)
        baseline_co2 = sum(
            co2_matrix[s][w] * v
            for (s, w), v in base["shipments"].items()
        )
        # Use 90% as budget
        budget = baseline_co2 * 0.90
        result = solve(supply, demand, cost,
                       co2_matrix=co2_matrix, co2_budget=budget)
        if result["status"] == "Optimal":
            actual_co2 = sum(
                co2_matrix[s][w] * v
                for (s, w), v in result["shipments"].items()
            )
            assert actual_co2 <= budget + 0.01

    def test_co2_matrix_none_ignores_budget(self, normal_season):
        supply, demand, cost = normal_season
        result = solve(supply, demand, cost,
                       co2_matrix=None, co2_budget=1.0)
        assert result["status"] == "Optimal"
