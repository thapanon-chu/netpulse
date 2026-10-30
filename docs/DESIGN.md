# NetPulse Design System & Visual Specification

## 1. Product Truth & Surface Mode
* **Brand Identity:** **NetPulse** (Subtitle: *Usage Tracker*)
* **Surface Mode:** Operate (High-Precision Network Telemetry & Predictive Analytics)
* **Design Philosophy:** Faithful implementation of the four reference mockups (`ui_1.png` – `ui_4.png`). A unified, dark, high-density telemetry console with zero visual bloat, no generic SaaS clutter, and verified 1:1 layout parity.

---

## 2. Spatial Hierarchy & 2-Column Architecture
* **Layout:** Full-width viewport (`max-width: 100%`) split into:
  * **Left Rail (`col_rail`, width ratio ~1.18):**
    * **Brand Header:** Deep royal blue icon tile (`#1D7BF6`, rounded 10px) with crisp white waveform SVG, bold white "NetPulse" (18px) and dim "Usage Tracker" (12px).
    * **Vertical Segmented Navigation (`st.radio`):**
      1. `Live Telemetry` (pulse waveform icon)
      2. `Process Attribution` (horizontal bars icon)
      3. `Diagnostics & SLA` (shield/hexagon icon)
      4. `Capacity & Trends` (analytics bar trend icon)
      * *Active Indicator:* Cyan `#00D2FF` left edge pill, navy card tint (`#111A2E`), border `rgba(0, 210, 255, 0.22)`.
    * **Bottom System Status Card:** Elevated tile (`#0C1422`, border `rgba(16, 185, 129, 0.22)`), static emerald dot (`#10B981`) with "Telemetry Active", "Sampling every 1s", and "Uptime 99.98%".
  * **Main Workspace (`col_main`, width ratio ~4.42):**
    * **View Header:** Clean `h1` Title (28px bold white) and descriptive Subtitle (`#8492A6`).
    * **Contextual Time Scope Bar:** Capsule pills (`1 Hour`, `6 Hours`, `24 Hours`, `7 Days`, `30 Days`, `Calendar`) + `↻ Refresh` capsule button + Powder-Blue pill `Export CSV` (`#7DD3FC` with `#0F172A` bold text).

---

## 3. Color Tokens & Semantic Accents
* **Canvas Void:** `#090D16`
* **Sidebar Rail:** `#0C101D` (border: `rgba(255, 255, 255, 0.06)`)
* **Elevated Cards:** `#0E1424` (border: `rgba(255, 255, 255, 0.06)`)
* **Pills & Buttons:** `#101728` (border: `rgba(255, 255, 255, 0.08)`)
* **Typography:**
  * Primary (`#F8FAFC`): Headers, primary numerals
  * Secondary (`#94A3B8`): Subtitles, labels, axis ticks
  * Muted / Dim (`#8E9CB2`): Footers, descriptions (compliant with WCAG AA > 4.5:1 contrast)
* **Semantic Spectrum:**
  * **Inbound / Download:** Cyan `#00D2FF` / Sky `#38BDF8`
  * **Outbound / Upload:** Rose `#F43F5E` / Light Rose `#FDA4AF`
  * **Peak / Anomaly / Forecast:** Amber `#FACC15` / `#F59E0B`
  * **Model / Ratio / Projection:** Purple `#818CF8` / Indigo `#6366F1`
  * **Active / Normal / SLA:** Emerald `#10B981` / `#34D399`

---

## 4. Typography & Tabular Figures
* **Primary Sans:** `system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` for ultra-crisp OS-level rendering.
* **Telemetry Numerals:** `'JetBrains Mono', monospace` with tabular numbers (`font-variant-numeric: tabular-nums`) to prevent horizontal layout shift during 1-second live data ticks.

---

## 5. Domain Views (1:1 Parity with Reference Screenshots)

### View 1: Live Telemetry (`ui_1.png`)
* **4 Metric Cards:**
  1. `INBOUND`: `↓ DOWNLOAD` cyan badge, live cyan throughput, window volume in MB.
  2. `OUTBOUND`: `↑ UPLOAD` rose badge, live rose throughput, window volume in MB.
  3. `PEAK`: Amber peak rate with peak time indicator.
  4. `DL / UL RATIO`: Purple ratio with volume balance label.
* **Throughput Over Time:**
  * Inbound (Cyan) and Outbound (Rose) line graphs with subtle area fills.
  * Capsule traffic toggle (`Both`, `Download`, `Upload`) and `! ML Anomalies` toggle.
  * Isolation Forest anomaly target markers (`🟡 Anomaly`) dynamically pegged to peak spikes.

### View 2: Process Attribution (`ui_2.png`)
* **2-Column Layout:**
  * **Left Card (62%):** `Bandwidth timeline` with `Rate/s` vs `Cumulative` toggle pill and dual-line Plotly chart.
  * **Right Card (38%):** `Top network consumers` list of top executables (e.g. `speedtest.exe`, `opera.exe`, `ChatGPT Classic.exe`, etc.) with usage volume and custom colored horizontal progress bars.

### View 3: Diagnostics & SLA (`ui_3.png`)
* **4 Metric Cards:** `AVG LATENCY` (green), `P95` (cyan), `PEAK` (rose), `PACKET LOSS` (amber).
* **Connection Latency:** Amber latency curve with dashed green `SLA threshold 100 ms` horizontal reference line.
* **ISP Capacity Benchmarks:** Grouped bar chart comparing Download (cyan) and Upload (rose) Ookla tests with exact Mbps labels centered directly on top of each bar.

### View 4: Capacity & Trends (`ui_4.png`)
* **4 Metric Cards:** `MONTH-TO-DATE` (cyan actual), `PROJECTED END` (purple Ridge), `DAILY BURN` (rose 14d mean), `BEST WINDOW` (green quiet hours).
* **7-Day Predictive Forecast:**
  * Daily actual history bars (cyan).
  * Vertical dashed divider line with `FORECAST →` annotation.
  * Dotted amber forecast line with markers and shaded 80% confidence interval band.
  * View switcher pills: `Forecast`, `Diurnal cycle` (24h profile), and `Anomaly log`.
