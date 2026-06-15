"""
Automated screenshot capture for IEEE report and README figures.
Runs against the local Streamlit app on port 8502.
"""

import asyncio

from playwright.async_api import async_playwright

BASE = "http://localhost:8502"
OUT  = "/Users/bahadirkarakus/Desktop/turkey_logistics"


async def click_tab(page, label):
    await page.get_by_role("tab", name=label).click()
    await page.wait_for_timeout(2000)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(viewport={"width": 1400, "height": 860})
        page    = await ctx.new_page()

        print("Loading app...")
        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── fig_interface: dashboard before solving ───────────────────────────
        await page.screenshot(path=f"{OUT}/fig_interface.png")
        print("fig_interface.png ✓")

        # ── Run Optimization ─────────────────────────────────────────────────
        run_btn = page.get_by_role("button", name="▶ Run Optimization")
        await run_btn.click()
        await page.wait_for_timeout(4000)

        # ── fig_map ───────────────────────────────────────────────────────────
        await click_tab(page, "🗺️ Map")
        await page.wait_for_timeout(2500)
        await page.screenshot(path=f"{OUT}/fig_map.png")
        print("fig_map.png ✓")

        # ── fig_sankey ────────────────────────────────────────────────────────
        await click_tab(page, "📦 Optimal Plan")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{OUT}/fig_sankey.png")
        print("fig_sankey.png ✓")

        # ── fig_cost ──────────────────────────────────────────────────────────
        await click_tab(page, "💰 Cost Analysis")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{OUT}/fig_cost.png")
        print("fig_cost.png ✓")

        # ── Scenario comparison ───────────────────────────────────────────────
        save_btn = page.get_by_role("button", name="💾 Save Result")
        await save_btn.click()
        await page.wait_for_timeout(800)

        sel = page.get_by_role("combobox").first
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Summer Season").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)
        await save_btn.click()
        await page.wait_for_timeout(600)

        compare_btn = page.get_by_role("button", name="📊 Compare Saved")
        await compare_btn.click()
        await page.wait_for_timeout(1500)
        await click_tab(page, "📊 Scenario Comparison")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/fig_scenario.png")
        print("fig_scenario.png ✓")

        # Back to Normal Season
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Normal Season").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)

        # ── fig_sensitivity ───────────────────────────────────────────────────
        await click_tab(page, "🔍 Sensitivity Analysis")
        await page.get_by_role("button", name="🔍 Run Sensitivity Analysis").click()
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{OUT}/fig_sensitivity.png")
        print("fig_sensitivity.png ✓")

        # ── fig_montecarlo ────────────────────────────────────────────────────
        await click_tab(page, "🎲 Monte Carlo")
        await page.get_by_role("button", name="🎲 Run Simulation").click()
        await page.wait_for_timeout(15000)
        await page.screenshot(path=f"{OUT}/fig_montecarlo.png")
        print("fig_montecarlo.png ✓")

        # ── fig_pareto ────────────────────────────────────────────────────────
        await click_tab(page, "🎯 Multi-Objective")
        await page.get_by_role("button", name="🎯 Compute Pareto").click()
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{OUT}/fig_pareto.png")
        print("fig_pareto.png ✓")

        # ── fig_multiperiod ───────────────────────────────────────────────────
        await click_tab(page, "📅 Multi-Period")
        await page.wait_for_timeout(1000)
        mp_sel = page.get_by_role("combobox").nth(1)
        await mp_sel.click()
        await page.wait_for_timeout(500)
        await page.get_by_role("option", name="Summer Season").click()
        await page.wait_for_timeout(500)
        await page.get_by_role("button", name="▶ Solve Multi-Period").click()
        await page.wait_for_timeout(4000)
        await page.screenshot(path=f"{OUT}/fig_multiperiod.png")
        print("fig_multiperiod.png ✓")

        # ── fig_forecast ──────────────────────────────────────────────────────
        await page.get_by_text("📈 Demand Forecast").click()
        await page.wait_for_timeout(800)
        await page.get_by_role("button", name="📊 Generate Forecast").click()
        await page.wait_for_timeout(2500)
        await page.screenshot(path=f"{OUT}/fig_forecast.png")
        print("fig_forecast.png ✓")

        # ── fig_disruption ────────────────────────────────────────────────────
        await click_tab(page, "⚠️ Disruption")
        await page.wait_for_timeout(1000)
        # Disable Bursa
        await page.get_by_label("Bursa").check()
        await page.wait_for_timeout(500)
        await page.get_by_role("button", name="⚠️ Simulate Disruption").click()
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{OUT}/fig_disruption.png")
        print("fig_disruption.png ✓")

        # ── fig_location ──────────────────────────────────────────────────────
        await click_tab(page, "📍 Location")
        await page.wait_for_timeout(1000)
        await page.get_by_role("button", name="📍 Find Optimal Locations").click()
        await page.wait_for_timeout(8000)
        await page.screenshot(path=f"{OUT}/fig_location.png")
        print("fig_location.png ✓")

        await browser.close()
        print("\nAll screenshots saved.")


asyncio.run(main())
