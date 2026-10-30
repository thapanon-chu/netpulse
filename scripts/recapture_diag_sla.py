import asyncio
import os
from playwright.async_api import async_playwright

ASSETS_DIR = r"C:\Users\NussyEiEi\Desktop\code\Try\Network_rec\assets"
out_path = os.path.join(ASSETS_DIR, "screen_diagnostics_sla.png")

async def capture_diag():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        print("Navigating to http://localhost:8501...")
        await page.goto("http://localhost:8501", wait_until="networkidle")
        await page.wait_for_timeout(2500)

        print("Switching to Diagnostics & SLA...")
        tab_locator = page.get_by_text("Diagnostics & SLA", exact=False).first
        await tab_locator.click()
        await page.wait_for_timeout(2500)

        print("Selecting 6 Hours scope to reveal ISP Ookla benchmarks...")
        pill_6h = page.get_by_text("6 Hours", exact=True).first
        await pill_6h.click()
        await page.wait_for_timeout(4000)

        loader = page.locator("#netpulse-global-loader")
        if await loader.count() > 0:
            try:
                await loader.wait_for(state="detached", timeout=5000)
            except Exception:
                pass

        await page.screenshot(path=out_path)
        print(f"Successfully captured Diagnostics & SLA with ISP benchmarks to {out_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_diag())
