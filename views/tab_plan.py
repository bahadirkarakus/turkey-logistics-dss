"""Tab: Optimal shipment plan + Sankey + route details + Excel export."""

import pandas as pd
import streamlit as st

from data import SOURCES, WAREHOUSES
from excel_export import generate_excel
from visualization import build_sankey


def render() -> None:
    res        = st.session_state.result
    co2_matrix = st.session_state.co2_matrix

    if not (res and res["status"] == "Optimal"):
        st.info("Select a scenario from the sidebar and press **Run Optimization**.")
        return

    sup   = st.session_state.supply_used
    dem   = st.session_state.demand_used
    cost  = st.session_state.cost_used
    ships = res["shipments"]

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown('<div class="section-header">Optimal Shipment Plan</div>',
                    unsafe_allow_html=True)

        whs = list(WAREHOUSES.keys())
        rows = []
        for src in SOURCES:
            row = {"Source": src}
            row_total = 0
            for wh in whs:
                v = ships.get((src, wh), 0)
                row[wh] = int(v) if v > 0 else "—"
                row_total += v
            row["Total Shipped"] = int(row_total)
            row["Capacity"]    = sup[src]
            row["Slack"]       = int(sup[src] - row_total)
            rows.append(row)

        df_plan = pd.DataFrame(rows).set_index("Source")

        def highlight(val):
            if val == "—" or val == 0:
                return "color: #555"
            return "color: #68d391; font-weight: 600"

        st.dataframe(
            df_plan.style.map(highlight, subset=list(whs)),
            use_container_width=True, height=220,
        )

        # Demand row
        dem_row = {wh: dem[wh] for wh in whs}
        met_row = {wh: int(sum(ships.get((s, wh), 0) for s in SOURCES)) for wh in whs}
        st.markdown("**Demand fulfilment:**")
        df_dem = pd.DataFrame([
            {"": "Demand"} | dem_row,
            {"": "Fulfilled"} | met_row,
        ]).set_index("")
        st.dataframe(df_dem, use_container_width=True, height=100)

    with col_r:
        st.markdown('<div class="section-header">Flow Diagram</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(build_sankey(ships), use_container_width=True)

    st.divider()
    st.markdown('<div class="section-header">Route Details</div>',
                unsafe_allow_html=True)

    detail_rows = []
    for (s, w), units in sorted(ships.items(), key=lambda x: -x[1]):
        unit_c   = cost[s][w]
        total_c  = round(unit_c * units, 0)
        co2_unit = co2_matrix[s][w]
        co2_tot  = round(co2_unit * units, 1)
        detail_rows.append({
            "Source": s, "Warehouse": w,
            "Shipment (units)": int(units),
            "Unit Cost (TL)": f"₺{unit_c:,.2f}",
            "Total Cost (TL)": f"₺{total_c:,.0f}",
            "CO₂/unit (kg)": f"{co2_unit:.3f}",
            "Total CO₂ (kg)": f"{co2_tot:,.1f}",
        })
    st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

    total_co2 = sum(co2_matrix[s][w] * v for (s, w), v in ships.items())
    col_cost, col_co2 = st.columns(2)
    col_cost.success(f"**Minimum Total Cost: ₺{res['total_cost']:,.2f}**")
    col_co2.info(f"**Total CO₂ Emissions: {total_co2:,.1f} kg ({total_co2 / 1000:.2f} t)**")

    # Excel download
    st.divider()
    excel_bytes = generate_excel(
        res, sup, dem, cost, co2_matrix,
        st.session_state.scenario_run,
        saved_scenarios=st.session_state.saved_scenarios or None,
    )
    st.download_button(
        label="📥 Download Excel Report (.xlsx)",
        data=excel_bytes,
        file_name=f"logistics_{st.session_state.scenario_run.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
