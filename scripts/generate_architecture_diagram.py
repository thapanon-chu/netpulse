import os
import asyncio
from playwright.async_api import async_playwright

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #090d16;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #f1f5f9;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 30px;
    width: 1200px;
    height: 520px;
  }
  .container {
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at 50% 0%, rgba(30, 41, 59, 0.5) 0%, rgba(15, 23, 42, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 32px;
    position: relative;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 16px;
  }
  .header-title {
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .header-badge {
    background: rgba(14, 165, 233, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(14, 165, 233, 0.3);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .header-meta {
    font-size: 12px;
    color: #94a3b8;
    font-family: 'JetBrains Mono', Consolas, monospace;
  }
  
  .diagram-flow {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0;
    position: relative;
  }

  .node-card {
    background: rgba(15, 23, 42, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 18px 20px;
    width: 250px;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
    transition: all 0.2s ease;
    backdrop-filter: blur(12px);
  }

  .card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }
  .tag {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 3px 8px;
    border-radius: 6px;
  }
  .tag-cyan { background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3); }
  .tag-purple { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
  .tag-emerald { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
  .tag-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

  .card-title {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 4px;
  }
  .card-file {
    font-family: 'JetBrains Mono', Consolas, monospace;
    font-size: 12px;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    display: inline-block;
    padding: 2px 6px;
    border-radius: 4px;
    margin-bottom: 8px;
  }
  .card-desc {
    font-size: 12px;
    line-height: 1.45;
    color: #94a3b8;
  }

  .arrow-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 60px;
    text-align: center;
  }
  .arrow-line {
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    position: relative;
    margin-bottom: 6px;
  }
  .arrow-line::after {
    content: '';
    position: absolute;
    right: 0;
    top: -4px;
    width: 0;
    height: 0;
    border-top: 5px solid transparent;
    border-bottom: 5px solid transparent;
    border-left: 7px solid #818cf8;
  }
  .arrow-label {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: #cbd5e1;
    white-space: nowrap;
    background: rgba(30, 41, 59, 0.9);
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .tray-node-container {
    position: absolute;
    right: 32px;
    top: 76px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .node-card-small {
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 10px 14px;
    width: 250px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }
  .tray-arrow {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: #94a3b8;
    margin-top: 4px;
  }

  .footer-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 14px;
    font-size: 12px;
    color: #64748b;
  }
  .footer-specs {
    display: flex;
    gap: 20px;
  }
  .spec-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .spec-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #10b981;
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-title">
      <span>NetPulse System Architecture</span>
      <span class="header-badge">Decoupled Three-Tier</span>
    </div>
    <div class="header-meta">Windows x64 Telemetry Engine · 60 FPS Target</div>
  </div>

  <div class="diagram-flow">
    <!-- Node 1: Ingestion -->
    <div class="node-card" style="border-top: 3px solid #06b6d4;">
      <div class="card-top">
        <span class="tag tag-cyan">Tier 1 · Ingestion</span>
      </div>
      <div class="card-title">Telemetry Daemon</div>
      <div class="card-file">tracker.py</div>
      <div class="card-desc">Continuous 1s socket I/O sampling, per-process network attribution, and ICMP echo latency probes.</div>
    </div>

    <!-- Arrow 1 to 2 -->
    <div class="arrow-connector">
      <div class="arrow-line"></div>
      <span class="arrow-label">1s WAL Inserts</span>
    </div>

    <!-- Node 2: Persistent Storage -->
    <div class="node-card" style="border-top: 3px solid #8b5cf6;">
      <div class="card-top">
        <span class="tag tag-purple">Storage Engine</span>
      </div>
      <div class="card-title">SQLite Database</div>
      <div class="card-file">network_data.db</div>
      <div class="card-desc">Write-Ahead Logging (WAL) with normalized schema. Zero shared state per installation.</div>
    </div>

    <!-- Arrow 2 to 3 -->
    <div class="arrow-connector">
      <div class="arrow-line"></div>
      <span class="arrow-label">Indexed Queries</span>
    </div>

    <!-- Node 3: Presentation -->
    <div class="node-card" style="border-top: 3px solid #10b981;">
      <div class="card-top">
        <span class="tag tag-emerald">Tier 2 · Presentation</span>
      </div>
      <div class="card-title">Interactive Dashboard</div>
      <div class="card-file">app.py (:8501)</div>
      <div class="card-desc">Streamlit fragments, Plotly waveforms, Isolation Forest ML anomaly markers, and proactive RAM pre-fetching.</div>
    </div>
  </div>

  <!-- Tray App Row -->
  <div style="display: flex; justify-content: flex-end; padding-right: 10px;">
    <div style="display: flex; align-items: center; gap: 12px; background: rgba(30, 41, 59, 0.4); border: 1px dashed rgba(255, 255, 255, 0.15); border-radius: 10px; padding: 10px 18px;">
      <div>
        <span class="tag tag-amber">Tier 3 · Background Control</span>
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #f59e0b; margin-left: 8px;">tray_app.py</span>
      </div>
      <div style="font-size: 12px; color: #94a3b8;">Windows Taskbar Tray · 1-Click Launch & Status Indicator</div>
    </div>
  </div>

  <div class="footer-bar">
    <div class="footer-specs">
      <div class="spec-item"><span class="spec-dot"></span> Thread Isolation: Daemon & UI run in independent processes</div>
      <div class="spec-item"><span class="spec-dot"></span> Crash Resilient: Uncorrupted WAL journals during power loss</div>
    </div>
    <div>NetPulse v2.4 Architecture</div>
  </div>
</div>
</body>
</html>
"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1200, "height": 520}, device_scale_factor=2)
        await page.set_content(HTML_CONTENT)
        await page.wait_for_timeout(500)
        out_path = r"C:\Users\NussyEiEi\Desktop\code\Try\Network_rec\assets\architecture.png"
        await page.screenshot(path=out_path, type="png")
        await browser.close()
        print(f"Generated architecture diagram at: {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
