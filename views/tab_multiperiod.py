"""Tab: Demand forecast (Holt) + 4-quarter multi-period LP."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data import SCENARIOS
from forecasting import forecast_demand
from multiperiod import HOLDING_COST_PER_UNIT_PER_QUARTER, solve_multiperiod


def render() -> None:
    _render_forecast()
    _render_multiperiod()


def _render_forecast() -> None:
    with st.expander("📈 Demand Forecast (Holt Exponential Smoothing)", expanded=False):
        fc_col1, fc_col2 = st.columns([1, 3])
        with fc_col1:
            fc_alpha = st.slider("Alpha (level)", 0.05, 0.95, 0.40, 0.05,
                                 help="Higher = more weight on recent observations")
            fc_beta  = st.slider("Beta (trend)", 0.05, 0.50, 0.15, 0.05,
                                 help="Controls trend dampening")
            fc_btn   = st.button("📊 Generate Forecast", type="primary",
                                 use_container_width=True, key="fc_btn")
            st.checkbox("Use forecast as Q1-Q4 demand", value=False,
                        key="use_fc",
                        help="Overrides base demand in the LP below")

        if fc_btn:
            st.session_state["fc_result"] = forecast_demand(
                n_forecast=4, alpha=fc_alpha, beta=fc_beta,
            )

        fc_res = st.session_state.get("fc_result")
        if not fc_res:
            with fc_col2:
                st.info("Press **Generate Forecast** to run Holt smoothing on "
                        "synthetic historical data.")
            return

        quarters_hist = [f"H-Q{i + 1}" for i in range(8)]
        quarters_fct  = ["Q1", "Q2", "Q3", "Q4"]

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

        fc_rows = []
        for w, data in fc_res.items():
            row = {"Warehouse": w}
            for i, v in enumerate(data["forecast"]):
                row[f"Q{i + 1}"] = v
            fc_rows.append(row)
        st.dataframe(
            pd.DataFrame(fc_rows).set_index("Warehouse"),
            use_container_width=True,
        )


def _render_multiperiod() -> None:
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
            st.session_state["mp_result"] = solve_multiperiod(
                mp_scenario, holding_cost=mp_holding)

    mp_res = st.session_state.get("mp_result")
    if mp_res and mp_res["status"] == "Optimal":
        with col_mp2:
            k1, k2, k3 = st.columns(3)
            k1.metric("Total Cost", f"₺{mp_res['total_cost']:,.0f}")
            k2.metric("Transport Cost", f"₺{mp_res['transport_cost']:,.0f}")
            k3.metric("Holding Cost", f"₺{mp_res['holding_cost']:,.0f}")

        st.divider()
        q_names  = [q["period"] for q in mp_res["quarters"]]
        q_trans  = [q["transport_cost"] for q in mp_res["quarters"]]
        q_hold   = [q["holding_cost"] for q in mp_res["quarters"]]
        q_inv    = [sum(q["inventory"].values()) for q in mp_res["quarters"]]

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
