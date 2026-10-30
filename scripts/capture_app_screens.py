import asyncio
import os
from playwright.async_api import async_playwright

ASSETS_DIR = r"C:\Users\NussyEiEi\Desktop\code\Try\Network_rec\assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

TABS = [
    ("Live Telemetry", "screen_live_telemetry.png"),
    ("Process Attribution", "screen_process_attribution.png"),
    ("Diagnostics & SLA", "screen_diagnostics_sla.png"),
    ("Capacity & Trends", "screen_capacity_trends.png"),
]

async def capture_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        print("Navigating to http://localhost:8501...")
        await page.goto("http://localhost:8501", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        for tab_name, filename in TABS:
            print(f"Switching to tab: {tab_name}...")
            # Click the tab label
            tab_locator = page.get_by_text(tab_name, exact=False).first
            await tab_locator.click()
            # Wait for data & charts to load
            await page.wait_for_timeout(3500)
            
            # Wait if loader is visible
            loader = page.locator("#netpulse-global-loader")
            if await loader.count() > 0:
                try:
                    await loader.wait_for(state="detached", timeout=5000)
                except Exception:
                    pass

            out_path = os.path.join(ASSETS_DIR, filename)
            await page.screenshot(path=out_path)
            print(f"Captured {tab_name} -> {out_path}")

        await browser.close()
        print("All screen captures completed successfully!")

if __name__ == "__main__":
    asyncio.run(capture_all())
