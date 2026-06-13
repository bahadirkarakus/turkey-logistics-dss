"""
Second pass: scenario comparison + sensitivity + monte carlo + pareto.
Assumes app is already running on port 8502.
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

        run_btn  = page.get_by_role("button", name="▶ Run Optimisation")
        save_btn = page.get_by_role("button", name="💾 Save Result")
        sel      = page.get_by_role("combobox")

        # Solve & save Normal Season
        await run_btn.click()
        await page.wait_for_timeout(4000)
        await save_btn.click()
        await page.wait_for_timeout(800)

        # Switch to Summer Season, solve & save
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Summer Season").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)
        await save_btn.click()
        await page.wait_for_timeout(600)

        # Switch to Fuel Increase, solve & save
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Fuel Increase (+20%)").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)
        await save_btn.click()
        await page.wait_for_timeout(600)

        # Compare → fig_scenario
        compare_btn = page.get_by_role("button", name="📊 Compare Saved")
        await compare_btn.click()
        await page.wait_for_timeout(1500)
        await click_tab(page, "📊 Scenario Comparison")
        await page.screenshot(path=f"{OUT}/fig_scenario.png", full_page=False)
        print("fig_scenario.png ✓")

        # Back to Normal Season for analytics
        await sel.click()
        await page.wait_for_timeout(600)
        await page.get_by_role("option", name="Normal Season").click()
        await page.wait_for_timeout(600)
        await run_btn.click()
        await page.wait_for_timeout(4000)

        # fig_sensitivity
        await click_tab(page, "🔍 Sensitivity Analysis")
        sens_btn = page.get_by_role("button", name="🔍 Run Sensitivity Analysis")
        await sens_btn.click()
        await page.wait_for_timeout(3000)
        await page.screenshot(path=f"{OUT}/fig_sensitivity.png", full_page=False)
        print("fig_sensitivity.png ✓")

        # fig_montecarlo
        await click_tab(page, "🎲 Monte Carlo")
        mc_btn = page.get_by_role("button", name="🎲 Run Simulation")
        await mc_btn.click()
        await page.wait_for_timeout(18000)
        await page.screenshot(path=f"{OUT}/fig_montecarlo.png", full_page=False)
        print("fig_montecarlo.png ✓")

        # fig_pareto
        await click_tab(page, "🎯 Multi-Objective")
        pareto_btn = page.get_by_role("button", name="🎯 Compute Pareto")
        await pareto_btn.click()
        await page.wait_for_timeout(6000)
        await page.screenshot(path=f"{OUT}/fig_pareto.png", full_page=False)
        print("fig_pareto.png ✓")

        await browser.close()
        print("\nAll remaining screenshots saved.")


asyncio.run(main())
