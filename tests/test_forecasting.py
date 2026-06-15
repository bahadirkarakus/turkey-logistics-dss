from data import WAREHOUSES
from forecasting import forecast_demand, generate_historical


class TestGenerateHistorical:
    def test_all_warehouses_present(self):
        h = generate_historical()
        assert set(h.keys()) == set(WAREHOUSES.keys())

    def test_length(self):
        assert all(len(v) == 8 for v in generate_historical().values())

    def test_all_positive(self):
        for v in generate_historical().values():
            assert all(x > 0 for x in v)

    def test_custom_n_periods(self):
        h = generate_historical(n_periods=12)
        assert all(len(v) == 12 for v in h.values())

    def test_seed_reproducibility(self):
        assert generate_historical(seed=1) == generate_historical(seed=1)

    def test_different_seeds_differ(self):
        h1 = generate_historical(seed=1)
        h2 = generate_historical(seed=99)
        assert h1 != h2


class TestForecastDemand:
    def test_output_keys(self):
        result = forecast_demand()
        assert set(result.keys()) == set(WAREHOUSES.keys())

    def test_history_length(self):
        for data in forecast_demand().values():
            assert len(data["history"]) == 8

    def test_smoothed_length(self):
        for data in forecast_demand().values():
            assert len(data["smoothed"]) == 8

    def test_forecast_length_default(self):
        for data in forecast_demand(n_forecast=4).values():
            assert len(data["forecast"]) == 4

    def test_forecast_length_custom(self):
        for data in forecast_demand(n_forecast=6).values():
            assert len(data["forecast"]) == 6

    def test_forecast_non_negative(self):
        for data in forecast_demand().values():
            assert all(v >= 0 for v in data["forecast"])

    def test_different_alpha_produces_different_forecast(self):
        w  = list(WAREHOUSES.keys())[0]
        f1 = forecast_demand(alpha=0.1)[w]["forecast"]
        f2 = forecast_demand(alpha=0.9)[w]["forecast"]
        assert f1 != f2

    def test_forecast_values_are_ints(self):
        for data in forecast_demand().values():
            assert all(isinstance(v, int) for v in data["forecast"])
