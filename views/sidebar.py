"""Sidebar controls — returns a SidebarConfig consumed by app.py."""

from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st

from data import SCENARIOS, SOURCES, WAREHOUSES, fetch_real_distances
from report import generate_pdf


@dataclass
class SidebarConfig:
    scenario: str
    live_fuel_price: float
    custom_fuel: float
    custom_supply: dict = field(default_factory=dict)
    custom_demand: dict = field(default_factory=dict)
    co2_budget_on: bool = False
    co2_budget_val: float | None = None
    use_custom: bool = False
    run_btn: bool = False
    save_btn: bool = False
    compare_btn: bool = False


def render_sidebar() -> SidebarConfig:
    with st.sidebar:
        st.markdown("## 🇹🇷 🚛 Turkey Logistics DSS")
        st.caption("Transportation Problem Optimization Tool")
        st.divider()

        # Scenario picker
        scenario = st.selectbox(
            "Scenario",
            list(SCENARIOS.keys()),
            help="Select the scenario to run.",
        )
        st.caption(f"*{SCENARIOS[scenario]['description']}*")
        st.divider()

        # Live fuel price
        st.markdown("**⛽ Current Diesel Price (TL/L)**")
        live_fuel_price = st.number_input(
            "Diesel price", min_value=10.0, max_value=200.0,
            value=40.0, step=0.5,
            help="Enter current price. Cost matrix updates automatically.",
        )

        # OSRM real distances
        if st.button("🗺️ Fetch Real Road Distances (OSRM)", use_container_width=True):
            with st.spinner("Querying OSRM API..."):
                real_dist, real_dur = fetch_real_distances(timeout=6)
                st.session_state.real_distances = real_dist
                st.session_state.real_durations = real_dur
            st.sidebar.success("Real distances loaded ✓")

        st.divider()

        # Custom parameter overrides
        custom_supply: dict = {}
        custom_demand: dict = {}
        with st.expander("⚙️ Customise Parameters", expanded=False):
            st.markdown("**Fuel Multiplier**")
            custom_fuel = st.slider(
                "Fuel cost multiplier", 0.80, 2.00, 1.00, 0.05,
                help="1.20 = fuel price up 20%",
            )

            st.markdown("**Supply Capacities**")
            for src, info in SOURCES.items():
                custom_supply[src] = st.number_input(
                    src, min_value=0, max_value=2000,
                    value=info["capacity"], step=50, key=f"sup_{src}",
                )

            st.markdown("**Demand Values**")
            for wh, info in WAREHOUSES.items():
                custom_demand[wh] = st.number_input(
                    wh, min_value=0, max_value=1000,
                    value=info["demand"], step=10, key=f"dem_{wh}",
                )

            st.markdown("**🌱 CO₂ Emission Cap**")
            co2_budget_on = st.checkbox("Apply CO₂ budget constraint", value=False)
            if co2_budget_on:
                co2_budget_val = st.slider(
                    "Max total CO₂ (kg)", 200, 3000, 800, 50,
                    help="Hard upper limit on total CO₂ from all shipments.",
                )
            else:
                co2_budget_val = None

        use_custom = st.checkbox("Apply custom parameters", value=False)

        st.divider()
        run_btn     = st.button("▶ Run Optimization", type="primary", use_container_width=True)
        save_btn    = st.button("💾 Save Result", use_container_width=True)
        compare_btn = st.button("📊 Compare Saved", use_container_width=True)

        # Saved scenarios list
        if st.session_state.get("saved_scenarios"):
            st.divider()
            st.markdown("**💾 Saved**")
            for sname, sdata in st.session_state.saved_scenarios.items():
                col_a, col_b = st.columns([3, 1])
                col_a.caption(f"✓ {sname}")
                col_b.caption(f"₺{sdata['total_cost']:,.0f}")
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.saved_scenarios = {}
                st.session_state.all_results = {}

        st.divider()
        st.caption("Solver: Simplex LP (PuLP / CBC)")

        _render_pdf_button()

    return SidebarConfig(
        scenario=scenario,
        live_fuel_price=live_fuel_price,
        custom_fuel=custom_fuel,
        custom_supply=custom_supply,
        custom_demand=custom_demand,
        co2_budget_on=co2_budget_on,
        co2_budget_val=co2_budget_val,
        use_custom=use_custom,
        run_btn=run_btn,
        save_btn=save_btn,
        compare_btn=compare_btn,
    )


def _render_pdf_button() -> None:
    """PDF export — only meaningful once an optimal result exists."""
    res = st.session_state.get("result")
    if res and res["status"] == "Optimal":
        st.divider()
        if st.button("📄 Download PDF Report", use_container_width=True):
            pdf_bytes = generate_pdf(
                result=res,
                supply=st.session_state.supply_used,
                demand=st.session_state.demand_used,
                cost=st.session_state.cost_used,
                scenario_name=st.session_state.scenario_run or "—",
                saved_scenarios=st.session_state.saved_scenarios or None,
                mc_result=st.session_state.mc_result,
            )
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"logistics_report_{st.session_state.scenario_run}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
