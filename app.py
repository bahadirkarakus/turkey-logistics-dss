"""
Turkey Logistics DSS — Streamlit App
Ulaştırma problemi optimizasyon aracı (Türkiye lojistik ağı)
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

from data import (
    SOURCES, WAREHOUSES, SCENARIOS,
    get_scenario_data, compute_cost_matrix,
)
from model import solve, formulation_text
from visualization import (
    build_map, build_sankey, build_cost_breakdown,
    build_scenario_comparison, build_cost_heatmap,
)

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Türkiye Lojistik DSS",
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
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/"
        "Flag_of_Turkey.svg/320px-Flag_of_Turkey.svg.png",
        width=80,
    )
    st.markdown("## 🚛 Türkiye Lojistik DSS")
    st.caption("Ulaştırma Problemi Optimizasyon Aracı")
    st.divider()

    # Scenario picker
    scenario = st.selectbox(
        "Senaryo",
        list(SCENARIOS.keys()),
        help="Çalıştırılacak senaryoyu seçin.",
    )
    st.caption(f"*{SCENARIOS[scenario]['description']}*")
    st.divider()

    # Custom parameter overrides
    with st.expander("⚙️ Parametreleri Özelleştir", expanded=False):
        st.markdown("**Yakıt Çarpanı**")
        custom_fuel = st.slider(
            "Yakıt maliyet çarpanı", 0.80, 2.00, 1.00, 0.05,
            help="1.20 = yakıt fiyatı %20 arttı",
        )

        st.markdown("**Arz Kapasiteleri**")
        custom_supply = {}
        for src, info in SOURCES.items():
            custom_supply[src] = st.number_input(
                src, min_value=0, max_value=2000,
                value=info["capacity"], step=50, key=f"sup_{src}",
            )

        st.markdown("**Talep Değerleri**")
        custom_demand = {}
        for wh, info in WAREHOUSES.items():
            custom_demand[wh] = st.number_input(
                wh, min_value=0, max_value=1000,
                value=info["demand"], step=10, key=f"dem_{wh}",
            )

    use_custom = st.checkbox("Özel parametreleri uygula", value=False)

    st.divider()
    run_btn = st.button("▶ Optimizasyonu Çalıştır", type="primary", use_container_width=True)
    run_all = st.button("📊 Tüm Senaryoları Karşılaştır", use_container_width=True)

    st.divider()
    st.caption("Çözüm yöntemi: Simplex LP (PuLP / CBC)")
    st.caption("© 2026 — IE303 Benzeri Proje")


# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------
if "result"       not in st.session_state: st.session_state.result       = None
if "scenario_run" not in st.session_state: st.session_state.scenario_run = None
if "supply_used"  not in st.session_state: st.session_state.supply_used  = None
if "demand_used"  not in st.session_state: st.session_state.demand_used  = None
if "cost_used"    not in st.session_state: st.session_state.cost_used    = None
if "all_results"  not in st.session_state: st.session_state.all_results  = None


# ---------------------------------------------------------------------------
# RUN OPTIMIZATION
# ---------------------------------------------------------------------------
def run_optimization(scen_name, use_cust):
    with st.spinner("Solver çalışıyor..."):
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

if run_all:
    all_res = {}
    with st.spinner("Tüm senaryolar çözülüyor..."):
        for sname in SCENARIOS:
            sup, dem, cst = get_scenario_data(sname)
            all_res[sname] = solve(sup, dem, cst)
    st.session_state.all_results = all_res
    # Also run selected scenario so result panel is populated
    run_optimization(scenario, use_custom)


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown("# 🚛 Türkiye Lojistik Karar Destek Sistemi")
st.markdown(
    "Üretim merkezlerinden depolara **minimum maliyetli** dağıtım planını "
    "hesapla · Senaryo analizi · Harita görselleştirme"
)
st.divider()

# ---------------------------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------------------------
res = st.session_state.result

c1, c2, c3, c4, c5 = st.columns(5)
total_supply = sum(SOURCES[s]["capacity"] for s in SOURCES)
total_demand_base = sum(WAREHOUSES[w]["demand"] for w in WAREHOUSES)

with c1:
    cost_val = f"₺{res['total_cost']:,.0f}" if res else "—"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Minimum Maliyet</div>
        <div class="kpi-value">{cost_val}</div>
        <div class="kpi-sub">{'Optimal ✓' if res else 'Henüz çözülmedi'}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    scen_label = st.session_state.scenario_run or "—"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Aktif Senaryo</div>
        <div class="kpi-value" style="font-size:1.1rem">{scen_label}</div>
        <div class="kpi-sub">&nbsp;</div>
    </div>""", unsafe_allow_html=True)

with c3:
    routes_n = len(res["shipments"]) if res else "—"
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Aktif Rota</div>
        <div class="kpi-value">{routes_n}</div>
        <div class="kpi-sub">15 olası rotadan</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Toplam Arz</div>
        <div class="kpi-value">{total_supply:,}</div>
        <div class="kpi-sub">birim kapasite</div>
    </div>""", unsafe_allow_html=True)

with c5:
    dem_used = sum(st.session_state.demand_used.values()) if st.session_state.demand_used else total_demand_base
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Toplam Talep</div>
        <div class="kpi-value">{dem_used:,}</div>
        <div class="kpi-sub">birim</div>
    </div>""", unsafe_allow_html=True)

st.markdown("")

# ---------------------------------------------------------------------------
# TABS
# ---------------------------------------------------------------------------
tab_map, tab_plan, tab_cost, tab_scenario, tab_model = st.tabs([
    "🗺️ Harita", "📦 Optimal Plan", "💰 Maliyet Analizi",
    "📊 Senaryo Karşılaştırması", "📐 Model Formülasyonu",
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
        st.caption("🔴 Üretim merkezi · 🟢 Depo · Hat kalınlığı = sevkiyat hacmi")
    else:
        # Default map without routes
        default_map = build_map({}, {s: SOURCES[s]["capacity"] for s in SOURCES},
                                 {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES})
        st_folium(default_map, width="100%", height=540)
        st.info("Optimizasyonu çalıştır → rotalar haritada görünür.")

# ── TAB 2: OPTIMAL PLAN ─────────────────────────────────────────────────────
with tab_plan:
    if res and res["status"] == "Optimal":
        sup   = st.session_state.supply_used
        dem   = st.session_state.demand_used
        cost  = st.session_state.cost_used
        ships = res["shipments"]

        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.markdown('<div class="section-header">Optimal Sevkiyat Planı</div>',
                        unsafe_allow_html=True)

            whs = list(WAREHOUSES.keys())
            rows = []
            for src in SOURCES:
                row = {"Kaynak": src}
                row_total = 0
                for wh in whs:
                    v = ships.get((src, wh), 0)
                    row[wh] = int(v) if v > 0 else "—"
                    row_total += v
                row["Toplam Sevk"] = int(row_total)
                row["Kapasite"]    = sup[src]
                row["Boşta"]       = int(sup[src] - row_total)
                rows.append(row)

            df_plan = pd.DataFrame(rows).set_index("Kaynak")

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
            st.markdown("**Talep karşılama:**")
            df_dem = pd.DataFrame([
                {"": "Talep"} | dem_row,
                {"": "Karşılanan"} | met_row,
            ]).set_index("")
            st.dataframe(df_dem, use_container_width=True, height=100)

        with col_r:
            st.markdown('<div class="section-header">Akış Diyagramı</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(build_sankey(ships), use_container_width=True)

        st.divider()
        st.markdown('<div class="section-header">Rota Detayları</div>',
                    unsafe_allow_html=True)

        detail_rows = []
        for (s, w), units in sorted(ships.items(), key=lambda x: -x[1]):
            unit_c  = cost[s][w]
            total_c = round(unit_c * units, 0)
            detail_rows.append({
                "Kaynak": s, "Depo": w,
                "Sevkiyat (birim)": int(units),
                "Birim Maliyet (₺)": f"₺{unit_c:,.2f}",
                "Toplam Maliyet (₺)": f"₺{total_c:,.0f}",
            })
        st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)

        st.success(f"**Toplam Minimum Maliyet: ₺{res['total_cost']:,.2f}**")

    else:
        st.info("Sol panelden bir senaryo seçip **Optimizasyonu Çalıştır** butonuna bas.")

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
        st.markdown('<div class="section-header">Tüm Rotalar — Birim Maliyet Tablosu (₺/birim)</div>',
                    unsafe_allow_html=True)
        whs = list(WAREHOUSES.keys())
        df_cost = pd.DataFrame(
            {src: {wh: f"₺{cost[src][wh]:,.0f}" for wh in whs} for src in SOURCES}
        ).T
        st.dataframe(df_cost, use_container_width=True)
    else:
        st.info("Önce optimizasyonu çalıştır.")

# ── TAB 4: SCENARIO COMPARISON ──────────────────────────────────────────────
with tab_scenario:
    if st.session_state.all_results:
        all_res = st.session_state.all_results
        st.plotly_chart(build_scenario_comparison(all_res), use_container_width=True)

        st.markdown('<div class="section-header">Senaryo Özet Tablosu</div>',
                    unsafe_allow_html=True)

        base = list(all_res.values())[0]["total_cost"]
        rows = []
        for sname, r in all_res.items():
            tc  = r["total_cost"]
            pct = round((tc - base) / base * 100, 1) if base else 0
            rows.append({
                "Senaryo": sname,
                "Toplam Maliyet": f"₺{tc:,.2f}",
                "Fark (₺)": f"{tc - base:+,.2f}",
                "Fark (%)": f"{pct:+.1f}%",
                "Aktif Rota": len(r["shipments"]),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Per-scenario shipment comparison
        st.markdown('<div class="section-header">Senaryo Bazında Sevkiyat Planları</div>',
                    unsafe_allow_html=True)
        for sname, r in all_res.items():
            with st.expander(f"📋 {sname}  —  ₺{r['total_cost']:,.0f}"):
                rows2 = [{"Rota": f"{s} → {w}", "Birim": int(v)}
                         for (s, w), v in r["shipments"].items()]
                st.dataframe(pd.DataFrame(rows2), hide_index=True, use_container_width=True)
    else:
        st.info("Sol panelde **Tüm Senaryoları Karşılaştır** butonuna bas.")

# ── TAB 5: MODEL FORMULATION ─────────────────────────────────────────────────
with tab_model:
    sup_disp = st.session_state.supply_used or {s: SOURCES[s]["capacity"] for s in SOURCES}
    dem_disp = st.session_state.demand_used or {w: WAREHOUSES[w]["demand"] for w in WAREHOUSES}

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown(formulation_text(sup_disp, dem_disp))

    with col_r:
        st.markdown('<div class="section-header">Arz & Talep</div>', unsafe_allow_html=True)

        df_sup = pd.DataFrame([
            {"Üretim Merkezi": s, "Kapasite (birim)": v}
            for s, v in sup_disp.items()
        ])
        df_sup.loc[len(df_sup)] = ["**TOPLAM**", sum(sup_disp.values())]
        st.dataframe(df_sup, hide_index=True, use_container_width=True)

        st.markdown("")
        df_dem = pd.DataFrame([
            {"Depo": w, "Talep (birim)": v}
            for w, v in dem_disp.items()
        ])
        df_dem.loc[len(df_dem)] = ["**TOPLAM**", sum(dem_disp.values())]
        st.dataframe(df_dem, hide_index=True, use_container_width=True)

    if res and res["status"] == "Optimal":
        st.divider()
        st.markdown('<div class="section-header">Çözüm Özeti</div>', unsafe_allow_html=True)
        slack_df = pd.DataFrame([
            {"Kaynak": s, "Boşta Kapasite": int(v)}
            for s, v in res["slack"].items()
        ])
        st.dataframe(slack_df, hide_index=True, use_container_width=True)
