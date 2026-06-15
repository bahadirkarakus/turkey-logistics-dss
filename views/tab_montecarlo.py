"""Tab: Monte Carlo simulation under demand uncertainty."""

import plotly.graph_objects as go
import streamlit as st

from analytics import monte_carlo
from data import SOURCES, WAREHOUSES


def render() -> None:
    res = st.session_state.result

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
    if not mc:
        st.info("Select a scenario, run optimization, then start the simulation.")
        return

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
        fig_hist.add_vline(x=mc["mean_cost"], line_color="#E74C3C",
                           line_dash="dash", annotation_text="Mean")
        fig_hist.add_vline(x=mc["p5_cost"], line_color="#F39C12",
                           line_dash="dot", annotation_text="%5")
        fig_hist.add_vline(x=mc["p95_cost"], line_color="#F39C12",
                           line_dash="dot", annotation_text="%95")
        fig_hist.update_layout(
            title="Total Cost Distribution (Monte Carlo)",
            xaxis_title="Total Cost (TL)",
            yaxis_title="Frequency",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", height=350,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

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
