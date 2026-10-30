# NetPulse — Network Usage Tracker & Diagnostics

NetPulse is a high-performance Windows desktop network telemetry and analytics suite designed for low overhead, 60 FPS responsiveness, and deep network intelligence.

---

## 🏗️ System Architecture

NetPulse operates on a three-tier decoupled architecture:

```
┌────────────────────────────────────────────────────────┐
│                   Windows System                       │
├──────────────────────────┬─────────────────────────────┤
│ 1. Telemetry Daemon      │ tracker.py                  │
│    (Background Service)  │ Samples socket I/O & ping   │
│                          │ Writes to SQLite (WAL mode) │
├──────────────────────────┼─────────────────────────────┤
│ 2. Interactive Dashboard │ app.py (Streamlit + Plotly) │
│    (Web GUI / Port 8501) │ Real-time KPIs, charts, ML  │
│                          │ Proactive RAM pre-fetching  │
├──────────────────────────┼─────────────────────────────┤
│ 3. System Tray Launcher  │ tray_app.py (pystray)       │
│    (Taskbar Notification)│ Quick launch / background   │
│                          │ Custom circular pulse logo  │
└──────────────────────────┴─────────────────────────────┘
```

---

## ⚡ Refresh & Real-Time Streaming Architecture

NetPulse uses **Granular Streamlit Fragments** (`@st.fragment`) to separate high-frequency live metric updates from heavy historical chart rendering.

### 1. Active 1-Second Reactive KPIs (Enabled)
* **Location:** `app.py` $\rightarrow$ `render_live_telemetry_kpis()`
* **Decorator:** `@st.fragment(run_every="1s")`
* **Behavior:** Automatically queries the single latest second of throughput metrics from SQLite (`LIMIT 1`) every 1,000 ms.
* **Scope:** Re-renders *only* the top 4 metric cards (`INBOUND`, `OUTBOUND`, `PEAK`, `DL/UL RATIO`).
* **Advantage:** Zero page reload, zero DOM flashing, negligible CPU footprint (< 0.1%).

### 2. Throughput Chart Auto-Refresh (Configurable / Disabled by Default)
* **Location:** `app.py` $\rightarrow$ `render_throughput_chart_panel()`
* **Decorator:** `@st.fragment(run_every=LIVE_CHART_AUTO_REFRESH_INTERVAL)`
* **Current Status:** **Disabled by default** (`LIVE_CHART_AUTO_REFRESH_INTERVAL = None`).
  * The chart operates in **Interactive Snapshot Mode**: data is loaded when entering the view or when clicking the `↻ Refresh` button.
  * **Why Disabled by Default:**
    1. **Stable Tooltip Hover:** When exploring anomalies or specific timestamps, periodic re-rendering would reset active Plotly hover tooltips and zoom boxes.
    2. **Zero Client CPU Waste:** Rendering dense time-series graphs (1,800+ data points) is deferred until user-initiated actions.

#### How to Enable Chart Live Auto-Refresh:
To turn on live streaming for the Throughput chart, open `app.py` (around line 1435) and set:

```python
# Change from:
LIVE_CHART_AUTO_REFRESH_INTERVAL = None

# To your desired interval (recommended 5s or 10s):
LIVE_CHART_AUTO_REFRESH_INTERVAL = "5s"  # or "10s"
```

* When enabled, the chart will automatically pull the latest telemetry window and stream forward smoothly every 5 or 10 seconds without reloading any other part of the dashboard.

---

## 🧠 Background Data & Cache Management

### Predictive Pre-fetching Daemon (`_prefetch_worker`)
* Runs in an independent background thread (`NetPulsePrefetcher`).
* Once the active view is displayed, the prefetcher quietly warms up:
  - Adjacent time scopes (`1 Hour`, `6 Hours`, `24 Hours`, `7 Days`, `30 Days`)
  - Predictive Ridge Regression models and diurnal patterns for *Capacity & Trends*
* Results are cached directly in RAM (`@st.cache_data`).
* **Tab Switching Performance:** Navigating between tabs takes **< 380 ms** with zero database read lag.

### Motion Loading Overlay Threshold
* Configured in CSS (`#netpulse-global-loader`):
  ```css
  transition-delay: 0.6s;
  ```
* Standard navigation (< 400 ms) completes seamlessly without displaying the black loading card. The loading overlay only fades in if a query genuinely exceeds 600 ms (e.g., massive date range calculations).

---

## 💾 Persistent System Settings (`user_settings.json` & Settings Modal)

Global user interface and engine preferences are managed via the **⚙️ Settings modal** (located on the left navigation rail under the divider line) and permanently persisted using atomic file writes:

* **Waveform Smoothing Window (`smoothing_sec`):**
  * Options: `1` (Raw 1-second bursts), `5` (Task Manager style smooth wave — Recommended), `10` (Grafana ultra-smooth).
  * Automatically calculates rolling means on-the-fly during rendering without altering the underlying 1s SQLite database records.
* **Highlight Anomalies (`highlight_anomalies`):**
  * Toggles machine learning Isolation Forest markers on the Throughput chart (`True` or `False`).
* **Live Chart Auto-Refresh (`chart_auto_refresh`):**
  * Options: `"None"` (Manual snapshot), `"5s"`, `"10s"`.
  * Dynamically configures the `@st.fragment(run_every=...)` interval of the Throughput panel.
* **Connection Latency SLA Threshold (`latency_sla_ms`):**
  * Controls the target SLA limit line (default `100` ms) on the Diagnostics & SLA Connection Latency chart.
* **Packet Loss Warning Level (`packet_loss_warn_pct`):**
  * Quality warning threshold percentage (default `1.0`%).
* **Time Scope (`active_time_scope`):**
  * Preserved across all 4 tab transitions during the active browser session.

---

## 📐 Chart Ground Rule: Inactive Downtime Gap Handling

* **Problem Solved:** When the PC is turned off, asleep, or the tracker daemon is stopped, standard Plotly time-series lines naively bridge the last active point (e.g., 02:00) directly to the next reboot point (e.g., 12:30) with an artificial diagonal line across hours of downtime.
* **Universal Solution (`sanitize_timeseries_gaps` in `app.py`):**
  - **Adaptive Gap Detection:** Computes median point intervals and triggers gap breaks whenever `\Delta t > \max(120\text{s}, \text{median\_step} \times 3.5)`.
  - **Throughput & Bandwidth Rates (`fill='tozeroy'`):** Inserts a 0.0 drop at `prev_time + 1s` to ground the filled polygon, followed by `NaN` sentinels to break the line, and smoothly rises from 0.0 at `next_time - 1s` when tracking resumes.
  - **Connection Latency (`ping_ms`):** Pure `NaN` boundary insertion with `connectgaps=False`. The latency line abruptly stops at the exact moment of daemon pause without misreporting false 0ms latency.
  - **Reboot Resilience (Cumulative Bandwidth):** Cumulative metrics use monotonic non-negative delta accumulation (`clip(lower=0).cumsum()`), preventing inverted charts when Windows resets socket counters on reboot.
* **Scope:** Strictly enforced across **Live Telemetry**, **Process Attribution**, and **Diagnostics & SLA**.

---

## 🚀 Running & Managing the Application

### Starting Services Manually:
```powershell
# 1. Start Telemetry Tracker Daemon
python tracker.py

# 2. Start Web Dashboard
streamlit run app.py --server.headless true

# 3. Start System Tray Icon
pythonw tray_app.py
```

### Windows Startup Script:
NetPulse is automatically configured to launch silently on Windows boot via:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\NetworkTracker.vbs`

---

## 📊 Database Schema (`network_data.db`)
Operates under SQLite `WAL` (Write-Ahead Logging) mode with `PRAGMA synchronous=NORMAL`:
* `bandwidth`: 1-second interval download/upload rates and cumulative bytes.
* `program_usage`: Per-process socket bandwidth attribution.
* `ping`: Continuous ICMP echo latency and packet loss logs.
* `speedtest`: Periodic ISP Ookla capacity benchmark benchmarks (XX:00 and XX:30).
