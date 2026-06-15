"""Page header + KPI cards."""

import streamlit as st

from data import SOURCES, WAREHOUSES


def render_header_kpis() -> None:
    st.markdown("# 🚛 Turkey Logistics Decision-Support System")
    st.markdown(
        "Find the **minimum-cost** shipment plan from production centres to warehouses "
        "· Scenario analysis · Map visualisation"
    )
    st.divider()

    res         = st.session_state.result
    co2_matrix  = st.session_state.co2_matrix

    total_supply      = sum(SOURCES[s]["capacity"] for s in SOURCES)
    total_demand_base = sum(WAREHOUSES[w]["demand"] for w in WAREHOUSES)

    cost_val = f"₺{res['total_cost']:,.0f}" if res else "—"
    cost_sub = "Optimal ✓" if res else "Not solved yet"
    if res:
        total_co2 = sum(co2_matrix[s][w] * v for (s, w), v in res["shipments"].items())
        co2_val, co2_sub = f"{total_co2:,.0f} kg", f"{total_co2 / 1000:.2f} t CO₂"
    else:
        co2_val, co2_sub = "—", "not solved yet"
    scen_label = st.session_state.scenario_run or "—"
    routes_n   = len(res["shipments"]) if res else "—"
    dem_used   = (sum(st.session_state.demand_used.values())
                  if st.session_state.demand_used else total_demand_base)

    st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Minimum Cost</div>
    <div class="kpi-value">{cost_val}</div>
    <div class="kpi-sub">{cost_sub}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total CO₂</div>
    <div class="kpi-value" style="font-size:1.15rem">{co2_val}</div>
    <div class="kpi-sub">{co2_sub}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Active Scenario</div>
    <div class="kpi-value" style="font-size:1.05rem">{scen_label}</div>
    <div class="kpi-sub">&nbsp;</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Active Routes</div>
    <div class="kpi-value">{routes_n}</div>
    <div class="kpi-sub">of 40 possible</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Supply</div>
    <div class="kpi-value">{total_supply:,}</div>
    <div class="kpi-sub">units capacity</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Demand</div>
    <div class="kpi-value">{dem_used:,}</div>
    <div class="kpi-sub">units</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("")
