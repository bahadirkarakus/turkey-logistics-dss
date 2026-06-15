"""Tab: Interactive route map."""

import streamlit as st
from streamlit_folium import st_folium

from data import SOURCES, WAREHOUSES
from visualization import build_map


def render() -> None:
    res = st.session_state.result
    if res and res["status"] == "Optimal":
        fmap = build_map(
            res["shipments"],
            st.session_state.supply_used,
            st.session_state.demand_used,
        )
        st_folium(fmap, width="100%", height=540)
        st.caption("🔴 Production centre · 🟢 Warehouse · Line thickness = shipment volume")
    else:
        default_map = build_map(
            {},
            {s: SOURCES[s]["capacity"] for s in SOURCES},
            {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES},
        )
        st_folium(default_map, width="100%", height=540)
        st.info("Run optimization → routes appear on the map.")
