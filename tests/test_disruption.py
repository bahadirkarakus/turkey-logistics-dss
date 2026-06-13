import pytest
from disruption import simulate_disruption
from data import SOURCES, WAREHOUSES, get_scenario_data


@pytest.fixture(scope="module")
def base_data():
    return get_scenario_data("Normal Season")


class TestNoDisruption:
    def test_zero_cost_delta(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c)
        assert r["cost_delta"] == pytest.approx(0.0, abs=0.01)

    def test_no_lost_routes(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c)
        assert r["lost_routes"] == []
        assert r["new_routes"] == []

    def test_all_routes_unchanged(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c)
        assert len(r["unchanged_routes"]) == len(r["base"]["shipments"])


class TestDisabledSource:
    def test_disabled_supply_is_zero(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, disabled_sources=["Bursa"])
        assert r["disrupted_supply"]["Bursa"] == 0

    def test_non_disabled_supply_unchanged(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, disabled_sources=["Bursa"])
        for src in SOURCES:
            if src != "Bursa":
                assert r["disrupted_supply"][src] == s[src]

    def test_lost_routes_only_from_disabled(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, disabled_sources=["İstanbul"])
        for src, wh in r["lost_routes"]:
            assert src == "İstanbul"

    def test_cost_does_not_decrease(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, disabled_sources=["Adana"])
        if r["disrupted"]["status"] == "Optimal":
            assert r["cost_delta"] >= -0.01  # allow tiny float tolerance

    @pytest.mark.parametrize("src", list(SOURCES.keys()))
    def test_disable_each_source(self, src, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, disabled_sources=[src])
        # Either infeasible or cost delta >= 0
        dis_ok = r["disrupted"]["status"] == "Optimal"
        if dis_ok:
            assert r["cost_delta"] >= -0.01
        assert r["disrupted_supply"][src] == 0


class TestPartialCapacity:
    def test_partial_supply_correct(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, capacity_fractions={"İzmir": 0.5})
        assert r["disrupted_supply"]["İzmir"] == round(s["İzmir"] * 0.5)

    def test_other_sources_unchanged_in_partial(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, capacity_fractions={"İzmir": 0.5})
        for src in SOURCES:
            if src != "İzmir":
                assert r["disrupted_supply"][src] == s[src]

    def test_cost_delta_pct_returned(self, base_data):
        s, d, c = base_data
        r = simulate_disruption(s, d, c, capacity_fractions={"Ankara": 0.7})
        if r["disrupted"]["status"] == "Optimal":
            assert r["cost_delta_pct"] is not None
