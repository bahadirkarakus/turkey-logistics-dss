"""Tab: Cost analysis — breakdown, heatmap, full unit-cost table."""

import pandas as pd
import streamlit as st

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
