"""
Demand forecasting — Holt double-exponential smoothing.
Generates synthetic quarterly demand history and forecasts next n periods.
"""
from __future__ import annotations

import numpy as np

from data import WAREHOUSES


def generate_historical(n_periods: int = 8, seed: int = 42) -> dict[str, list[int]]:
    """Synthetic quarterly demand with trend + seasonality + noise."""
    rng      = np.random.default_rng(seed)
    seasonal = np.tile([1.00, 1.10, 1.20, 0.90], (n_periods // 4) + 1)[:n_periods]
    trend    = np.linspace(0.93, 1.07, n_periods)
    history: dict[str, list[int]] = {}
    for w, info in WAREHOUSES.items():
        noise      = rng.normal(1.0, 0.055, n_periods)
        raw        = info["demand"] * seasonal * trend * noise
        history[w] = np.round(raw).astype(int).tolist()
    return history


def _holt(
    series: list[float],
    alpha: float,
    beta:  float,
) -> tuple[list[float], list[float]]:
    """Holt's double exponential smoothing → (levels, trends)."""
    L = [float(series[0])]
    T = [float(series[1] - series[0]) if len(series) > 1 else 0.0]
    for x in series[1:]:
        L_new = alpha * x + (1 - alpha) * (L[-1] + T[-1])
        T_new = beta  * (L_new - L[-1]) + (1 - beta) * T[-1]
        L.append(L_new)
        T.append(T_new)
    return L, T


def forecast_demand(
    n_forecast: int   = 4,
    alpha:      float = 0.40,
    beta:       float = 0.15,
    seed:       int   = 42,
) -> dict[str, dict]:
    """
    Returns per-warehouse:
    {
        "history":  [int × 8],     # synthetic historical quarters
        "smoothed": [float × 8],   # Holt fitted levels (in-sample)
        "forecast": [int × n_forecast],
    }
    """
    history = generate_historical(seed=seed)
    out: dict[str, dict] = {}
    for w, hist in history.items():
        L, T = _holt(hist, alpha=alpha, beta=beta)
        fcst = [max(0, round(L[-1] + h * T[-1])) for h in range(1, n_forecast + 1)]
        out[w] = {
            "history":  hist,
            "smoothed": [round(v, 1) for v in L],
            "forecast": fcst,
        }
    return out
