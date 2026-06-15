"""Tests for the central solver factory."""

import pulp

from solver import get_solver


class TestSolver:
    def test_default_returns_solver(self):
        s = get_solver()
        assert isinstance(s, pulp.LpSolver)

    def test_cbc_explicit(self):
        s = get_solver("cbc")
        assert isinstance(s, pulp.PULP_CBC_CMD)

    def test_unknown_falls_back_to_cbc(self):
        s = get_solver("does-not-exist")
        assert isinstance(s, pulp.PULP_CBC_CMD)

    def test_solver_actually_solves(self):
        prob = pulp.LpProblem("t", pulp.LpMinimize)
        x = pulp.LpVariable("x", lowBound=0)
        prob += x
        prob += x >= 3
        prob.solve(get_solver())
        assert pulp.LpStatus[prob.status] == "Optimal"
        assert abs((x.varValue or 0) - 3) < 1e-6
