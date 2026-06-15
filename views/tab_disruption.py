"""Tab: Supply disruption simulation."""

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from data import SCENARIOS, SOURCES, WAREHOUSES, get_scenario_data
from disruption import simulate_disruption


def render() -> None:
    st.markdown(
        "Simulate a supply disruption — disable or reduce source capacity "
        "and see how the optimizer re-routes and how much cost increases."
    )

    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.markdown('<div class="section-header">Disruption Settings</div>',
                    unsafe_allow_html=True)

        dis_scenario = st.selectbox("Base Scenario", list(SCENARIOS.keys()),
                                    key="dis_scen")
        st.markdown("**Disable Sources (capacity → 0)**")
        disabled_srcs = []
        for src in SOURCES:
            if st.checkbox(src, value=False, key=f"dis_{src}"):
                disabled_srcs.append(src)

        st.markdown("**Partial Capacity Cuts**")
        cap_fracs: dict[str, float] = {}
        for src in SOURCES:
            if src not in disabled_srcs:
                frac = st.slider(f"{src} capacity %", 10, 100, 100, 10,
                                 key=f"frac_{src}") / 100
                if frac < 1.0:
                    cap_fracs[src] = frac

        dis_btn = st.button("⚠️ Simulate Disruption", type="primary",
                            use_container_width=True, key="dis_btn")

    if dis_btn:
        d_supply, d_demand, d_cost = get_scenario_data(dis_scenario)
        with st.spinner("Solving base + disrupted LP..."):
            dis_result = simulate_disruption(
                d_supply, d_demand, d_cost,
                disabled_sources=disabled_srcs,
                capacity_fractions=cap_fracs,
            )
        st.session_state["dis_result"] = dis_result
        st.session_state["dis_supply"] = d_supply
        st.session_state["dis_demand"] = d_demand

    dr = st.session_state.get("dis_result")
    if not dr:
        st.info("Configure disruption settings and press **Simulate Disruption**.")
        return

    with col_d2:
        base_ok = dr["base"]["status"] == "Optimal"
        dis_ok  = dr["disrupted"]["status"] == "Optimal"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Base Cost", f"₺{dr['base']['total_cost']:,.0f}" if base_ok else "—")
        if dis_ok:
            m2.metric("Disrupted Cost", f"₺{dr['disrupted']['total_cost']:,.0f}",
                      delta=f"₺{dr['cost_delta']:+,.0f}" if dr['cost_delta'] else None,
                      delta_color="inverse")
            m3.metric("Cost Impact",
                      f"{dr['cost_delta_pct']:+.1f}%" if dr['cost_delta_pct'] else "—")
        else:
            m2.metric("Disrupted Cost", "INFEASIBLE")
            m3.metric("Cost Impact", "Cannot serve demand")
        m4.metric("Lost Routes", len(dr["lost_routes"]))

    st.divider()

    if not dis_ok:
        st.error(
            "Disruption makes the problem **infeasible** — "
            "remaining supply cannot cover all warehouse demand. "
            "Try enabling more sources or reducing partial capacity cuts."
        )
        return

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.markdown('<div class="section-header">Lost Routes (red)</div>',
                    unsafe_allow_html=True)
        if dr["lost_routes"]:
            ldf = pd.DataFrame([
                {"Source": s, "Warehouse": w,
                 "Base units": int(dr["base"]["shipments"].get((s, w), 0))}
                for (s, w) in sorted(dr["lost_routes"])
            ])
            st.dataframe(ldf, hide_index=True, use_container_width=True)
        else:
            st.success("No routes lost.")

    with col_r2:
        st.markdown('<div class="section-header">New Routes (green)</div>',
                    unsafe_allow_html=True)
        if dr["new_routes"]:
            ndf = pd.DataFrame([
                {"Source": s, "Warehouse": w,
                 "New units": int(dr["disrupted"]["shipments"].get((s, w), 0))}
                for (s, w) in sorted(dr["new_routes"])
            ])
            st.dataframe(ndf, hide_index=True, use_container_width=True)
        else:
            st.info("No new routes introduced.")

    st.divider()
    fig_dis = go.Figure()
    fig_dis.add_trace(go.Bar(
        name="Base", x=["Total Cost"], y=[dr["base"]["total_cost"]],
        marker_color="#3498DB",
        text=[f"₺{dr['base']['total_cost']:,.0f}"], textposition="outside",
    ))
    fig_dis.add_trace(go.Bar(
        name="Disrupted", x=["Total Cost"], y=[dr["disrupted"]["total_cost"]],
        marker_color="#E74C3C",
        text=[f"₺{dr['disrupted']['total_cost']:,.0f}"], textposition="outside",
    ))
    fig_dis.update_layout(
        title="Base vs Disrupted Total Cost",
        barmode="group",
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font_color="white", height=300,
        yaxis=dict(title="Cost (TL)", gridcolor="#333"),
    )
    st.plotly_chart(fig_dis, use_container_width=True)

    st.markdown('<div class="section-header">Network Map</div>',
                unsafe_allow_html=True)
    st.caption("🔵 Unchanged routes · 🔴 Lost routes · 🟢 New routes")

    dmap = folium.Map(location=[39.0, 35.0], zoom_start=6, tiles="CartoDB dark_matter")

    for src, info in SOURCES.items():
        is_disabled = src in disabled_srcs
        cap_frac    = cap_fracs.get(src, 1.0)
        color = "#888888" if is_disabled else ("#F39C12" if cap_frac < 1.0 else "#E74C3C")
        label = f"{src} ({'DISABLED' if is_disabled else f'{int(cap_frac * 100)}%'})"
        folium.CircleMarker(
            [info["lat"], info["lon"]], radius=10,
            color=color, fill=True, fill_opacity=0.9,
            popup=label, tooltip=label,
        ).add_to(dmap)

    for wh, info in WAREHOUSES.items():
        folium.CircleMarker(
            [info["lat"], info["lon"]], radius=7,
            color="#2ECC71", fill=True, fill_opacity=0.8,
            tooltip=wh,
        ).add_to(dmap)

    for (s, w) in dr["unchanged_routes"]:
        folium.PolyLine(
            [[SOURCES[s]["lat"], SOURCES[s]["lon"]],
             [WAREHOUSES[w]["lat"], WAREHOUSES[w]["lon"]]],
            color="#3498DB", weight=2, opacity=0.6,
            tooltip=f"{s}→{w} (unchanged)",
        ).add_to(dmap)

    for (s, w) in dr["lost_routes"]:
        folium.PolyLine(
            [[SOURCES[s]["lat"], SOURCES[s]["lon"]],
             [WAREHOUSES[w]["lat"], WAREHOUSES[w]["lon"]]],
            color="#E74C3C", weight=3, opacity=0.9, dash_array="8 4",
            tooltip=f"{s}→{w} (LOST)",
        ).add_to(dmap)

    for (s, w) in dr["new_routes"]:
        folium.PolyLine(
            [[SOURCES[s]["lat"], SOURCES[s]["lon"]],
             [WAREHOUSES[w]["lat"], WAREHOUSES[w]["lon"]]],
            color="#2ECC71", weight=3, opacity=0.9,
            tooltip=f"{s}→{w} (NEW)",
        ).add_to(dmap)

    st_folium(dmap, width="100%", height=450)
