"""Tab: Cost analysis — breakdown, heatmap, unit-cost table, fuel-price sweep."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import fuel_price_sweep
from data import SOURCES, WAREHOUSES
from visualization import build_cost_breakdown, build_cost_heatmap


def render() -> None:
    res = st.session_state.result
    if not (res and res["status"] == "Optimal"):
        st.info("Run optimization first.")
        return

    cost  = st.session_state.cost_used
    ships = res["shipments"]

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(build_cost_breakdown(ships, cost), use_container_width=True)
    with col2:
        st.plotly_chart(build_cost_heatmap(cost), use_container_width=True)

    st.divider()
    st.markdown('<div class="section-header">All Routes — Unit Cost Table (TL/unit)</div>',
                unsafe_allow_html=True)
    whs = list(WAREHOUSES.keys())
    df_cost = pd.DataFrame(
        {src: {wh: f"₺{cost[src][wh]:,.0f}" for wh in whs} for src in SOURCES}
    ).T
    st.dataframe(df_cost, use_container_width=True)

    _render_fuel_sweep()


def _render_fuel_sweep() -> None:
    """Diesel-price sensitivity: how total cost responds to the fuel price."""
    st.divider()
    st.markdown('<div class="section-header">Fuel Price Sensitivity</div>',
                unsafe_allow_html=True)
    st.caption("Re-solves the LP across a range of diesel prices and traces the "
               "minimum total cost. Elasticity = % cost change per % price change.")

    scenario = st.session_state.scenario_run or "Normal Season"
    with st.spinner("Sweeping fuel price..."):
        sweep = fuel_price_sweep(scenario, n_points=12)

    if not sweep["points"]:
        st.info("No feasible solution across the swept price range.")
        return

    prices = [p["fuel_price"] for p in sweep["points"]]
    costs  = [p["total_cost"] for p in sweep["points"]]

    fig = go.Figure(go.Scatter(
        x=prices, y=costs, mode="lines+markers",
        line=dict(color="#F39C12", width=2),
        marker=dict(size=7),
        hovertemplate="₺%{x:.1f}/L → ₺%{y:,.0f}<extra></extra>",
    ))
    fig.add_vline(x=sweep["base_price"], line_color="#3498DB", line_dash="dash",
                  annotation_text="current")
    fig.update_layout(
        title=f"Total Cost vs Diesel Price — {scenario}",
        xaxis_title="Diesel price (TL/L)", yaxis_title="Total Cost (TL)",
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="white",
        height=340, xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
    )
    st.plotly_chart(fig, use_container_width=True)

    if sweep["elasticity"] is not None:
        st.metric("Cost elasticity w.r.t. fuel price", f"{sweep['elasticity']:.2f}",
                  help="A value of 0.6 means a 10% rise in diesel price raises "
                       "total cost by ~6%.")
