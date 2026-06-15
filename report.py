"""
PDF Report Generator — fpdf2
"""

from __future__ import annotations

from datetime import datetime

from fpdf import FPDF

_TR = str.maketrans(
    "ğĞşŞİıöÖüÜçÇ",
    "gGsS" "Iioo" "UUcC"
)

def _s(text: str) -> str:
    """Sanitize text for latin-1 PDF output."""
    text = str(text).translate(_TR)
    text = text.replace("—", "-").replace("–", "-")  # em/en dash
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text


class _Report(FPDF):
    def cell(self, w=0, h=0, text="", *args, **kwargs):
        super().cell(w, h, _s(text), *args, **kwargs)

    def header(self):
        self.set_fill_color(15, 23, 42)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.cell(0, 11, "Turkey Logistics DSS - Optimization Report",
                  fill=True, align="C")
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8,
                  f"Page {self.page_no()}  |  "
                  f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
                  "Turkey Logistics DSS",
                  align="C")


def _section(pdf: _Report, title: str):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(0, 8, title, fill=True)
    pdf.ln(2)


def _kv(pdf: _Report, label: str, value: str):
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(65, 6, label)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, value)
    pdf.ln()


def generate_pdf(result: dict, supply: dict, demand: dict,
                 cost: dict, scenario_name: str,
                 saved_scenarios: dict | None = None,
                 mc_result: dict | None = None) -> bytes:
    """
    Generates a PDF report and returns it as bytes.
    """
    pdf = _Report(orientation="L", format="A4")
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    warehouses = list(demand.keys())
    sources    = list(supply.keys())

    # ── KPI Banner ──────────────────────────────────────────────────────────
    _section(pdf, "Summary")
    _kv(pdf, "Active Scenario:",   scenario_name)
    _kv(pdf, "Solution Status:",   result.get("status", "-"))
    _kv(pdf, "Min. Total Cost:",   f"TL {result['total_cost']:,.2f}")
    _kv(pdf, "Total Supply:",      f"{sum(supply.values()):,} units")
    _kv(pdf, "Total Demand:",      f"{sum(demand.values()):,} units")
    _kv(pdf, "Slack Capacity:",    f"{sum(supply.values()) - sum(demand.values()):,} units")
    _kv(pdf, "Active Routes:",     f"{len(result['shipments'])} / {len(sources)*len(warehouses)}")
    pdf.ln(4)

    # ── Optimal Shipment Plan ────────────────────────────────────────────────
    _section(pdf, "Optimal Shipment Plan (units)")

    COL_SRC  = 30
    COL_WH   = int((pdf.w - 2 * pdf.l_margin - COL_SRC - 22) / len(warehouses))
    COL_TOT  = 22

    # Header row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(COL_SRC, 7, "Source \\ Warehouse", border=1, fill=True, align="C")
    for wh in warehouses:
        pdf.cell(COL_WH, 7, wh[:8], border=1, fill=True, align="C")
    pdf.cell(COL_TOT, 7, "Total", border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    for src in sources:
        row_total = 0
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(COL_SRC, 6, src, border=1, fill=True)
        pdf.set_font("Helvetica", "", 8)
        for wh in warehouses:
            v = result["shipments"].get((src, wh), 0)
            row_total += v
            if v > 0:
                pdf.set_fill_color(187, 247, 208)
                txt = str(int(v))
            else:
                pdf.set_fill_color(255, 255, 255)
                txt = "—"
            pdf.cell(COL_WH, 6, txt, border=1, align="C", fill=True)
        pdf.cell(COL_TOT, 6, str(int(row_total)), border=1, align="C")
        pdf.ln()

    # Demand row
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(COL_SRC, 6, "Demand", border=1, fill=True)
    for wh in warehouses:
        pdf.cell(COL_WH, 6, str(demand[wh]), border=1, align="C", fill=True)
    pdf.cell(COL_TOT, 6, str(sum(demand.values())), border=1, align="C", fill=True)
    pdf.ln(6)

    # ── Cost Matrix ──────────────────────────────────────────────────────────
    _section(pdf, "Unit Transport Cost Matrix (TL/unit)")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(COL_SRC, 7, "Source \\ Warehouse", border=1, fill=True, align="C")
    for wh in warehouses:
        pdf.cell(COL_WH, 7, wh[:8], border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    for src in sources:
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(COL_SRC, 6, src, border=1, fill=True)
        for wh in warehouses:
            pdf.cell(COL_WH, 6, f"{cost[src][wh]:,.0f}", border=1, align="C")
        pdf.ln()
    pdf.ln(4)

    # ── Route Detail ─────────────────────────────────────────────────────────
    _section(pdf, "Route Details")

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    for hdr, w in [("Source", 38), ("Warehouse", 32), ("Shipment (units)", 36),
                   ("Unit Cost (TL)", 40), ("Total Cost (TL)", 44)]:
        pdf.cell(w, 7, hdr, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    sorted_ships = sorted(result["shipments"].items(), key=lambda x: -x[1])
    for idx, ((src, wh), units) in enumerate(sorted_ships):
        uc = cost[src][wh]
        tc = uc * units
        pdf.set_fill_color(248, 250, 252) if idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.cell(38, 6, src,  border=1, fill=True)
        pdf.cell(32, 6, wh,   border=1, fill=True)
        pdf.cell(36, 6, str(int(units)), border=1, align="C", fill=True)
        pdf.cell(40, 6, f"TL {uc:,.2f}", border=1, align="C", fill=True)
        pdf.cell(44, 6, f"TL {tc:,.0f}", border=1, align="C", fill=True)
        pdf.ln()
    pdf.ln(4)

    # ── Scenario Comparison ─────────────────────────────────────────────────
    if saved_scenarios and len(saved_scenarios) > 1:
        _section(pdf, "Scenario Comparison")
        base = list(saved_scenarios.values())[0]["total_cost"]

        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        for hdr, w in [("Scenario", 70), ("Total Cost (TL)", 50),
                       ("Delta (TL)", 40), ("Delta (%)", 35)]:
            pdf.cell(w, 7, hdr, border=1, fill=True, align="C")
        pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 8)
        for idx, (sname, sdata) in enumerate(saved_scenarios.items()):
            tc   = sdata["total_cost"]
            diff = tc - base
            pct  = diff / base * 100 if base else 0
            pdf.set_fill_color(248, 250, 252) if idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            pdf.cell(70, 6, sname,               border=1, fill=True)
            pdf.cell(50, 6, f"TL {tc:,.2f}",    border=1, align="C", fill=True)
            pdf.cell(40, 6, f"{diff:+,.0f}",     border=1, align="C", fill=True)
            pdf.cell(35, 6, f"{pct:+.1f}%",      border=1, align="C", fill=True)
            pdf.ln()
        pdf.ln(4)

    # ── Monte Carlo Summary ──────────────────────────────────────────────────
    if mc_result:
        _section(pdf, f"Monte Carlo Simulation Summary  ({mc_result['n_simulations']} iterations)")
        _kv(pdf, "Mean Cost:",          f"TL {mc_result['mean_cost']:,.2f}")
        _kv(pdf, "Std Dev:",            f"TL {mc_result['std_cost']:,.2f}")
        _kv(pdf, "5th Percentile:",     f"TL {mc_result['p5_cost']:,.2f}")
        _kv(pdf, "95th Percentile:",    f"TL {mc_result['p95_cost']:,.2f}")
        _kv(pdf, "Infeasible runs:",    str(mc_result["n_infeasible"]))

    return bytes(pdf.output())
