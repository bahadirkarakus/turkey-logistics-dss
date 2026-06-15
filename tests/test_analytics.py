"""Tests for analytics — sensitivity, Monte Carlo, Pareto."""

import pytest

from analytics import monte_carlo, multi_objective_pareto, sensitivity_analysis


class TestSensitivity:
    @pytest.fixture(scope="class")
    def sens(self, normal_season):
        supply, demand, cost = normal_season
        return sensitivity_analysis(supply, demand, cost)

    def test_status_optimal(self, sens):
        assert sens["status"] == "Optimal"

    def test_shadow_supply_count(self, sens):
        assert len(sens["shadow_supply"]) == 5

    def test_shadow_demand_count(self, sens):
        assert len(sens["shadow_demand"]) == 8

    def test_shadow_supply_non_positive(self, sens):
        """Supply shadow prices must be ≤ 0 (relaxing supply reduces cost)."""
        for src, pi in sens["shadow_supply"].items():
            assert pi <= 0.01, f"Supply shadow price positive for {src}: {pi}"

    def test_shadow_demand_non_negative(self, sens):
        """Demand shadow prices must be ≥ 0 (more demand increases cost)."""
        for wh, pi in sens["shadow_demand"].items():
            assert pi >= -0.01, f"Demand shadow price negative for {wh}: {pi}"

    def test_reduced_costs_non_negative(self, sens):
        """Reduced costs of non-basic routes must be ≥ 0."""
        for route, rc in sens["reduced_costs"].items():
            assert rc >= -0.01, f"Negative reduced cost for {route}: {rc}"


class TestMonteCarlo:
    @pytest.fixture(scope="class")
    def mc(self, normal_season):
        supply, demand, cost = normal_season
        return monte_carlo(supply, demand, cost, n_simulations=100, demand_cv=0.15)

    def test_feasible_count(self, mc):
        assert mc["n_feasible"] > 80, "Too many infeasible MC iterations"

    def test_mean_positive(self, mc):
        assert mc["mean_cost"] > 0

    def test_std_positive(self, mc):
        assert mc["std_cost"] > 0

    def test_percentile_order(self, mc):
        assert mc["p5_cost"] <= mc["mean_cost"] <= mc["p95_cost"]

    def test_route_reliability_range(self, mc):
        for route, rel in mc["route_reliability"].items():
            assert 0 <= rel <= 100, f"Reliability out of range for {route}: {rel}"

    def test_infeasible_plus_feasible_equals_total(self, mc):
        assert mc["n_feasible"] + mc["n_infeasible"] == mc["n_simulations"]

    def test_mean_near_deterministic(self, normal_result, mc):
        """MC mean should be within 30% of the deterministic optimum."""
        det = normal_result["total_cost"]
        assert abs(mc["mean_cost"] - det) / det < 0.30


class TestPareto:
    @pytest.fixture(scope="class")
    def pareto(self, normal_season):
        supply, demand, cost = normal_season
        return multi_objective_pareto(supply, demand, cost, n_points=8)

    def test_points_exist(self, pareto):
        assert len(pareto["pareto"]) >= 2

    def test_all_points_have_keys(self, pareto):
        for p in pareto["pareto"]:
            assert "alpha" in p and "cost" in p and "time" in p

    def test_alpha_range(self, pareto):
        for p in pareto["all_points"]:
            assert 0.0 <= p["alpha"] <= 1.0

    def test_cost_positive(self, pareto):
        for p in pareto["pareto"]:
            assert p["cost"] > 0

    def test_time_positive(self, pareto):
        for p in pareto["pareto"]:
            assert p["time"] > 0

    def test_pareto_non_dominated(self, pareto):
        """No point in the Pareto set should be dominated by another."""
        pts = pareto["pareto"]
        for i, p in enumerate(pts):
            for j, q in enumerate(pts):
                if i != j:
                    assert not (q["cost"] <= p["cost"] and q["time"] <= p["time"]
                                and (q["cost"] < p["cost"] or q["time"] < p["time"])), \
                        f"Point {p} dominated by {q}"
