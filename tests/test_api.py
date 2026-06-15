"""FastAPI endpoint tests via Starlette's TestClient."""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestHealth:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


class TestScenarios:
    def test_list_scenarios(self):
        r = client.get("/scenarios")
        assert r.status_code == 200
        names = [s["name"] for s in r.json()]
        assert "Normal Season" in names
        assert len(names) == 4


class TestSolve:
    def test_solve_normal(self):
        r = client.post("/solve", json={"scenario": "Normal Season"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "Optimal"
        assert body["total_cost"] > 0
        assert body["active_routes"] >= 1
        assert len(body["shipments"]) == body["active_routes"]

    def test_solve_unknown_scenario(self):
        r = client.post("/solve", json={"scenario": "Nonexistent"})
        assert r.status_code == 400

    def test_solve_custom_demand(self):
        r = client.post("/solve", json={
            "scenario": "Normal Season",
            "custom_demand": {
                "Konya": 100, "Kayseri": 100, "Trabzon": 100, "Gaziantep": 100,
                "Antalya": 100, "Samsun": 100, "Eskişehir": 100, "Diyarbakır": 100,
            },
        })
        assert r.status_code == 200
        assert r.json()["status"] == "Optimal"

    def test_fuel_multiplier_validation(self):
        r = client.post("/solve", json={"scenario": "Normal Season", "fuel_multiplier": 99})
        assert r.status_code == 422  # out of [0.5, 3.0]


class TestAnalytics:
    def test_sensitivity(self):
        r = client.post("/sensitivity", json={"scenario": "Normal Season"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "Optimal"
        assert body["base_cost"] > 0
        assert len(body["shadow_supply"]) == 5
        assert len(body["shadow_demand"]) == 8

    def test_monte_carlo(self):
        r = client.post("/monte-carlo", json={
            "scenario": "Normal Season", "n_simulations": 20, "demand_cv": 0.1,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["n_simulations"] == 20
        assert body["n_feasible"] + body["n_infeasible"] == 20
        assert body["mean_cost"] >= 0

    def test_pareto(self):
        r = client.post("/pareto", json={"scenario": "Normal Season", "n_points": 5})
        assert r.status_code == 200
        body = r.json()
        assert len(body["all_points"]) >= 1
        assert len(body["pareto"]) >= 1
        for p in body["pareto"]:
            assert {"alpha", "cost", "time"} <= set(p.keys())
