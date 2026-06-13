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
    .main { background-color: #0e1117; }
    .block-container { padding-top: 1rem; }
    .kpi-card {
        background: linear-gradient(135deg, #1a1f2e, #252d3d);
        border: 1px solid #2d3748;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        margin-bottom: 4px;
    }
    .kpi-label { color: #8892a4; font-size: 0.78rem; text-transform: uppercase;
                 letter-spacing: 0.05em; margin-bottom: 4px; }
    .kpi-value { color: #e2e8f0; font-size: 1.55rem; font-weight: 700; }
    .kpi-sub   { color: #68d391; font-size: 0.78rem; margin-top: 2px; }
    .section-header {
        color: #e2e8f0; font-size: 1.05rem; font-weight: 600;
        border-left: 3px solid #3182ce; padding-left: 10px; margin: 14px 0 8px 0;
    }
    div[data-testid="stTab"] button { font-size: 0.9rem; }
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

        result = solve(supply, demand, cost)
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

c1, c2, c3, c4, c5, c6 = st.columns(6)
total_supply      = sum(SOURCES[s]["capacity"] for s in SOURCES)
total_demand_base = sum(WAREHOUSES[w]["demand"] for w in WAREHOUSES)
_co2_matrix       = compute_co2_matrix()

with c1:
    cost_val = f"₺{res['total_cost']:,.0f}" if res else "—"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Minimum Cost</div>
        <div class="kpi-value">{cost_val}</div>
        <div class="kpi-sub">{'Optimal ✓' if res else 'Not solved yet'}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    if res:
        total_co2 = sum(
            _co2_matrix[s][w] * v
            for (s, w), v in res["shipments"].items()
        )
        co2_val = f"{total_co2:,.0f} kg"
        co2_sub = f"{total_co2/1000:.2f} t CO₂"
    else:
        co2_val, co2_sub = "—", "not solved yet"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Total CO₂</div>
        <div class="kpi-value" style="font-size:1.2rem">{co2_val}</div>
        <div class="kpi-sub">{co2_sub}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    scen_label = st.session_state.scenario_run or "—"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Active Scenario</div>
        <div class="kpi-value" style="font-size:1.1rem">{scen_label}</div>
        <div class="kpi-sub">&nbsp;</div>
    </div>""", unsafe_allow_html=True)

with c4:
    routes_n = len(res["shipments"]) if res else "—"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Active Routes</div>
        <div class="kpi-value">{routes_n}</div>
        <div class="kpi-sub">of 40 possible routes</div>
    </div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Total Supply</div>
        <div class="kpi-value">{total_supply:,}</div>
        <div class="kpi-sub">units capacity</div>
    </div>""", unsafe_allow_html=True)

with c6:
    dem_used = sum(st.session_state.demand_used.values()) if st.session_state.demand_used else total_demand_base
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Total Demand</div>
        <div class="kpi-value">{dem_used:,}</div>
        <div class="kpi-sub">units</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_map, tab_plan, tab_cost, tab_scenario, tab_mc, tab_sens, tab_pareto, tab_model = st.tabs([
    "🗺️ Map", "📦 Optimal Plan", "💰 Cost Analysis",
    "📊 Scenario Comparison", "🎲 Monte Carlo",
    "🔍 Sensitivity Analysis", "🎯 Multi-Objective",
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


# ── TAB 8: MODEL FORMULATION ─────────────────────────────────────────────────
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
