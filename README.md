# 🚛 Turkey Logistics Decision-Support System

A **portfolio-quality transportation optimisation tool** for a Turkish logistics network, built with Python, PuLP, and Streamlit.

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

Simulates cost distribution under demand uncertainty (truncated normal, CV = 0.15, N = 300 iterations). Shows mean, 5th/95th percentile, and per-route reliability.

---

## 🎯 Multi-Objective Pareto Frontier

![Pareto](fig_pareto.png)

Weighted-sum scalarisation sweeps α ∈ [0, 1] between cost minimisation and travel-time minimisation, tracing the Pareto-optimal frontier.

---

## 🏗️ System Architecture

![Architecture](fig_architecture.png)

---

## 🎯 What it does

Finds the **minimum-cost shipment plan** from 5 production centres to 8 warehouses across Turkey using Linear Programming (Simplex method), then visualises the results interactively.

## 🗺️ Network

| Production Centres | Warehouses |
|---|---|
| İstanbul, Ankara, İzmir, Bursa, Adana | Konya, Kayseri, Trabzon, Gaziantep, Antalya, Samsun, Eskişehir, Diyarbakır |

**Total supply:** 2,650 units · **Base demand:** 1,410 units · **Slack:** 1,240 units

## 🧮 Mathematical Model

$$\min Z = \sum_{i \in I} \sum_{j \in J} c_{ij} x_{ij}$$

Subject to:
- $\sum_{j} x_{ij} \leq s_i \quad \forall i$ — supply constraints (capacity cannot be exceeded)
- $\sum_{i} x_{ij} \geq d_j \quad \forall j$ — demand constraints (all demand must be met)
- $x_{ij} \geq 0 \quad \forall i, j$ — non-negativity

**Model size:** 40 decision variables · 13 constraints

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

## 🚀 Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🐳 Run with Docker

```bash
docker build -t turkey-logistics .
docker run -p 8501:8501 turkey-logistics
```

## 📦 Tech Stack

| Layer | Tools |
|---|---|
| Optimisation | PuLP 2.8 · CBC Simplex Solver |
| Web App | Streamlit |
| Maps | Folium + AntPath + streamlit-folium |
| Charts | Plotly (Sankey · Heatmap · Bar · Scatter) |
| Analytics | NumPy · SciPy (Monte Carlo, Pareto) |
| PDF Export | fpdf2 |
| Road Distances | OSRM API (with fallback) |
| Containerisation | Docker |

## 📁 Project Structure

```
turkey_logistics/
├── app.py               # Streamlit dashboard (8 tabs)
├── model.py             # PuLP LP formulation & solver
├── data.py              # Network data, scenarios, OSRM client
├── analytics.py         # Sensitivity, Monte Carlo, Pareto
├── visualization.py     # Folium maps + Plotly charts
├── report.py            # PDF report generator (fpdf2)
├── report_ieee.tex      # IEEE-format LaTeX paper
├── report_ieee.pdf      # Compiled paper
├── Dockerfile
└── requirements.txt
```

---

*Transportation Problem · Linear Programming · Decision-Support System · Python*
