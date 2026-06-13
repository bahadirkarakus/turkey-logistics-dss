"""
Turkey Logistics DSS — Streamlit App
Transportation problem optimization tool (Turkey logistics network)
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from data import (
    SOURCES, WAREHOUSES, SCENARIOS,
    get_scenario_data, compute_cost_matrix, compute_co2_matrix,
    fetch_real_distances,
)
from model import solve, formulation_text
from visualization import (
    build_map, build_sankey, build_cost_breakdown,
    build_scenario_comparison, build_cost_heatmap,
)
from analytics import sensitivity_analysis, monte_carlo, multi_objective_pareto
from report import generate_pdf
from excel_export import generate_excel
from multiperiod import solve_multiperiod, QUARTERS, HOLDING_COST_PER_UNIT_PER_QUARTER
from forecasting import forecast_demand
from pmedian import solve_pmedian, ALL_LOCATIONS
from disruption import simulate_disruption

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Turkey Logistics DSS",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Base ──────────────────────────────────────────────────────────── */
    .main { background-color: #0e1117; }
    .block-container {
        padding-top: 1rem;
        overflow-x: hidden;   /* prevent horizontal scroll on mobile */
        max-width: 100%;
    }

    /* ── KPI grid — 6 cols desktop, 3 tablet, 2 phone ─────────────────── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 10px;
        margin-bottom: 8px;
    }
    @media (max-width: 1024px) {
        .kpi-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 600px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 6px; }
    }

    /* ── KPI card ──────────────────────────────────────────────────────── */
    .kpi-card {
        background: linear-gradient(135deg, #1a1f2e, #252d3d);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 14px 16px;
        text-align: center;
        min-width: 0;          /* allow grid cells to shrink */
        word-break: break-word;
    }
    .kpi-label {
        color: #8892a4; font-size: 0.72rem; text-transform: uppercase;
        letter-spacing: 0.05em; margin-bottom: 4px;
    }
    .kpi-value { color: #e2e8f0; font-size: 1.4rem; font-weight: 700; }
    .kpi-sub   { color: #68d391; font-size: 0.72rem; margin-top: 2px; }

    @media (max-width: 600px) {
        .kpi-value { font-size: 1.1rem; }
        .kpi-label { font-size: 0.65rem; }
    }

    /* ── Section header ────────────────────────────────────────────────── */
    .section-header {
        color: #e2e8f0; font-size: 1.05rem; font-weight: 600;
        border-left: 3px solid #3182ce; padding-left: 10px;
        margin: 14px 0 8px 0;
    }

    /* ── Tabs — scrollable on small screens ───────────────────────────── */
    div[data-testid="stTab"] button { font-size: 0.9rem; }
    div[data-testid="stTabs"] [role="tablist"] {
        overflow-x: auto;
        flex-wrap: nowrap;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    div[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar { display: none; }

    /* ── Tables & dataframes — don't overflow ──────────────────────────── */
    .stDataFrame { overflow-x: auto; }
    iframe { max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
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
    with st.expander("⚙️ Customise Parameters", expanded=False):
        st.markdown("**Fuel Multiplier**")
        custom_fuel = st.slider(
            "Fuel cost multiplier", 0.80, 2.00, 1.00, 0.05,
            help="1.20 = fuel price up 20%",
        )

        st.markdown("**Supply Capacities**")
        custom_supply = {}
        for src, info in SOURCES.items():
            custom_supply[src] = st.number_input(
                src, min_value=0, max_value=2000,
                value=info["capacity"], step=50, key=f"sup_{src}",
            )

        st.markdown("**Demand Values**")
        custom_demand = {}
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
    run_btn  = st.button("▶ Run Optimization", type="primary", use_container_width=True)
    save_btn = st.button("💾 Save Result", use_container_width=True)
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


# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------
if "result"       not in st.session_state: st.session_state.result       = None
if "scenario_run" not in st.session_state: st.session_state.scenario_run = None
if "supply_used"  not in st.session_state: st.session_state.supply_used  = None
if "demand_used"  not in st.session_state: st.session_state.demand_used  = None
if "cost_used"    not in st.session_state: st.session_state.cost_used    = None
if "all_results"      not in st.session_state: st.session_state.all_results      = {}
if "saved_scenarios"  not in st.session_state: st.session_state.saved_scenarios  = {}
if "mc_result"        not in st.session_state: st.session_state.mc_result        = None
if "sens_result"      not in st.session_state: st.session_state.sens_result      = None
if "pareto_result"    not in st.session_state: st.session_state.pareto_result    = None
if "real_distances"   not in st.session_state: st.session_state.real_distances   = None
if "real_durations"   not in st.session_state: st.session_state.real_durations   = None


# ---------------------------------------------------------------------------
# RUN OPTIMIZATION
# ---------------------------------------------------------------------------
def run_optimization(scen_name, use_cust):
    with st.spinner("Solving..."):
        if use_cust:
            supply = custom_supply
            demand_raw = custom_demand
            # Apply scenario demand multipliers on top of custom demand
            scen_mults = SCENARIOS[scen_name]["demand_multipliers"]
            demand = {w: round(demand_raw[w] * scen_mults[w]) for w in demand_raw}
            cost   = compute_cost_matrix(custom_fuel)
        else:
            supply, demand, cost = get_scenario_data(scen_name)

        co2_mat = _co2_matrix if co2_budget_on else None
        co2_bud = co2_budget_val if co2_budget_on else None
        result = solve(supply, demand, cost, co2_matrix=co2_mat, co2_budget=co2_bud)
        st.session_state.result       = result
        st.session_state.scenario_run = scen_name
        st.session_state.supply_used  = supply
        st.session_state.demand_used  = demand
        st.session_state.cost_used    = cost


if run_btn:
    run_optimization(scenario, use_custom)

if save_btn:
    if st.session_state.result and st.session_state.result["status"] == "Optimal":
        key = st.session_state.scenario_run
        st.session_state.saved_scenarios[key] = {
            "total_cost": st.session_state.result["total_cost"],
            "shipments":  st.session_state.result["shipments"],
        }
        st.session_state.all_results = st.session_state.saved_scenarios
        st.sidebar.success(f"✓ '{key}' saved")
    else:
        st.sidebar.warning("Run optimization first.")

if compare_btn:
    if st.session_state.saved_scenarios:
        st.session_state.all_results = st.session_state.saved_scenarios
    else:
        st.sidebar.warning("No scenarios saved yet.")


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown("# 🚛 Turkey Logistics Decision-Support System")
st.markdown(
    "Find the **minimum-cost** shipment plan from production centres to warehouses "
    "· Scenario analysis · Map visualisation"
)
st.divider()

# ---------------------------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------------------------
res = st.session_state.result

total_supply      = sum(SOURCES[s]["capacity"] for s in SOURCES)
total_demand_base = sum(WAREHOUSES[w]["demand"] for w in WAREHOUSES)
_co2_matrix       = compute_co2_matrix()

# KPI values
cost_val   = f"₺{res['total_cost']:,.0f}" if res else "—"
cost_sub   = "Optimal ✓" if res else "Not solved yet"
if res:
    _total_co2 = sum(_co2_matrix[s][w] * v for (s, w), v in res["shipments"].items())
    co2_val, co2_sub = f"{_total_co2:,.0f} kg", f"{_total_co2/1000:.2f} t CO₂"
else:
    co2_val, co2_sub = "—", "not solved yet"
scen_label = st.session_state.scenario_run or "—"
routes_n   = len(res["shipments"]) if res else "—"
dem_used   = sum(st.session_state.demand_used.values()) if st.session_state.demand_used else total_demand_base

# Single HTML block — CSS Grid handles responsive layout
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

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_map, tab_plan, tab_cost, tab_scenario, tab_mc, tab_sens, tab_pareto, tab_mp, tab_dis, tab_loc, tab_model = st.tabs([
    "🗺️ Map", "📦 Optimal Plan", "💰 Cost Analysis",
    "📊 Scenario Comparison", "🎲 Monte Carlo",
    "🔍 Sensitivity Analysis", "🎯 Multi-Objective",
    "📅 Multi-Period", "⚠️ Disruption", "📍 Location",
    "📐 Model Formulation",
])

# ── TAB 1: MAP ──────────────────────────────────────────────────────────────
with tab_map:
    if res and res["status"] == "Optimal":
        fmap = build_map(
            res["shipments"],
            st.session_state.supply_used,
            st.session_state.demand_used,
        )
        st_folium(fmap, width="100%", height=540)
        st.caption("🔴 Production centre · 🟢 Warehouse · Line thickness = shipment volume")
    else:
        # Default map without routes
        default_map = build_map({}, {s: SOURCES[s]["capacity"] for s in SOURCES},
                                 {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES})
        st_folium(default_map, width="100%", height=540)
        st.info("Run optimization → routes appear on the map.")

# ── TAB 2: OPTIMAL PLAN ─────────────────────────────────────────────────────
with tab_plan:
    if res and res["status"] == "Optimal":
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
                df_plan.style.map(
                    highlight,
                    subset=[w for w in whs],
                ),
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
            co2_unit = _co2_matrix[s][w]
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

        total_co2 = sum(_co2_matrix[s][w] * v for (s, w), v in ships.items())
        col_cost, col_co2 = st.columns(2)
        col_cost.success(f"**Minimum Total Cost: ₺{res['total_cost']:,.2f}**")
        col_co2.info(f"**Total CO₂ Emissions: {total_co2:,.1f} kg ({total_co2/1000:.2f} t)**")

        # Excel download
        st.divider()
        excel_bytes = generate_excel(
            res, sup, dem, cost, _co2_matrix,
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

    else:
        st.info("Select a scenario from the sidebar and press **Run Optimization**.")

# ── TAB 3: COST ANALYSIS ────────────────────────────────────────────────────
with tab_cost:
    if res and res["status"] == "Optimal":
        cost = st.session_state.cost_used
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
    else:
        st.info("Run optimization first.")

# ── TAB 4: SCENARIO COMPARISON ──────────────────────────────────────────────
with tab_scenario:
    if st.session_state.all_results and len(st.session_state.all_results) > 0:
        all_res = st.session_state.all_results
        st.plotly_chart(build_scenario_comparison(all_res), use_container_width=True)

        st.markdown('<div class="section-header">Scenario Summary Table</div>',
                    unsafe_allow_html=True)

        base = list(all_res.values())[0]["total_cost"]
        rows = []
        for sname, r in all_res.items():
            tc  = r["total_cost"]
            pct = round((tc - base) / base * 100, 1) if base else 0
            rows.append({
                "Scenario": sname,
                "Total Cost": f"₺{tc:,.2f}",
                "Delta (TL)": f"{tc - base:+,.2f}",
                "Delta (%)": f"{pct:+.1f}%",
                "Active Routes": len(r["shipments"]),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Per-scenario shipment comparison
        st.markdown('<div class="section-header">Shipment Plans per Scenario</div>',
                    unsafe_allow_html=True)
        for sname, r in all_res.items():
            with st.expander(f"📋 {sname}  —  ₺{r['total_cost']:,.0f}"):
                rows2 = [{"Route": f"{s} → {w}", "Birim": int(v)}
                         for (s, w), v in r["shipments"].items()]
                st.dataframe(pd.DataFrame(rows2), hide_index=True, use_container_width=True)
    else:
        st.info("Select scenario → Run Optimization → Save Result · After saving multiple scenarios press Compare Saved.")

# ── TAB 5: MONTE CARLO ──────────────────────────────────────────────────────
with tab_mc:
    import plotly.graph_objects as go

    st.markdown("Simulates cost distribution under demand uncertainty. "
                "Each iteration samples demand from a normal distribution and solves the LP.")

    col_mc1, col_mc2 = st.columns([1, 2])
    with col_mc1:
        n_sim = st.slider("Number of simulations", 50, 500, 200, 50)
        cv    = st.slider("Demand uncertainty (CV)", 0.05, 0.35, 0.15, 0.05,
                          help="Coefficient of variation — 0.15 = ±15% std dev")
        run_mc = st.button("🎲 Run Simulation", type="primary")

    if run_mc:
        if res and res["status"] == "Optimal":
            with st.spinner(f"{n_sim} iterations solving..."):
                st.session_state.mc_result = monte_carlo(
                    st.session_state.supply_used,
                    st.session_state.demand_used,
                    st.session_state.cost_used,
                    n_simulations=n_sim,
                    demand_cv=cv,
                )
        else:
            st.warning("Run Optimization first.")

    mc = st.session_state.mc_result
    if mc:
        with col_mc1:
            st.metric("Mean Cost",   f"₺{mc['mean_cost']:,.0f}")
            st.metric("Std Dev",          f"₺{mc['std_cost']:,.0f}")
            st.metric("5th Percentile",         f"₺{mc['p5_cost']:,.0f}")
            st.metric("95th Percentile",        f"₺{mc['p95_cost']:,.0f}")
            st.metric("Infeasible iterations", mc["n_infeasible"])

        with col_mc2:
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=mc["costs"], nbinsx=30,
                marker_color="#3498DB", opacity=0.8,
                name="Cost distribution",
            ))
            fig_hist.add_vline(x=mc["mean_cost"],  line_color="#E74C3C",
                               line_dash="dash", annotation_text="Mean")
            fig_hist.add_vline(x=mc["p5_cost"],    line_color="#F39C12",
                               line_dash="dot",  annotation_text="%5")
            fig_hist.add_vline(x=mc["p95_cost"],   line_color="#F39C12",
                               line_dash="dot",  annotation_text="%95")
            fig_hist.update_layout(
                title="Total Cost Distribution (Monte Carlo)",
                xaxis_title="Total Cost (TL)",
                yaxis_title="Frequency",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", height=350,
            )
            st.plotly_chart(fig_hist, use_container_width=True)

        # Route reliability heatmap
        st.markdown('<div class="section-header">Route Reliability (% of iterations in use)</div>',
                    unsafe_allow_html=True)
        sources_list = list(SOURCES.keys())
        whs_list     = list(WAREHOUSES.keys())
        rel_matrix   = [[mc["route_reliability"].get((s, w), 0) for w in whs_list]
                        for s in sources_list]
        fig_rel = go.Figure(go.Heatmap(
            z=rel_matrix, x=whs_list, y=sources_list,
            colorscale="RdYlGn", zmin=0, zmax=100,
            text=[[f"{v:.0f}%" for v in row] for row in rel_matrix],
            texttemplate="%{text}",
            hovertemplate="%{y} → %{x}: %{z:.1f}%<extra></extra>",
            colorbar=dict(title="%"),
        ))
        fig_rel.update_layout(
            height=280, paper_bgcolor="#0e1117",
            font_color="white", margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig_rel, use_container_width=True)
    else:
        st.info("Select a scenario, run optimization, then start the simulation.")


# ── TAB 6: SENSITIVITY ANALYSIS ─────────────────────────────────────────────
with tab_sens:
    st.markdown("**Shadow price**: how much does total cost change when supply/demand increases by 1 unit?  \n"
                "**Reduced cost**: how much must a non-basic route's unit cost decrease to enter the optimal solution?")

    run_sens = st.button("🔍 Run Sensitivity Analysis", type="primary")

    if run_sens:
        if res and res["status"] == "Optimal":
            with st.spinner("Computing dual variables..."):
                st.session_state.sens_result = sensitivity_analysis(
                    st.session_state.supply_used,
                    st.session_state.demand_used,
                    st.session_state.cost_used,
                )
        else:
            st.warning("Run Optimization first.")

    sens = st.session_state.sens_result
    if sens:
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.markdown('<div class="section-header">Supply Shadow Prices</div>',
                        unsafe_allow_html=True)
            st.caption("1 extra unit of supply reduces total cost by (TL)")
            df_sp_sup = pd.DataFrame([
                {"Production Centre": s, "Shadow Price (TL/unit)": v}
                for s, v in sens["shadow_supply"].items()
            ])
            st.dataframe(df_sp_sup, hide_index=True, use_container_width=True)

            st.markdown("")
            st.markdown('<div class="section-header">Demand Shadow Prices</div>',
                        unsafe_allow_html=True)
            st.caption("1 units fazla talep → toplam maliyet bu kadar artar (TL)")
            df_sp_dem = pd.DataFrame([
                {"Warehouse": w, "Shadow Price (TL/unit)": v}
                for w, v in sens["shadow_demand"].items()
            ])
            st.dataframe(df_sp_dem, hide_index=True, use_container_width=True)

        with col_s2:
            st.markdown('<div class="section-header">Unused Route Reduced Costs</div>',
                        unsafe_allow_html=True)
            st.caption("Route enters optimal plan if unit cost drops by this much")
            rc_rows = [
                {"Route": f"{s} → {w}", "Reduced Cost (TL/units)": v}
                for (s, w), v in sorted(sens["reduced_costs"].items(),
                                        key=lambda x: abs(x[1]))
            ]
            st.dataframe(pd.DataFrame(rc_rows), hide_index=True, use_container_width=True)
    else:
        st.info("Run optimization, then start the sensitivity analysis.")


# ── TAB 7: MULTI-OBJECTIVE PARETO ───────────────────────────────────────────
with tab_pareto:
    st.markdown("**Pareto Frontier** — trade-off between total cost (TL) and total weighted travel time (h·unit).  \n"
                "Each point is an optimal solution at a different weight combination.")

    col_p1, col_p2 = st.columns([1, 3])
    with col_p1:
        n_pts   = st.slider("Number of Pareto points", 5, 20, 10)
        run_par = st.button("🎯 Compute Pareto", type="primary")

    if run_par:
        if res and res["status"] == "Optimal":
            with st.spinner("Computing Pareto frontier..."):
                st.session_state.pareto_result = multi_objective_pareto(
                    st.session_state.supply_used,
                    st.session_state.demand_used,
                    st.session_state.cost_used,
                    n_points=n_pts,
                )
        else:
            st.warning("Run Optimization first.")

    par = st.session_state.pareto_result
    if par and par["pareto"]:
        with col_p2:
            import plotly.express as px
            df_par = pd.DataFrame(par["pareto"])
            fig_par = go.Figure()
            fig_par.add_trace(go.Scatter(
                x=df_par["cost"], y=df_par["time"],
                mode="lines+markers+text",
                text=[f"α={p['alpha']:.2f}" for p in par["pareto"]],
                textposition="top center",
                marker=dict(size=10, color=df_par["alpha"],
                            colorscale="Viridis", showscale=True,
                            colorbar=dict(title="alpha (cost weight)")),
                line=dict(color="#3498DB", width=2),
                hovertemplate="Cost: ₺%{x:,.0f}<br>Time: %{y:.1f} h<extra></extra>",
            ))
            fig_par.update_layout(
                title="Pareto Frontier — Cost vs Travel Time",
                xaxis_title="Total Cost (TL)",
                yaxis_title="Total Travel Time (h·unit)",
                height=420,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white",
                xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
            )
            st.plotly_chart(fig_par, use_container_width=True)

        st.markdown('<div class="section-header">Pareto Points</div>',
                    unsafe_allow_html=True)
        st.caption("α=1 → cost only · α=0 → time only")
        st.dataframe(
            pd.DataFrame(par["pareto"]).rename(columns={
                "alpha": "alpha (cost weight)",
                "cost": "Cost (TL)",
                "time": "Time (h·unit)",
            }),
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("Run optimization, then press Compute Pareto.")


# ── PDF EXPORT (visible in sidebar after result exists) ─────────────────────
if res and res["status"] == "Optimal":
    with st.sidebar:
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


# ── TAB 8: MULTI-PERIOD ──────────────────────────────────────────────────────
with tab_mp:
    # ── Demand Forecast sub-section ──────────────────────────────────────────
    with st.expander("📈 Demand Forecast (Holt Exponential Smoothing)", expanded=False):
        fc_col1, fc_col2 = st.columns([1, 3])
        with fc_col1:
            fc_alpha = st.slider("Alpha (level)", 0.05, 0.95, 0.40, 0.05,
                                 help="Higher = more weight on recent observations")
            fc_beta  = st.slider("Beta (trend)", 0.05, 0.50, 0.15, 0.05,
                                 help="Controls trend dampening")
            fc_btn   = st.button("📊 Generate Forecast", type="primary",
                                 use_container_width=True, key="fc_btn")
            use_fc   = st.checkbox("Use forecast as Q1-Q4 demand", value=False,
                                   key="use_fc",
                                   help="Overrides base demand in the LP below")

        if fc_btn:
            st.session_state["fc_result"] = forecast_demand(
                n_forecast=4, alpha=fc_alpha, beta=fc_beta,
            )

        fc_res = st.session_state.get("fc_result")
        if fc_res:
            import plotly.graph_objects as go
            quarters_hist = [f"H-Q{i+1}" for i in range(8)]
            quarters_fct  = ["Q1", "Q2", "Q3", "Q4"]
            x_all         = quarters_hist + quarters_fct

            with fc_col2:
                fig_fc = go.Figure()
                colors = ["#3498DB", "#E74C3C", "#2ECC71", "#F39C12",
                          "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"]
                for idx, (w, data) in enumerate(fc_res.items()):
                    c = colors[idx % len(colors)]
                    fig_fc.add_trace(go.Scatter(
                        x=quarters_hist, y=data["history"],
                        mode="markers", name=f"{w} actual",
                        marker=dict(color=c, size=7), legendgroup=w,
                        showlegend=True,
                    ))
                    fig_fc.add_trace(go.Scatter(
                        x=quarters_hist, y=data["smoothed"],
                        mode="lines", name=f"{w} smoothed",
                        line=dict(color=c, width=1.5, dash="dot"),
                        legendgroup=w, showlegend=False,
                    ))
                    fig_fc.add_trace(go.Scatter(
                        x=quarters_fct, y=data["forecast"],
                        mode="lines+markers", name=f"{w} forecast",
                        line=dict(color=c, width=2, dash="dash"),
                        marker=dict(symbol="diamond", size=8),
                        legendgroup=w, showlegend=False,
                    ))
                fig_fc.add_vrect(
                    x0="Q1", x1="Q4",
                    fillcolor="#2ECC71", opacity=0.05,
                    annotation_text="Forecast horizon", annotation_position="top left",
                )
                fig_fc.update_layout(
                    title="Historical Demand + Forecast (Holt Smoothing)",
                    xaxis_title="Quarter", yaxis_title="Units",
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font_color="white", height=340,
                    xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
                )
                st.plotly_chart(fig_fc, use_container_width=True)

            # Forecast table
            fc_rows = []
            for w, data in fc_res.items():
                row = {"Warehouse": w}
                for i, v in enumerate(data["forecast"]):
                    row[f"Q{i+1}"] = v
                fc_rows.append(row)
            st.dataframe(
                pd.DataFrame(fc_rows).set_index("Warehouse"),
                use_container_width=True,
            )
        else:
            with fc_col2:
                st.info("Press **Generate Forecast** to run Holt smoothing on synthetic historical data.")

with tab_mp:
    st.markdown(
        "**4-quarter LP** with inventory carryover. "
        "Annual capacity is split evenly across quarters; "
        "seasonal demand multipliers shift load between periods."
    )
    col_mp1, col_mp2 = st.columns([1, 3])
    with col_mp1:
        mp_scenario = st.selectbox("Scenario", list(SCENARIOS.keys()), key="mp_scen")
        mp_holding  = st.number_input("Holding cost (TL/unit/quarter)",
                                       min_value=0.0, max_value=50.0,
                                       value=float(HOLDING_COST_PER_UNIT_PER_QUARTER),
                                       step=1.0, key="mp_hold")
        mp_run = st.button("▶ Solve Multi-Period", type="primary",
                            use_container_width=True, key="mp_btn")

    if mp_run:
        with st.spinner("Solving 4-quarter LP..."):
            mp_result = solve_multiperiod(mp_scenario, holding_cost=mp_holding)
            st.session_state["mp_result"] = mp_result

    mp_res = st.session_state.get("mp_result")
    if mp_res and mp_res["status"] == "Optimal":
        with col_mp2:
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Cost", f"₺{mp_res['total_cost']:,.0f}")
            k2.metric("Transport Cost", f"₺{mp_res['transport_cost']:,.0f}")
            k3.metric("Holding Cost", f"₺{mp_res['holding_cost']:,.0f}")

        st.divider()
        # Quarter-by-quarter summary table
        import plotly.graph_objects as go
        q_names   = [q["period"] for q in mp_res["quarters"]]
        q_trans   = [q["transport_cost"] for q in mp_res["quarters"]]
        q_hold    = [q["holding_cost"]   for q in mp_res["quarters"]]
        q_inv     = [sum(q["inventory"].values()) for q in mp_res["quarters"]]
        q_routes  = [len(q["shipments"]) for q in mp_res["quarters"]]

        fig_mp = go.Figure()
        fig_mp.add_trace(go.Bar(name="Transport Cost", x=q_names, y=q_trans,
                                marker_color="#3498DB",
                                text=[f"₺{v:,.0f}" for v in q_trans],
                                textposition="inside"))
        fig_mp.add_trace(go.Bar(name="Holding Cost", x=q_names, y=q_hold,
                                marker_color="#F39C12",
                                text=[f"₺{v:,.0f}" for v in q_hold],
                                textposition="inside"))
        fig_mp.add_trace(go.Scatter(name="End Inventory (units)", x=q_names, y=q_inv,
                                    yaxis="y2", mode="lines+markers+text",
                                    text=[f"{v:.0f}" for v in q_inv],
                                    textposition="top center",
                                    line=dict(color="#2ECC71", width=2, dash="dot"),
                                    marker=dict(size=9)))
        fig_mp.update_layout(
            barmode="stack",
            title="Cost Breakdown & Inventory by Quarter",
            yaxis=dict(title="Cost (TL)", gridcolor="#333"),
            yaxis2=dict(title="Inventory (units)", overlaying="y", side="right"),
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="white",
            xaxis=dict(gridcolor="#333"),
            legend=dict(orientation="h", y=1.08),
            height=380,
        )
        st.plotly_chart(fig_mp, use_container_width=True)

        st.divider()
        st.markdown('<div class="section-header">Quarter Details</div>',
                    unsafe_allow_html=True)
        for q in mp_res["quarters"]:
            with st.expander(f"**{q['period']}** — {len(q['shipments'])} routes · "
                             f"TL {q['transport_cost']:,.0f} transport · "
                             f"{sum(q['inventory'].values()):.0f} units inventory"):
                rows = []
                for (s, w), units in sorted(q["shipments"].items(), key=lambda x: -x[1]):
                    rows.append({"Source": s, "Warehouse": w,
                                 "Units": int(units),
                                 "Demand": q["demand"][w]})
                st.dataframe(pd.DataFrame(rows), use_container_width=True,
                             hide_index=True)
                inv_df = pd.DataFrame([
                    {"Source": s, "End Inventory (units)": int(v)}
                    for s, v in q["inventory"].items() if v > 0
                ])
                if not inv_df.empty:
                    st.dataframe(inv_df, use_container_width=True, hide_index=True)
    elif mp_res:
        st.error(f"Solver status: {mp_res['status']} — check supply/demand balance.")
    else:
        st.info("Press **Solve Multi-Period** to run the 4-quarter LP.")


# ── TAB 9: DISRUPTION SIMULATION ─────────────────────────────────────────────
with tab_dis:
    import plotly.graph_objects as go
    import folium

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
    if dr:
        with col_d2:
            base_ok = dr["base"]["status"] == "Optimal"
            dis_ok  = dr["disrupted"]["status"] == "Optimal"

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Base Cost", f"₺{dr['base']['total_cost']:,.0f}" if base_ok else "—")
            if dis_ok:
                m2.metric("Disrupted Cost", f"₺{dr['disrupted']['total_cost']:,.0f}",
                          delta=f"₺{dr['cost_delta']:+,.0f}" if dr['cost_delta'] else None,
                          delta_color="inverse")
                m3.metric("Cost Impact", f"{dr['cost_delta_pct']:+.1f}%" if dr['cost_delta_pct'] else "—")
            else:
                m2.metric("Disrupted Cost", "INFEASIBLE")
                m3.metric("Cost Impact", "Cannot serve demand")
            m4.metric("Lost Routes", len(dr["lost_routes"]))

        st.divider()

        if dis_ok:
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
            # Cost comparison bar chart
            fig_dis = go.Figure()
            fig_dis.add_trace(go.Bar(
                name="Base",
                x=["Total Cost"],
                y=[dr["base"]["total_cost"]],
                marker_color="#3498DB",
                text=[f"₺{dr['base']['total_cost']:,.0f}"],
                textposition="outside",
            ))
            fig_dis.add_trace(go.Bar(
                name="Disrupted",
                x=["Total Cost"],
                y=[dr["disrupted"]["total_cost"]],
                marker_color="#E74C3C",
                text=[f"₺{dr['disrupted']['total_cost']:,.0f}"],
                textposition="outside",
            ))

            # Supply comparison
            fig_dis.update_layout(
                title="Base vs Disrupted Total Cost",
                barmode="group",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", height=300,
                yaxis=dict(title="Cost (TL)", gridcolor="#333"),
            )
            st.plotly_chart(fig_dis, use_container_width=True)

            # Disruption map
            st.markdown('<div class="section-header">Network Map</div>',
                        unsafe_allow_html=True)
            st.caption("🔵 Unchanged routes · 🔴 Lost routes · 🟢 New routes")

            dmap = folium.Map(location=[39.0, 35.0], zoom_start=6,
                              tiles="CartoDB dark_matter")

            # Sources
            for src, info in SOURCES.items():
                is_disabled = src in (disabled_srcs or [])
                cap_frac    = cap_fracs.get(src, 1.0)
                color       = "#888888" if is_disabled else ("#F39C12" if cap_frac < 1.0 else "#E74C3C")
                label       = f"{src} ({'DISABLED' if is_disabled else f'{int(cap_frac*100)}%'})"
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

            # Unchanged routes (blue)
            for (s, w) in dr["unchanged_routes"]:
                folium.PolyLine(
                    [[SOURCES[s]["lat"], SOURCES[s]["lon"]],
                     [WAREHOUSES[w]["lat"], WAREHOUSES[w]["lon"]]],
                    color="#3498DB", weight=2, opacity=0.6,
                    tooltip=f"{s}→{w} (unchanged)",
                ).add_to(dmap)

            # Lost routes (red dashed)
            for (s, w) in dr["lost_routes"]:
                folium.PolyLine(
                    [[SOURCES[s]["lat"], SOURCES[s]["lon"]],
                     [WAREHOUSES[w]["lat"], WAREHOUSES[w]["lon"]]],
                    color="#E74C3C", weight=3, opacity=0.9,
                    dash_array="8 4",
                    tooltip=f"{s}→{w} (LOST)",
                ).add_to(dmap)

            # New routes (green)
            for (s, w) in dr["new_routes"]:
                folium.PolyLine(
                    [[SOURCES[s]["lat"], SOURCES[s]["lon"]],
                     [WAREHOUSES[w]["lat"], WAREHOUSES[w]["lon"]]],
                    color="#2ECC71", weight=3, opacity=0.9,
                    tooltip=f"{s}→{w} (NEW)",
                ).add_to(dmap)

            st_folium(dmap, width="100%", height=450)
        else:
            st.error(
                "Disruption makes the problem **infeasible** — "
                "remaining supply cannot cover all warehouse demand. "
                "Try enabling more sources or reducing partial capacity cuts."
            )
    else:
        st.info("Configure disruption settings and press **Simulate Disruption**.")


# ── TAB 10: LOCATION OPTIMIZATION (P-MEDIAN) ─────────────────────────────────
with tab_loc:
    import plotly.graph_objects as go

    st.markdown(
        "**P-Median Facility Location** — given 13 candidate cities (5 sources + 8 warehouses), "
        "find which *p* locations minimise total **demand × distance** (km·units). "
        "Useful for deciding where to open new distribution hubs."
    )

    col_l1, col_l2 = st.columns([1, 3])
    with col_l1:
        p_val   = st.slider("Number of facilities (p)", 1, 8, 3)
        loc_btn = st.button("📍 Find Optimal Locations", type="primary",
                            use_container_width=True, key="loc_btn")

    if loc_btn:
        with st.spinner(f"Solving p={p_val} median MIP..."):
            loc_result = solve_pmedian(p=p_val)
        st.session_state["loc_result"] = loc_result
        st.session_state["loc_p"]      = p_val

    lr = st.session_state.get("loc_result")
    if lr and lr["status"] == "Optimal":
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

            # Colour palette for facilities
            palette = ["#F39C12", "#3498DB", "#E74C3C", "#2ECC71",
                       "#9B59B6", "#1ABC9C", "#E67E22", "#34495E"]
            fac_color = {fac: palette[i % len(palette)]
                         for i, fac in enumerate(lr["selected"])}

            # Draw assignment lines (demand node → assigned facility)
            for node, fac in lr["assignment"].items():
                n_loc = ALL_LOCATIONS[node]
                f_loc = ALL_LOCATIONS[fac]
                folium.PolyLine(
                    [[n_loc["lat"], n_loc["lon"]],
                     [f_loc["lat"],  f_loc["lon"]]],
                    color=fac_color[fac], weight=2, opacity=0.5,
                    tooltip=f"{node} → {fac}",
                ).add_to(loc_map)

            # All candidate cities (small grey)
            for city, loc in ALL_LOCATIONS.items():
                if city not in lr["selected"]:
                    folium.CircleMarker(
                        [loc["lat"], loc["lon"]], radius=5,
                        color="#555", fill=True, fill_opacity=0.5,
                        tooltip=city,
                    ).add_to(loc_map)

            # Selected facilities (large, coloured)
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

            # Demand nodes (coloured by assignment)
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
                served   = [n for n, f in lr["assignment"].items() if f == fac]
                tot_d    = sum(
                    WAREHOUSES.get(n, {}).get("demand", 0) * lr["dist_matrix"][n][fac]
                    for n in served
                )
                hub_rows.append({
                    "Hub":              fac,
                    "Serves":           len(served),
                    "Total km·units":   f"{tot_d:,.0f}",
                })
            st.dataframe(pd.DataFrame(hub_rows), hide_index=True, use_container_width=True)

            # p comparison chart (solve for p=1..p+2 for context)
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
    elif lr:
        st.error(f"Solver status: {lr['status']}")
    else:
        st.info("Set p and press **Find Optimal Locations**.")


# ── TAB 11: MODEL FORMULATION ─────────────────────────────────────────────────
with tab_model:
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
        st.markdown('<div class="section-header">Solution Summary</div>', unsafe_allow_html=True)
        slack_df = pd.DataFrame([
            {"Source": s, "Slack Capacity": int(v)}
            for s, v in res["slack"].items()
        ])
        st.dataframe(slack_df, hide_index=True, use_container_width=True)
