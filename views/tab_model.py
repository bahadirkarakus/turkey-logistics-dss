"""Tab: Mathematical model formulation + supply/demand summary."""

import pandas as pd
import streamlit as st

from data import SOURCES, WAREHOUSES
from model import formulation_text


def render() -> None:
    res = st.session_state.result

    sup_disp = st.session_state.supply_used or {s: SOURCES[s]["capacity"] for s in SOURCES}
    dem_disp = st.session_state.demand_used or {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES}

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown(formulation_text(sup_disp, dem_disp))

    with col_r:
        st.markdown('<div class="section-header">Arz & Demand</div>', unsafe_allow_html=True)

        df_sup = pd.DataFrame([
            {"Production Centre": s, "Capacity (units)": v}
            for s, v in sup_disp.items()
        ])
        df_sup.loc[len(df_sup)] = ["**TOTAL**", sum(sup_disp.values())]
        st.dataframe(df_sup, hide_index=True, use_container_width=True)

        st.markdown("")
        df_dem = pd.DataFrame([
            {"Warehouse": w, "Demand (units)": v}
            for w, v in dem_disp.items()
        ])
        df_dem.loc[len(df_dem)] = ["**TOTAL**", sum(dem_disp.values())]
        st.dataframe(df_dem, hide_index=True, use_container_width=True)

    if res and res["status"] == "Optimal":
        st.divider()
        st.markdown('<div class="section-header">Solution Summary</div>',
                    unsafe_allow_html=True)
        slack_df = pd.DataFrame([
            {"Source": s, "Slack Capacity": int(v)}
            for s, v in res["slack"].items()
        ])
        st.dataframe(slack_df, hide_index=True, use_container_width=True)
