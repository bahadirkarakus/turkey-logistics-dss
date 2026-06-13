# 🚛 Turkey Logistics Decision-Support System

A **transportation problem optimization tool** for a Turkish logistics network, built with Python, PuLP, and Streamlit.

## 🎯 What it does

Finds the **minimum-cost shipment plan** from 5 production centres to 8 warehouses across Turkey using Linear Programming (Simplex method), then visualizes the results interactively.

## 🗺️ Network

| Production Centres | Warehouses |
|---|---|
| İstanbul, Ankara, İzmir, Bursa, Adana | Konya, Kayseri, Trabzon, Gaziantep, Antalya, Samsun, Eskişehir, Diyarbakır |

**Total supply:** 2,650 units · **Base demand:** 1,610 units

## 📊 Features

- **LP Optimization** via PuLP (CBC Simplex solver) — 15 decision variables, 13 constraints
- **Interactive map** (Folium) — animated routes on Turkey map, thickness = shipment volume
- **Sankey flow diagram** — visual material flow from sources to warehouses
- **4 scenario analysis** — Normal, Summer Season, Fuel Price Increase (+20%), Winter
- **Custom parameter override** — modify supply, demand, fuel price live via sliders
- **Cost breakdown** — per-route cost bar chart + full cost matrix heatmap

## 🚀 Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🧮 Mathematical Model

$$\min Z = \sum_{i \in I} \sum_{j \in J} c_{ij} x_{ij}$$

Subject to:
- $\sum_{j} x_{ij} \leq s_i \quad \forall i$ (supply constraints)
- $\sum_{i} x_{ij} \geq d_j \quad \forall j$ (demand constraints)  
- $x_{ij} \geq 0 \quad \forall i, j$ (non-negativity)

## 💰 Cost Estimation

Route costs computed from real distances (Google Maps) using:

$$c_{ij} = \frac{d_{ij} \times \frac{L}{100} \times p_f + \frac{d_{ij}}{v} \times w + \tau_{ij} + f}{q}$$

Where: fuel consumption 30 L/100km · fuel price 40 TL/L · driver wage 150 TL/h · HGS tolls · load fee 200 TL · truck capacity 25 units

## 📦 Tech Stack

| Layer | Tools |
|---|---|
| Optimization | PuLP 2.8 · CBC Solver |
| Web App | Streamlit |
| Maps | Folium + streamlit-folium |
| Charts | Plotly |
| Data | Pandas |

## 📁 Project Structure

```
turkey_logistics/
├── app.py            # Streamlit dashboard
├── model.py          # PuLP LP model
├── data.py           # Network data & scenarios
├── visualization.py  # Folium maps + Plotly charts
└── requirements.txt
```

---
*IE303 Operations Research I — inspired project · IUS FENS Industrial Engineering*
