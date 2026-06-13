"""Shared pytest fixtures."""

import pytest
from data import get_scenario_data, compute_co2_matrix
from model import solve


@pytest.fixture(scope="session")
def normal_season():
    supply, demand, cost = get_scenario_data("Normal Season")
    return supply, demand, cost


@pytest.fixture(scope="session")
def normal_result(normal_season):
    supply, demand, cost = normal_season
    return solve(supply, demand, cost)


@pytest.fixture(scope="session")
def co2_matrix():
    return compute_co2_matrix()
