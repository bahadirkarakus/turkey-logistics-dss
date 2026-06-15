"""Global CSS for the dashboard."""

import streamlit as st

_CSS = """
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
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
