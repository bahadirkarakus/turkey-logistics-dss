"""Tab: Sensitivity analysis — shadow prices and reduced costs."""

import pandas as pd
import streamlit as st

from analytics import sensitivity_analysis


def render() -> None:
    res = st.session_state.result

    st.markdown(
        "**Shadow price**: how much does total cost change when supply/demand "
        "increases by 1 unit?  \n"
        "**Reduced cost**: how much must a non-basic route's unit cost decrease "
        "to enter the optimal solution?"
    )

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
    if not sens:
        st.info("Run optimization, then start the sensitivity analysis.")
        return

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
