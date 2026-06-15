import pytest

from data import WAREHOUSES
from pmedian import ALL_LOCATIONS, haversine, solve_pmedian


class TestHaversine:
    def test_same_point_is_zero(self):
        assert haversine(39.0, 35.0, 39.0, 35.0) == pytest.approx(0.0, abs=0.01)

    def test_known_distance_istanbul_ankara(self):
        # straight-line ~350 km
        d = haversine(41.0082, 28.9784, 39.9334, 32.8597)
        assert 340 < d < 380

    def test_symmetric(self):
        d1 = haversine(40.0, 29.0, 38.0, 35.0)
        d2 = haversine(38.0, 35.0, 40.0, 29.0)
        assert d1 == pytest.approx(d2, rel=1e-6)


class TestAllLocations:
    def test_count(self):
        assert len(ALL_LOCATIONS) == 13  # 5 sources + 8 warehouses

    def test_has_lat_lon(self):
        for info in ALL_LOCATIONS.values():
            assert "lat" in info and "lon" in info


class TestSolvePMedian:
    @pytest.mark.parametrize("p", [1, 2, 3, 4, 5])
    def test_optimal_status(self, p):
        r = solve_pmedian(p=p)
        assert r["status"] == "Optimal"

    @pytest.mark.parametrize("p", [1, 2, 3])
    def test_selected_count(self, p):
        r = solve_pmedian(p=p)
        assert len(r["selected"]) == p

    def test_all_demand_nodes_assigned(self):
        r = solve_pmedian(p=3)
        for w in WAREHOUSES:
            assert w in r["assignment"]

    def test_assigned_to_open_facility(self):
        r = solve_pmedian(p=3)
        for fac in r["assignment"].values():
            assert fac in r["selected"]

    def test_total_weighted_dist_positive(self):
        r = solve_pmedian(p=3)
        assert r["total_weighted_dist"] > 0

    def test_more_facilities_lowers_distance(self):
        r2 = solve_pmedian(p=2)["total_weighted_dist"]
        r5 = solve_pmedian(p=5)["total_weighted_dist"]
        assert r5 <= r2

    def test_p_equals_demand_nodes_assigns_each_to_itself(self):
        demand = {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES}
        r = solve_pmedian(p=len(demand), demand=demand,
                          candidates=list(demand.keys()))
        assert r["status"] == "Optimal"
        for node, fac in r["assignment"].items():
            assert node == fac

    def test_dist_matrix_populated(self):
        r = solve_pmedian(p=2)
        for w in WAREHOUSES:
            assert w in r["dist_matrix"]
            assert len(r["dist_matrix"][w]) == 13
