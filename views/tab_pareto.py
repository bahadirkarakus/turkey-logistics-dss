"""Tab: Multi-objective Pareto frontier (cost vs travel time)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import multi_objective_pareto


def render() -> None:
    res = st.session_state.result

    st.markdown(
        "**Pareto Frontier** — trade-off between total cost (TL) and total "
        "weighted travel time (h·unit).  \n"
        "Each point is an optimal solution at a different weight combination."
    )

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
    if not (par and par["pareto"]):
        st.info("Run optimization, then press Compute Pareto.")
        return

    with col_p2:
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
