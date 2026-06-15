"""
Visualization — Folium map + Plotly charts.
"""

from __future__ import annotations

import folium
import plotly.graph_objects as go
from folium.plugins import AntPath

from data import SOURCES, WAREHOUSES

# ---------------------------------------------------------------------------
# COLOUR PALETTE
# ---------------------------------------------------------------------------
SOURCE_COLOR    = "#E74C3C"   # red
WAREHOUSE_COLOR = "#2ECC71"   # green
ROUTE_COLORS    = [
    "#3498DB", "#9B59B6", "#F39C12",
    "#1ABC9C", "#E67E22",
]


# ---------------------------------------------------------------------------
# MAP
# ---------------------------------------------------------------------------
def build_map(shipments: dict, supply: dict, demand: dict) -> folium.Map:
    """
    Returns a Folium map centred on Turkey with:
      - Factory markers (red) for supply nodes
      - Warehouse markers (green) for demand nodes
      - Animated route lines sized by shipment volume
    """
    m = folium.Map(
        location=[39.0, 35.0],
        zoom_start=6,
        tiles="CartoDB positron",
    )

    max_ship = max(shipments.values()) if shipments else 1

    # Draw routes
    for idx, ((src, wh), units) in enumerate(shipments.items()):
        src_lat, src_lon = SOURCES[src]["lat"], SOURCES[src]["lon"]
        wh_lat,  wh_lon  = WAREHOUSES[wh]["lat"], WAREHOUSES[wh]["lon"]
        weight  = 2 + int(10 * units / max_ship)
        color   = ROUTE_COLORS[idx % len(ROUTE_COLORS)]

        AntPath(
            locations=[[src_lat, src_lon], [wh_lat, wh_lon]],
            color=color,
            weight=weight,
            opacity=0.85,
            tooltip=f"{src} → {wh}: {int(units)} units",
            delay=800,
        ).add_to(m)

    # Supply node markers
    for name, info in SOURCES.items():
        cap   = supply.get(name, info["capacity"])
        used  = sum(v for (s, _), v in shipments.items() if s == name)
        slack = cap - used
        folium.Marker(
            location=[info["lat"], info["lon"]],
            tooltip=f"🏭 {name}",
            popup=folium.Popup(
                f"<b>{name}</b><br>Capacity: {cap} units<br>"
                f"Shipped: {int(used)} units<br>Slack: {int(slack)} units",
                max_width=220,
            ),
            icon=folium.Icon(color="red", icon="industry", prefix="fa"),
        ).add_to(m)

    # Warehouse markers
    for name, info in WAREHOUSES.items():
        dem  = demand.get(name, info["demand"])
        recv = sum(v for (_, w), v in shipments.items() if w == name)
        folium.Marker(
            location=[info["lat"], info["lon"]],
            tooltip=f"🏬 {name}",
            popup=folium.Popup(
                f"<b>{name}</b><br>Demand: {dem} units<br>"
                f"Received: {int(recv)} units",
                max_width=200,
            ),
            icon=folium.Icon(color="green", icon="warehouse", prefix="fa"),
        ).add_to(m)

    return m


# ---------------------------------------------------------------------------
# SANKEY DIAGRAM
# ---------------------------------------------------------------------------
def build_sankey(shipments: dict) -> go.Figure:
    """Flow diagram: sources → warehouses."""
    sources    = list(SOURCES.keys())
    warehouses = list(WAREHOUSES.keys())
    nodes      = sources + warehouses

    node_colors = (
        [SOURCE_COLOR] * len(sources) +
        [WAREHOUSE_COLOR] * len(warehouses)
    )

    src_idx, tgt_idx, values, labels = [], [], [], []
    for (s, w), v in shipments.items():
        src_idx.append(nodes.index(s))
        tgt_idx.append(nodes.index(w))
        values.append(v)
        labels.append(f"{int(v)} units")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20, thickness=22,
            line=dict(color="white", width=0.5),
            label=nodes,
            color=node_colors,
            hovertemplate="%{label}<extra></extra>",
        ),
        link=dict(
            source=src_idx,
            target=tgt_idx,
            value=values,
            customdata=labels,
            hovertemplate="%{source.label} → %{target.label}: %{customdata}<extra></extra>",
            color="rgba(52, 152, 219, 0.4)",
        ),
    ))

    fig.update_layout(
        title=dict(text="Material Flow — Production Centre → Warehouse", font_size=15),
        font=dict(size=13),
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="#0e1117",
        font_color="white",
    )
    return fig


# ---------------------------------------------------------------------------
# COST BREAKDOWN BAR
# ---------------------------------------------------------------------------
def build_cost_breakdown(shipments: dict, cost: dict) -> go.Figure:
    """Horizontal bar chart: cost per active route."""
    routes, costs = [], []
    for (s, w), units in sorted(shipments.items(), key=lambda x: -x[1]):
        routes.append(f"{s} → {w}")
        costs.append(round(cost[s][w] * units, 0))

    colors = [ROUTE_COLORS[i % len(ROUTE_COLORS)] for i in range(len(routes))]

    fig = go.Figure(go.Bar(
        x=costs,
        y=routes,
        orientation="h",
        marker_color=colors,
        text=[f"₺{c:,.0f}" for c in costs],
        textposition="outside",
        hovertemplate="%{y}: ₺%{x:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Total Cost per Active Route (TL)", font_size=15),
        xaxis_title="TL",
        height=max(300, len(routes) * 48),
        margin=dict(l=10, r=80, t=50, b=30),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font_color="white",
        xaxis=dict(gridcolor="#333"),
        yaxis=dict(autorange="reversed"),
    )
    return fig


# ---------------------------------------------------------------------------
# SCENARIO COMPARISON BAR
# ---------------------------------------------------------------------------
def build_scenario_comparison(results: dict) -> go.Figure:
    """Grouped bar: total cost + % change per scenario."""
    names  = list(results.keys())
    costs  = [results[n]["total_cost"] for n in names]
    base   = costs[0] if costs else 1

    pct_changes = [round((c - base) / base * 100, 1) for c in costs]
    bar_colors  = [
        "#2ECC71" if c == min(costs) else "#E74C3C" if c == max(costs) else "#3498DB"
        for c in costs
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Total Cost",
        x=names,
        y=costs,
        marker_color=bar_colors,
        text=[f"₺{c:,.0f}" for c in costs],
        textposition="outside",
        hovertemplate="%{x}<br>₺%{y:,.0f}<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        name="Change (%)",
        x=names,
        y=pct_changes,
        mode="lines+markers+text",
        text=[f"{p:+.1f}%" for p in pct_changes],
        textposition="top center",
        yaxis="y2",
        line=dict(color="#F39C12", width=2, dash="dot"),
        marker=dict(size=9, color="#F39C12"),
    ))

    fig.update_layout(
        title=dict(text="Scenario Comparison", font_size=15),
        yaxis=dict(title="Total Cost (TL)", gridcolor="#333"),
        yaxis2=dict(title="Change vs Base (%)", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(l=10, r=10, t=70, b=30),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font_color="white",
        xaxis=dict(gridcolor="#333"),
    )
    return fig


# ---------------------------------------------------------------------------
# COST MATRIX HEATMAP
# ---------------------------------------------------------------------------
def build_cost_heatmap(cost: dict) -> go.Figure:
    sources    = list(SOURCES.keys())
    warehouses = list(WAREHOUSES.keys())
    z = [[cost[s][w] for w in warehouses] for s in sources]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=warehouses,
        y=sources,
        colorscale="RdYlGn_r",
        text=[[f"₺{cost[s][w]:,.0f}" for w in warehouses] for s in sources],
        texttemplate="%{text}",
        hovertemplate="%{y} → %{x}: ₺%{z:,.0f}/unit<extra></extra>",
        colorbar=dict(title="TL/unit"),
    ))

    fig.update_layout(
        title=dict(text="Unit Transport Cost Matrix (TL/unit)", font_size=15),
        height=320,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="#0e1117",
        font_color="white",
    )
    return fig
