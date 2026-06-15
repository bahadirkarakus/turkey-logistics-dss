"""
Turkey Logistics DSS — Streamlit App (orchestrator)

Transportation problem optimization tool for a Turkish logistics network.
The dashboard is split into one module per tab under ``views/``; this file
wires the sidebar controls to the solver and renders the tabs.
"""

import streamlit as st

from data import SCENARIOS, compute_co2_matrix, compute_cost_matrix, get_scenario_data
from model import solve
from views import (
    header,
    styles,
    tab_cost,
    tab_disruption,
    tab_location,
    tab_map,
    tab_model,
    tab_montecarlo,
    tab_multiperiod,
    tab_pareto,
    tab_plan,
    tab_scenario,
    tab_sensitivity,
)
from views.sidebar import SidebarConfig, render_sidebar

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Turkey Logistics DSS",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject_css()


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
_DEFAULT_STATE = {
    "result": None,
    "scenario_run": None,
    "supply_used": None,
    "demand_used": None,
    "cost_used": None,
    "all_results": {},
    "saved_scenarios": {},
    "mc_result": None,
    "sens_result": None,
    "pareto_result": None,
    "real_distances": None,
    "real_durations": None,
}
for _key, _default in _DEFAULT_STATE.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

# CO₂ matrix is needed by several tabs; compute once per run.
st.session_state.co2_matrix = compute_co2_matrix()


# ---------------------------------------------------------------------------
# RUN / SAVE / COMPARE
# ---------------------------------------------------------------------------
def run_optimization(cfg: SidebarConfig) -> None:
    with st.spinner("Solving..."):
        if cfg.use_custom:
            supply     = cfg.custom_supply
            scen_mults = SCENARIOS[cfg.scenario]["demand_multipliers"]
            demand     = {w: round(cfg.custom_demand[w] * scen_mults[w])
                          for w in cfg.custom_demand}
            cost       = compute_cost_matrix(cfg.custom_fuel)
        else:
            supply, demand, cost = get_scenario_data(cfg.scenario)

        co2_mat = st.session_state.co2_matrix if cfg.co2_budget_on else None
        co2_bud = cfg.co2_budget_val if cfg.co2_budget_on else None
        result = solve(supply, demand, cost, co2_matrix=co2_mat, co2_budget=co2_bud)

        st.session_state.result       = result
        st.session_state.scenario_run = cfg.scenario
        st.session_state.supply_used  = supply
        st.session_state.demand_used  = demand
        st.session_state.cost_used    = cost


def handle_actions(cfg: SidebarConfig) -> None:
    if cfg.run_btn:
        run_optimization(cfg)

    if cfg.save_btn:
        res = st.session_state.result
        if res and res["status"] == "Optimal":
            key = st.session_state.scenario_run
            st.session_state.saved_scenarios[key] = {
                "total_cost": res["total_cost"],
                "shipments":  res["shipments"],
            }
            st.session_state.all_results = st.session_state.saved_scenarios
            st.sidebar.success(f"✓ '{key}' saved")
        else:
            st.sidebar.warning("Run optimization first.")

    if cfg.compare_btn:
        if st.session_state.saved_scenarios:
            st.session_state.all_results = st.session_state.saved_scenarios
        else:
            st.sidebar.warning("No scenarios saved yet.")


# ---------------------------------------------------------------------------
# RENDER
# ---------------------------------------------------------------------------
config = render_sidebar()
handle_actions(config)

header.render_header_kpis()

(tab_map_, tab_plan_, tab_cost_, tab_scenario_, tab_mc_, tab_sens_,
 tab_pareto_, tab_mp_, tab_dis_, tab_loc_, tab_model_) = st.tabs([
    "🗺️ Map", "📦 Optimal Plan", "💰 Cost Analysis",
    "📊 Scenario Comparison", "🎲 Monte Carlo",
    "🔍 Sensitivity Analysis", "🎯 Multi-Objective",
    "📅 Multi-Period", "⚠️ Disruption", "📍 Location",
    "📐 Model Formulation",
])

with tab_map_:
    tab_map.render()
with tab_plan_:
    tab_plan.render()
with tab_cost_:
    tab_cost.render()
with tab_scenario_:
    tab_scenario.render()
with tab_mc_:
    tab_montecarlo.render()
with tab_sens_:
    tab_sensitivity.render()
with tab_pareto_:
    tab_pareto.render()
with tab_mp_:
    tab_multiperiod.render()
with tab_dis_:
    tab_disruption.render()
with tab_loc_:
    tab_location.render()
with tab_model_:
    tab_model.render()
