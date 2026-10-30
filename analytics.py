import sqlite3
import pandas as pd
import numpy as np
import datetime
import os
from sklearn.linear_model import Ridge, HuberRegressor
from sklearn.ensemble import IsolationForest

def get_daily_telemetry(db_file):
    """
    Retrieves daily aggregated network telemetry from SQLite.
    Returns DataFrame with [day, date, dl_gb, ul_gb, total_gb].
    """
    try:
        conn = sqlite3.connect(db_file, timeout=10)
        daily_df = pd.read_sql_query('''
            SELECT strftime('%Y-%m-%d', timestamp) as day,
                   SUM(recv_speed_bps) / (1024.0 * 1024 * 1024) as dl_gb,
                   SUM(sent_speed_bps) / (1024.0 * 1024 * 1024) as ul_gb
            FROM bandwidth
            GROUP BY day
            ORDER BY day ASC
        ''', conn)
        conn.close()
    except Exception:
        return pd.DataFrame()

    if daily_df.empty:
        return pd.DataFrame()

    daily_df['dl_gb'] = daily_df['dl_gb'].fillna(0.0)
    daily_df['ul_gb'] = daily_df['ul_gb'].fillna(0.0)
    daily_df['total_gb'] = daily_df['dl_gb'] + daily_df['ul_gb']
    daily_df['date'] = pd.to_datetime(daily_df['day'])
    return daily_df


def compute_forecast(daily_df, days_ahead=7, db_file=None):
    """
    Fits a robust Huber regression model with outlier dampening, autoregressive lags, 
    and exponential recency weighting. Connects to SQLite feedback loop to evaluate
    and auto-calibrate against past actuals.
    """
    if daily_df.empty or len(daily_df) < 3:
        return None

    # Use up to past 60 days
    df = daily_df.tail(60).copy().reset_index(drop=True)
    if 'total_gb' not in df.columns:
        df['total_gb'] = df['dl_gb'] + df['ul_gb']
    if 'date' not in df.columns:
        df['date'] = pd.to_datetime(df['day'])

    # 1. Rolling median capping for robust baseline (absorbs 100+ GB spikes)
    roll_med = df['total_gb'].rolling(14, min_periods=3).median().bfill()
    df['clean_gb'] = np.minimum(df['total_gb'], roll_med * 2.2)

    # 2. Feature engineering: Lags, rollings, weekend indicator, cyclical day-of-week
    df['lag_1'] = df['clean_gb'].shift(1)
    df['roll_3'] = df['clean_gb'].shift(1).rolling(3, min_periods=1).mean()
    df['roll_7'] = df['clean_gb'].shift(1).rolling(7, min_periods=3).mean()
    df['roll_14'] = df['clean_gb'].shift(1).rolling(14, min_periods=5).median()
    df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6]).astype(float)
    df['dow_sin'] = np.sin(2 * np.pi * df['date'].dt.dayofweek / 7.0)
    df['dow_cos'] = np.cos(2 * np.pi * df['date'].dt.dayofweek / 7.0)
    df['day_idx'] = np.arange(len(df))

    train = df.dropna().copy().reset_index(drop=True)
    features = ['day_idx', 'dow_sin', 'dow_cos', 'is_weekend', 'lag_1', 'roll_3', 'roll_7', 'roll_14']

    if len(train) >= 7:
        X = train[features]
        y = train['clean_gb']

        # Exponential recency weighting: recent days get up to 3x weight
        n_train = len(train)
        weights = np.exp(np.linspace(-1.1, 0, n_train))

        model = HuberRegressor(epsilon=1.35, alpha=1.5, max_iter=400)
        model.fit(X, y, sample_weight=weights)

        preds = model.predict(X)
        resids = np.abs(train['total_gb'] - preds)
        robust_std = float(np.median(resids) * 1.4826)
    else:
        model = None
        robust_std = 5.0

    # 3. Autoregressive recursive projection for upcoming days
    future_preds = []
    curr_lag_1 = df['clean_gb'].iloc[-1]
    series_buffer = list(df['clean_gb'].values)
    last_date = df['date'].iloc[-1]
    future_dates = [last_date + datetime.timedelta(days=i) for i in range(1, days_ahead + 1)]

    for step in range(1, days_ahead + 1):
        f_date = last_date + datetime.timedelta(days=step)
        f_day_idx = len(df) + step - 1
        f_dow = f_date.dayofweek
        f_is_weekend = 1.0 if f_dow in [5, 6] else 0.0
        f_sin = np.sin(2 * np.pi * f_dow / 7.0)
        f_cos = np.cos(2 * np.pi * f_dow / 7.0)
        f_lag_1 = curr_lag_1
        f_roll3 = np.mean(series_buffer[-3:])
        f_roll7 = np.mean(series_buffer[-7:])
        f_roll14 = np.median(series_buffer[-14:])

        if model is not None:
            row_feat = pd.DataFrame([{
                'day_idx': f_day_idx,
                'dow_sin': f_sin,
                'dow_cos': f_cos,
                'is_weekend': f_is_weekend,
                'lag_1': f_lag_1,
                'roll_3': f_roll3,
                'roll_7': f_roll7,
                'roll_14': f_roll14
            }])
            pred_val = float(np.clip(model.predict(row_feat)[0], 1.0, None))
        else:
            pred_val = float(np.mean(series_buffer[-7:]))

        future_preds.append(pred_val)
        curr_lag_1 = pred_val
        series_buffer.append(pred_val)

    # 4. Feedback loop: Update and calibrate against past forecasts in SQLite
    eval_accuracy = None
    eval_mae = None
    rolling_bias = 0.0

    if db_file and os.path.exists(db_file):
        try:
            conn = sqlite3.connect(db_file, timeout=10)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS forecast_history (
                    target_date TEXT PRIMARY KEY,
                    predicted_gb REAL,
                    predicted_at DATETIME,
                    actual_gb REAL,
                    error_gb REAL,
                    accuracy_pct REAL
                )
            ''')
            conn.commit()

            # Update historical actuals for past dates that have concluded
            today_str = datetime.date.today().strftime('%Y-%m-%d')
            past_unfilled = pd.read_sql_query(
                "SELECT target_date, predicted_gb FROM forecast_history WHERE actual_gb IS NULL AND target_date < ?",
                conn, params=(today_str,)
            )

            for _, row in past_unfilled.iterrows():
                t_date = row['target_date']
                p_gb = float(row['predicted_gb'])
                match = daily_df[daily_df['day'] == t_date]
                if not match.empty:
                    act_gb = float(match['total_gb'].iloc[0])
                    err_gb = act_gb - p_gb
                    smape = 200.0 * abs(err_gb) / max(abs(act_gb) + abs(p_gb), 5.0)
                    acc = max(0.0, 100.0 - smape)
                    c.execute('''
                        UPDATE forecast_history 
                        SET actual_gb = ?, error_gb = ?, accuracy_pct = ? 
                        WHERE target_date = ?
                    ''', (round(act_gb, 1), round(err_gb, 1), round(acc, 1), t_date))
            conn.commit()

            # Read recent evaluated performance (last 7 completed evaluations)
            recent_eval = pd.read_sql_query(
                "SELECT error_gb, accuracy_pct FROM forecast_history WHERE actual_gb IS NOT NULL ORDER BY target_date DESC LIMIT 7",
                conn
            )
            if not recent_eval.empty:
                eval_accuracy = float(recent_eval['accuracy_pct'].mean())
                eval_mae = float(recent_eval['error_gb'].abs().mean())
                rolling_bias = float(recent_eval['error_gb'].mean())

            # Self-calibrating bias adjustment: if model had slight persistent bias, damp it
            if abs(rolling_bias) >= 1.0:
                adj_factor = np.clip(rolling_bias * 0.4, -5.0, 5.0)
                future_preds = [max(1.0, p + adj_factor) for p in future_preds]

            # Save the new 7-day predictions for future tracking
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for f_date, p_val in zip(future_dates, future_preds):
                f_date_str = f_date.strftime('%Y-%m-%d')
                c.execute('''
                    INSERT INTO forecast_history (target_date, predicted_gb, predicted_at, actual_gb, error_gb, accuracy_pct)
                    VALUES (?, ?, ?, NULL, NULL, NULL)
                    ON CONFLICT(target_date) DO UPDATE SET 
                        predicted_gb = excluded.predicted_gb,
                        predicted_at = excluded.predicted_at
                    WHERE forecast_history.actual_gb IS NULL
                ''', (f_date_str, round(p_val, 1), now_str))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # 5. Build forecast_df
    lower_bound = np.clip(np.array(future_preds) - (1.28 * robust_std), 0, None)
    upper_bound = np.array(future_preds) + (1.28 * robust_std)

    forecast_df = pd.DataFrame({
        'date': future_dates,
        'day': [d.strftime('%Y-%m-%d') for d in future_dates],
        'predicted_gb': future_preds,
        'lower_bound': lower_bound,
        'upper_bound': upper_bound
    })

    # Month-to-date and End-of-Month Projection
    today = datetime.date.today()
    current_year_month = today.strftime('%Y-%m')
    current_month_days = daily_df[daily_df['day'].str.startswith(current_year_month)]
    mtd_actual_gb = float(current_month_days['total_gb'].sum()) if not current_month_days.empty else 0.0

    if today.month == 12:
        next_month_first = datetime.date(today.year + 1, 1, 1)
    else:
        next_month_first = datetime.date(today.year, today.month + 1, 1)
    last_day_of_month = (next_month_first - datetime.timedelta(days=1)).day
    remaining_days = max(0, last_day_of_month - today.day)

    # Robust daily burn rate (14-day median/mean of clean traffic)
    recent_14 = df['clean_gb'].tail(14)
    daily_burn_rate = float(recent_14.mean()) if not recent_14.empty else float(df['clean_gb'].mean())

    projected_month_end_gb = mtd_actual_gb + (daily_burn_rate * remaining_days)

    return {
        'forecast_df': forecast_df,
        'mtd_actual_gb': mtd_actual_gb,
        'projected_month_end_gb': projected_month_end_gb,
        'daily_burn_rate': daily_burn_rate,
        'residual_std': robust_std,
        'remaining_days': remaining_days,
        'history_df': df,
        'eval_accuracy': eval_accuracy,
        'eval_mae': eval_mae,
        'rolling_bias': rolling_bias
    }


def compute_diurnal_profile(db_file, lookback_days=14):
    """
    Calculates 24-hour diurnal usage profiles (hourly averages across recent days).
    Identifies Quiet Hours (ideal download window) and Peak Congestion Hours.
    """
    try:
        conn = sqlite3.connect(db_file, timeout=10)
        hourly_df = pd.read_sql_query(f'''
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                   AVG(recv_speed_bps) / 1024.0 as avg_dl_kb,
                   AVG(sent_speed_bps) / 1024.0 as avg_ul_kb,
                   COUNT(*) as samples
            FROM bandwidth
            WHERE timestamp >= datetime('now', '-{lookback_days} days')
            GROUP BY hour
            ORDER BY hour ASC
        ''', conn)
        conn.close()
    except Exception:
        return None

    if hourly_df.empty or len(hourly_df) < 12:
        return None

    hourly_df['total_avg_kb'] = hourly_df['avg_dl_kb'] + hourly_df['avg_ul_kb']

    # Find optimal 4-hour window (lowest rolling average traffic)
    # Wrap around 24 hours
    extended = list(hourly_df['total_avg_kb']) + list(hourly_df['total_avg_kb'][:3])
    window_avgs = [sum(extended[i:i+4]) / 4.0 for i in range(24)]
    
    quiet_start_hour = int(np.argmin(window_avgs))
    quiet_end_hour = (quiet_start_hour + 4) % 24

    peak_start_hour = int(np.argmax(window_avgs))
    peak_end_hour = (peak_start_hour + 4) % 24

    return {
        'hourly_df': hourly_df,
        'optimal_window_str': f"{quiet_start_hour:02d}:00 - {quiet_end_hour:02d}:00",
        'peak_window_str': f"{peak_start_hour:02d}:00 - {peak_end_hour:02d}:00",
        'quiet_start_hour': quiet_start_hour,
        'peak_start_hour': peak_start_hour
    }


def detect_traffic_anomalies(bandwidth_df, contamination=0.015):
    """
    Executes unsupervised multivariate anomaly detection via Isolation Forest.
    Returns anomaly dataframe and high-severity outliers table.
    """
    if bandwidth_df.empty or len(bandwidth_df) < 50:
        return None

    # Sample if dataset is excessively large for instant sub-second reactivity
    if len(bandwidth_df) > 12000:
        sample_df = bandwidth_df.iloc[::max(1, len(bandwidth_df) // 10000)].copy()
    else:
        sample_df = bandwidth_df.copy()

    cols = ['Download (KB/s)', 'Upload (KB/s)'] if 'Download (KB/s)' in sample_df.columns and 'Upload (KB/s)' in sample_df.columns else ['recv_speed_bps', 'sent_speed_bps']
    X = sample_df[cols].values
    clf = IsolationForest(contamination=contamination, random_state=42, n_estimators=60)
    sample_df['anomaly'] = clf.fit_predict(X)
    sample_df['anomaly_score'] = clf.decision_function(X)

    anomalies_only = sample_df[sample_df['anomaly'] == -1].sort_values(by='anomaly_score', ascending=True)

    return {
        'anomalies_count': len(anomalies_only),
        'anomalies_df': anomalies_only,
        'scored_df': sample_df
    }
