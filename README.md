# 🚛 Turkey Logistics Decision-Support System

A **portfolio-quality transportation optimization tool** for a Turkish logistics network, built with Python, PuLP, and Streamlit.

🔗 **Live demo:** [turkey-logistics-dss-33hou3yq4gqkhaiejjrglh.streamlit.app](https://turkey-logistics-dss-33hou3yq4gqkhaiejjrglh.streamlit.app)

---

## Dashboard

![Interface](fig_interface.png)

---

## 🗺️ Interactive Route Map

![Map](fig_map.png)

Animated routes on a Turkey map — line thickness proportional to shipment volume. Red = production centres, green = warehouses.

---

## 📦 Material Flow — Sankey Diagram

![Sankey](fig_sankey.png)

---

## 💰 Cost Breakdown & Heatmap

![Cost](fig_cost.png)

---

## 📊 Scenario Comparison

![Scenario](fig_scenario.png)

Four built-in scenarios: **Normal Season · Summer Season · Fuel Increase (+20%) · Winter Season**. Save any solved scenario and compare side-by-side.

---

## 🔍 Sensitivity Analysis

![Sensitivity](fig_sensitivity.png)

Shadow prices (dual variables) show which supply/demand constraints are most valuable to relax. Reduced costs reveal how close inactive routes are to entering the optimal solution.

---

## 🎲 Monte Carlo Simulation

![Monte Carlo](fig_montecarlo.png)

Simulates cost distribution under demand uncertainty (truncated normal, CV = 0.15, N = 300 iterations). Shows mean, 5th/95th percentile, and per-route reliability heatmap.

---

## 🎯 Multi-Objective Pareto Frontier

![Pareto](fig_pareto.png)

Weighted-sum scalarisation sweeps α ∈ [0, 1] between cost minimisation and travel-time minimisation, tracing the Pareto-optimal frontier.

---

## 📅 Multi-Period Planning (4-Quarter LP)

![Multi-Period](fig_multiperiod.png)

4-quarter transportation LP with inventory carryover. Annual capacity split evenly per quarter; seasonal demand multipliers shift load between periods. Stacked bar chart shows transport vs. holding cost per quarter.

---

## 📈 Demand Forecasting

![Forecast](fig_forecast.png)

Holt double-exponential smoothing on 8 quarters of synthetic historical data. Forecasts next 4 quarters per warehouse with configurable α/β. Forecast output can feed directly into the multi-period LP.

---

## ⚠️ Disruption Simulation

![Disruption](fig_disruption.png)

Disable or partially reduce source capacity to model supply chain disruptions. Compares base vs. disrupted optimal plans — shows cost delta, lost/new routes, and a colour-coded map (blue = unchanged, red = lost, green = new).

---

## 📍 Facility Location (P-Median)

![Location](fig_location.png)

P-Median binary MIP: finds which *p* of 13 candidate cities (5 sources + 8 warehouses) to open as distribution hubs to minimise total demand-weighted distance. Includes an elbow curve to guide the choice of p.

---

## 🏗️ System Architecture

![Architecture](fig_architecture.png)

---

## 🎯 What it does

Finds the **minimum-cost shipment plan** from 5 production centres to 8 warehouses across Turkey using Linear Programming (Simplex method), then layers eight analytical modules on top.

## 🗺️ Network

| Production Centres | Warehouses |
|---|---|
| İstanbul, Ankara, İzmir, Bursa, Adana | Konya, Kayseri, Trabzon, Gaziantep, Antalya, Samsun, Eskişehir, Diyarbakır |

**Total supply:** 2,650 units · **Base demand:** 1,610 units · **Slack:** 1,040 units

## 🧮 Mathematical Model

$$\min Z = \sum_{i \in I} \sum_{j \in J} c_{ij} x_{ij}$$

Subject to:
- $\sum_{j} x_{ij} \leq s_i \quad \forall i$ — supply capacity
- $\sum_{i} x_{ij} \geq d_j \quad \forall j$ — demand fulfilment
- $\sum_{ij} e_{ij} x_{ij} \leq B$ — optional CO₂ emission cap
- $x_{ij} \geq 0 \quad \forall i, j$

**Model size:** 40 decision variables · 13 constraints (+ optional CO₂ constraint)

## 💰 Cost Estimation

$$c_{ij} = \frac{d_{ij} \cdot \frac{L}{100} \cdot p_f \;+\; \frac{d_{ij}}{v} \cdot w \;+\; \tau_{ij} \;+\; f}{q}$$

| Parameter | Value |
|---|---|
| Fuel consumption | 30 L / 100 km |
| Diesel price $p_f$ | 40 TL/L (live input) |
| Driver wage $w$ | 150 TL/h |
| Avg speed $v$ | 80 km/h |
| HGS/OGS tolls $\tau_{ij}$ | Route-specific |
| Load/unload fee $f$ | 200 TL |
| Truck capacity $q$ | 25 units |
| CO₂ factor | 2.68 kg/L (IPCC) |

## 🚀 Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🐳 Run with Docker Compose (API + Streamlit)

```bash
docker compose up
# Streamlit → http://localhost:8501
# FastAPI    → http://localhost:8000/docs
```

## 🧪 Tests

```bash
python -m pytest tests/ -v   # 124 tests
```

## 📦 Tech Stack

| Layer | Tools |
|---|---|
| Optimization | PuLP 2.8 · CBC Simplex · Binary MIP (p-median) |
| Forecasting | Holt double-exponential smoothing (NumPy) |
| Web App | Streamlit (11-tab dashboard) |
| REST API | FastAPI + Pydantic + Uvicorn |
| Maps | Folium + streamlit-folium |
| Charts | Plotly (Sankey · Heatmap · Bar · Scatter) |
| Analytics | NumPy · SciPy |
| Export | fpdf2 (PDF) · openpyxl (Excel) |
| Road Distances | OSRM API (with fallback) |
| CI/CD | GitHub Actions · Streamlit Community Cloud |
| Containerisation | Docker Compose |

## 📁 Project Structure

```
turkey_logistics/
├── app.py               # Streamlit dashboard (11 tabs)
├── model.py             # PuLP LP solver (+ CO₂ budget constraint)
├── data.py              # Network data, scenarios, OSRM client
├── analytics.py         # Sensitivity, Monte Carlo, Pareto
├── visualization.py     # Folium maps + Plotly charts
├── multiperiod.py       # 4-quarter LP with inventory
├── forecasting.py       # Holt exponential smoothing
├── disruption.py        # Supply disruption simulation
├── pmedian.py           # P-Median facility location MIP
├── excel_export.py      # Excel report generator
├── report.py            # PDF report generator
├── report_ieee.tex      # IEEE-format LaTeX paper
├── api/                 # FastAPI backend
│   ├── main.py
│   ├── schemas.py
│   └── routes/
├── tests/               # pytest suite (124 tests)
├── docker-compose.yml
└── requirements.txt
```

---

*Transportation Problem · Linear Programming · P-Median · Holt Forecasting · Disruption Simulation · Python · Streamlit*
