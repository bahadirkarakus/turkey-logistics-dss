"""Tab: Scenario comparison."""

import pandas as pd
import streamlit as st

from visualization import build_scenario_comparison


def render() -> None:
    all_results = st.session_state.all_results
    if not (all_results and len(all_results) > 0):
        st.info("Select scenario → Run Optimization → Save Result · "
                "After saving multiple scenarios press Compare Saved.")
        return

    st.plotly_chart(build_scenario_comparison(all_results), use_container_width=True)

    st.markdown('<div class="section-header">Scenario Summary Table</div>',
                unsafe_allow_html=True)

    base = list(all_results.values())[0]["total_cost"]
    rows = []
    for sname, r in all_results.items():
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

    st.markdown('<div class="section-header">Shipment Plans per Scenario</div>',
                unsafe_allow_html=True)
    for sname, r in all_results.items():
        with st.expander(f"📋 {sname}  —  ₺{r['total_cost']:,.0f}"):
            rows2 = [{"Route": f"{s} → {w}", "Birim": int(v)}
                     for (s, w), v in r["shipments"].items()]
            st.dataframe(pd.DataFrame(rows2), hide_index=True, use_container_width=True)
