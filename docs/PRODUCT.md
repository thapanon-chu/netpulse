# Product Context: Network Usage Tracker

## Purpose
A lightweight, background desktop application and dashboard that continuously monitors real-time system network telemetry, bandwidth utilization per process, connection latency via native Win32 ICMP, and automated scheduled ISP speed benchmarks.

## Target Audience
Engineers, gamers, network troubleshooters, and power users who need granular, persistent insights into why their network spikes, which local application consumes bandwidth, or when ISP latency degrades.

## Core Capabilities
1. **Real-Time Telemetry:** Live inbound & outbound throughput updating every second.
2. **Process-Level Attribution:** Exact bandwidth attribution per running executable via socket connections and OS I/O counters.
3. **Connection Latency Diagnostics:** Sub-second ICMP ping tracking with automatic disconnection gap detection.
4. **ISP Benchmark Automation:** Periodic Ookla Speedtest execution at XX:00 and XX:30.
5. **Flexible Scoping:** Relative time filters (1m to 30d) and custom calendar Date / Date-Range filters.
6. **Data Portability:** Clean CSV export capability for all four data domains.
7. **Predictive Intelligence & Data Science:**
   - **Time Series Capacity Forecasting:** 7-day projection using Ridge regression with day-of-week seasonality and confidence interval bands.
   - **Quota Burn Rate & Month-End Projections:** Estimates total monthly data footprint and daily consumption velocity.
   - **Diurnal Congestion Profiling:** Analyzes 24-hour cycles to identify optimal off-peak bulk transfer windows vs peak congestion hours.
   - **Unsupervised Anomaly Detection:** Multivariate outlier detection via `IsolationForest` across socket throughput and ping spikes.
