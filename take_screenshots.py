"""
Automated screenshot capture for IEEE report figures.
Runs against the local Streamlit app on port 8502.
"""

import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:8502"
OUT  = "/Users/bahadirkarakus/Desktop/turkey_logistics"

TABS = [
    "🗺️ Map",
    "📦 Optimal Plan",
    "💰 Cost Analysis",
    "📊 Scenario Comparison",
    "🎲 Monte Carlo",
    "🔍 Sensitivity Analysis",
    "🎯 Multi-Objective",
]

async def click_tab(page, label):
    await page.get_by_role("tab", name=label).click()
    await page.wait_for_timeout(1800)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(viewport={"width": 1400, "height": 860})
        page    = await ctx.new_page()

        print("Loading app...")
        await page.goto(BASE, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # ── fig_interface: full dashboard before solving ─────────────────────
        await page.screenshot(path=f"{OUT}/fig_interface.png", full_page=False)
        print("fig_interface.png ✓")

        # ── Click Run Optimisation ───────────────────────────────────────────
        run_btn = page.get_by_role("button", name="▶ Run Optimisation")
        await run_btn.click()
        await page.wait_for_timeout(4000)   # wait for solve + render

        # ── fig_map ──────────────────────────────────────────────────────────
        await click_tab(page, "🗺️ Map")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{OUT}/fig_map.png", full_page=False)
        print("fig_map.png ✓")

        # ── fig_sankey ───────────────────────────────────────────────────────
        await click_tab(page, "📦 Optimal Plan")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/fig_sankey.png", full_page=False)
        print("fig_sankey.png ✓")

        # ── fig_cost (cost analysis) ─────────────────────────────────────────
        await click_tab(page, "💰 Cost Analysis")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/fig_cost.png", full_page=False)
        print("fig_cost.png ✓")

        # ── Save result, then switch to Summer Season, save again ────────────
        save_btn = page.get_by_role("button", name="💾 Save Result")
        await save_btn.click()
        await page.wait_for_timeout(800)

        # Change to Summer Season via Streamlit custom combobox
        sel = page.get_by_role("combobox")
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Summer Season").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)
        await save_btn.click()
        await page.wait_for_timeout(600)

        # ── Compare saved → fig_scenario ─────────────────────────────────────
        compare_btn = page.get_by_role("button", name="📊 Compare Saved")
        await compare_btn.click()
        await page.wait_for_timeout(1500)
        await click_tab(page, "📊 Scenario Comparison")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{OUT}/fig_scenario.png", full_page=False)
        print("fig_scenario.png ✓")

        # Back to Normal Season for remaining analytics
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Normal Season").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)

        # ── fig_sensitivity ──────────────────────────────────────────────────
        await click_tab(page, "🔍 Sensitivity Analysis")
        sens_btn = page.get_by_role("button", name="🔍 Run Sensitivity Analysis")
        await sens_btn.click()
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{OUT}/fig_sensitivity.png", full_page=False)
        print("fig_sensitivity.png ✓")

        # ── fig_montecarlo ───────────────────────────────────────────────────
        await click_tab(page, "🎲 Monte Carlo")
        mc_btn = page.get_by_role("button", name="🎲 Run Simulation")
        await mc_btn.click()
        await page.wait_for_timeout(15000)   # 300 iterations
        await page.screenshot(path=f"{OUT}/fig_montecarlo.png", full_page=False)
        print("fig_montecarlo.png ✓")

        # ── fig_pareto ───────────────────────────────────────────────────────
        await click_tab(page, "🎯 Multi-Objective")
        pareto_btn = page.get_by_role("button", name="🎯 Compute Pareto")
        await pareto_btn.click()
        await page.wait_for_timeout(5000)
        await page.screenshot(path=f"{OUT}/fig_pareto.png", full_page=False)
        print("fig_pareto.png ✓")

        await browser.close()
        print("\nAll screenshots saved.")


asyncio.run(main())
