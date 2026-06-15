"""Tab: P-Median facility location."""

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from data import WAREHOUSES
from pmedian import ALL_LOCATIONS, solve_pmedian


def render() -> None:
    st.markdown(
        "**P-Median Facility Location** — given 13 candidate cities "
        "(5 sources + 8 warehouses), find which *p* locations minimise total "
        "**demand × distance** (km·units). "
        "Useful for deciding where to open new distribution hubs."
    )

    col_l1, col_l2 = st.columns([1, 3])
    with col_l1:
        p_val   = st.slider("Number of facilities (p)", 1, 8, 3)
        loc_btn = st.button("📍 Find Optimal Locations", type="primary",
                            use_container_width=True, key="loc_btn")

    if loc_btn:
        with st.spinner(f"Solving p={p_val} median MIP..."):
            st.session_state["loc_result"] = solve_pmedian(p=p_val)
        st.session_state["loc_p"] = p_val

    lr = st.session_state.get("loc_result")
    if not lr:
        st.info("Set p and press **Find Optimal Locations**.")
        return
    if lr["status"] != "Optimal":
        st.error(f"Solver status: {lr['status']}")
        return

    p_used = st.session_state.get("loc_p", p_val)

    with col_l2:
        k1, k2 = st.columns(2)
        k1.metric("Selected Facilities", p_used)
        k2.metric("Total Weighted Distance", f"{lr['total_weighted_dist']:,.0f} km·units")

    st.divider()

    col_m, col_t = st.columns([3, 2])
    with col_m:
        st.markdown('<div class="section-header">Optimal Facility Locations</div>',
                    unsafe_allow_html=True)

        loc_map = folium.Map(location=[39.0, 35.0], zoom_start=6,
                             tiles="CartoDB dark_matter")

        palette = ["#F39C12", "#3498DB", "#E74C3C", "#2ECC71",
                   "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"]
        fac_color = {fac: palette[i % len(palette)]
                     for i, fac in enumerate(lr["selected"])}

        for node, fac in lr["assignment"].items():
            n_loc = ALL_LOCATIONS[node]
            f_loc = ALL_LOCATIONS[fac]
            folium.PolyLine(
                [[n_loc["lat"], n_loc["lon"]], [f_loc["lat"], f_loc["lon"]]],
                color=fac_color[fac], weight=2, opacity=0.5,
                tooltip=f"{node} → {fac}",
            ).add_to(loc_map)

        for city, loc in ALL_LOCATIONS.items():
            if city not in lr["selected"]:
                folium.CircleMarker(
                    [loc["lat"], loc["lon"]], radius=5,
                    color="#555", fill=True, fill_opacity=0.5,
                    tooltip=city,
                ).add_to(loc_map)

        for fac in lr["selected"]:
            loc  = ALL_LOCATIONS[fac]
            col  = fac_color[fac]
            served = [n for n, f in lr["assignment"].items() if f == fac]
            pop    = f"<b>{fac}</b><br>Serves: {', '.join(served)}"
            folium.CircleMarker(
                [loc["lat"], loc["lon"]], radius=13,
                color=col, fill=True, fill_opacity=0.95,
                tooltip=fac, popup=pop,
            ).add_to(loc_map)
            folium.map.Marker(
                [loc["lat"], loc["lon"]],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:10px;color:white;'
                         f'font-weight:bold;text-align:center;'
                         f'margin-top:-5px">{fac[:3]}</div>',
                    icon_size=(40, 20), icon_anchor=(20, 10),
                ),
            ).add_to(loc_map)

        for node in lr["assignment"]:
            if node in WAREHOUSES:
                fac  = lr["assignment"][node]
                loc  = ALL_LOCATIONS[node]
                col  = fac_color[fac]
                dist = lr["dist_matrix"][node][fac]
                folium.CircleMarker(
                    [loc["lat"], loc["lon"]], radius=7,
                    color=col, fill=True, fill_opacity=0.8,
                    tooltip=f"{node} → {fac} ({dist:.0f} km)",
                ).add_to(loc_map)

        st_folium(loc_map, width="100%", height=480)

    with col_t:
        st.markdown('<div class="section-header">Assignment Table</div>',
                    unsafe_allow_html=True)
        rows_loc = []
        for node, fac in sorted(lr["assignment"].items()):
            dm = WAREHOUSES.get(node, {}).get("demand", "—")
            d  = lr["dist_matrix"][node][fac]
            rows_loc.append({
                "Demand Node":    node,
                "Assigned Hub":   fac,
                "Distance (km)":  f"{d:.0f}",
                "Demand (units)": dm,
                "Weighted (km·u)": f"{(dm * d if isinstance(dm, int) else 0):,.0f}",
            })
        st.dataframe(pd.DataFrame(rows_loc), hide_index=True, use_container_width=True)

        st.markdown('<div class="section-header">Selected Hubs</div>',
                    unsafe_allow_html=True)
        hub_rows = []
        for fac in lr["selected"]:
            served = [n for n, f in lr["assignment"].items() if f == fac]
            tot_d  = sum(
                WAREHOUSES.get(n, {}).get("demand", 0) * lr["dist_matrix"][n][fac]
                for n in served
            )
            hub_rows.append({
                "Hub":            fac,
                "Serves":         len(served),
                "Total km·units": f"{tot_d:,.0f}",
            })
        st.dataframe(pd.DataFrame(hub_rows), hide_index=True, use_container_width=True)

        # p-curve (solve p=1..8 for context), cached per selected p
        if "loc_curve" not in st.session_state or st.session_state.get("loc_p") != p_used:
            with st.spinner("Computing p-curve..."):
                curve = []
                for pp in range(1, min(8, len(ALL_LOCATIONS)) + 1):
                    rr = solve_pmedian(p=pp)
                    if rr["status"] == "Optimal":
                        curve.append({"p": pp, "wd": rr["total_weighted_dist"]})
            st.session_state["loc_curve"] = curve

        curve = st.session_state.get("loc_curve", [])
        if curve:
            fig_curve = go.Figure(go.Scatter(
                x=[c["p"] for c in curve],
                y=[c["wd"] for c in curve],
                mode="lines+markers",
                marker=dict(
                    size=[14 if c["p"] == p_used else 8 for c in curve],
                    color=["#F39C12" if c["p"] == p_used else "#3498DB" for c in curve],
                ),
                line=dict(color="#3498DB", width=2),
                hovertemplate="p=%{x}<br>%{y:,.0f} km·units<extra></extra>",
            ))
            fig_curve.update_layout(
                title="Weighted Distance vs Number of Facilities",
                xaxis_title="p (facilities)", yaxis_title="km·units",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", height=260,
                xaxis=dict(gridcolor="#333", dtick=1),
                yaxis=dict(gridcolor="#333"),
            )
            st.plotly_chart(fig_curve, use_container_width=True)
