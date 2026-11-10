"""Energy workstream: SYNTHETIC telemetry, day-ahead forecasting and anomaly detection.

Everything in this module is synthetic. It shows the method from the report
(Appendix A1); it says nothing about any real facility.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression

SEED = 42
START = "2026-06-01"
DAYS = 120
WARMUP_DAYS = 7          # needed for the 7-day lag features
TRAIN_DAYS = 90          # days 1-90 train, days 91-120 validation (chronological)
CAL_DAYS = 14            # last training days used to size the 90% band
MAPE_TARGET = 15.0       # report: provisional target, <= 15% MAPE
RECALL_TARGET = 90.0     # report: detect >= 90% of predefined test anomalies
FLATLINE_HOURS = 3       # identical power readings for this many hours = stuck meter
MODEL_VERSION = "gc-energy-1.0"

TYPES = [
    "Power spike at normal IT load",
    "Zone temperature drift",
    "Humidity excursion",
    "Power meter flatline",
]

FEATURES = ["hour", "dow", "is_weekend", "outside_temp_fc_c",
            "lag_24h", "lag_168h", "mean_same_hour_7d"]

DATA_DICTIONARY = pd.DataFrame([
    ("timestamp", "Hour start (local time)", "-"),
    ("outside_temp_c", "Outside air temperature", "°C"),
    ("outside_temp_fc_c", "Day-ahead weather forecast of outside temperature (actual + noise)", "°C"),
    ("it_load_kw", "IT equipment load", "kW"),
    ("facility_power_kw", "Total facility power: IT + cooling + other overhead", "kW"),
    ("zone_temp_c", "Server-zone air temperature", "°C"),
    ("humidity_pct", "Server-zone relative humidity", "%"),
    ("cooling_status", "Cooling plant status flag", "Normal / Degraded"),
    ("is_anomaly", "Injected test anomaly (ground-truth label)", "True / False"),
    ("anomaly_type", "Type of injected anomaly", "text"),
], columns=["Field", "Meaning", "Unit"])


def _ar1(rng, n, phi, sd):
    e = rng.normal(0, sd, n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + e[i]
    return out


def make_telemetry(days: int = DAYS, seed: int = SEED, n_events: int = 40):
    """Hourly synthetic telemetry with daily/weekly patterns and injected anomalies."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(START, periods=days * 24, freq="h")
    n = len(idx)
    hour = idx.hour.to_numpy()
    dow = idx.dayofweek.to_numpy()
    day = np.arange(n) / 24

    outside = (26 + 4 * np.sin(2 * np.pi * (hour - 9) / 24)
               + 1.5 * np.sin(2 * np.pi * day / 45) + _ar1(rng, n, 0.97, 0.35))
    business = np.exp(-((hour - 14) / 4.5) ** 2) * np.where(dow >= 5, 0.5, 1.0)
    it = 300 + 0.3 * day + 70 * business + _ar1(rng, n, 0.8, 4)
    cooling = it * (0.28 + 0.012 * (outside - 24)) + rng.normal(0, 5, n)
    other = 0.06 * it + 15 + rng.normal(0, 2, n)

    df = pd.DataFrame({
        "timestamp": idx,
        "outside_temp_c": outside,
        "outside_temp_fc_c": outside + rng.normal(0, 0.8, n),
        "it_load_kw": it,
        "facility_power_kw": it + cooling + other,
        "zone_temp_c": 23 + 0.02 * (it - 330) + 0.08 * (outside - 26) + rng.normal(0, 0.25, n),
        "humidity_pct": 48 + 5 * np.sin(2 * np.pi * (hour - 4) / 24)
                        - 0.6 * (outside - 26) + rng.normal(0, 1.2, n),
        "cooling_status": "Normal",
        "is_anomaly": False,
        "anomaly_type": "",
    })
    df, events = _inject(df, rng, n_events)
    return df, events


def _inject(df, rng, n_events):
    n = len(df)
    starts = []
    for s in rng.permutation(np.arange(WARMUP_DAYS * 24 + 24, n - 12)):
        if all(abs(s - o) > 48 for o in starts):
            starts.append(int(s))
        if len(starts) == n_events:
            break
    starts.sort()
    kinds = rng.permutation(np.arange(n_events) % len(TYPES))

    col = {c: df.columns.get_loc(c) for c in df.columns}
    rows = []
    for i, (s, k) in enumerate(zip(starts, kinds), start=1):
        kind = TYPES[k]
        if k == 0:
            dur, mag = int(rng.integers(2, 6)), rng.uniform(0.03, 0.15)
            df.iloc[s:s + dur, col["facility_power_kw"]] *= 1 + mag
            df.iloc[s:s + dur, col["cooling_status"]] = "Degraded"
            detail = f"+{mag:.0%} facility power"
        elif k == 1:
            dur, rise = int(rng.integers(3, 7)), rng.uniform(0.8, 3.0)
            df.iloc[s:s + dur, col["zone_temp_c"]] += np.linspace(rise / dur, rise, dur)
            detail = f"+{rise:.1f} °C ramp"
        elif k == 2:
            dur = int(rng.integers(2, 5))
            jump = rng.uniform(4, 14) * rng.choice([-1, 1])
            df.iloc[s:s + dur, col["humidity_pct"]] += jump
            detail = f"{jump:+.0f} pts RH"
        else:
            dur = int(rng.integers(4, 9))
            df.iloc[s:s + dur, col["facility_power_kw"]] = df.iloc[s - 1, col["facility_power_kw"]]
            detail = "reading stuck at last value"
        df.iloc[s:s + dur, col["is_anomaly"]] = True
        df.iloc[s:s + dur, col["anomaly_type"]] = kind
        rows.append({
            "event_id": f"E{i:02d}", "type": kind,
            "start": df.timestamp.iloc[s], "end": df.timestamp.iloc[s + dur - 1],
            "hours": dur, "detail": detail,
        })
    return df, pd.DataFrame(rows)


# ---------------------------------------------------------------- forecasting

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    f = df.copy()
    f["hour"] = f.timestamp.dt.hour
    f["dow"] = f.timestamp.dt.dayofweek
    f["is_weekend"] = (f.dow >= 5).astype(int)
    p = f.facility_power_kw
    f["lag_24h"] = p.shift(24)
    f["lag_168h"] = p.shift(168)
    f["mean_same_hour_7d"] = sum(p.shift(24 * k) for k in range(1, 8)) / 7
    day = (f.timestamp - f.timestamp.iloc[0]).dt.days
    f["split"] = np.where(day < WARMUP_DAYS, "warm-up",
                          np.where(day < TRAIN_DAYS, "train", "validation"))
    return f


def _metrics(y, yhat):
    err = np.abs(y - yhat)
    return {"MAE (kW)": float(err.mean()), "MAPE (%)": float((err / np.abs(y)).mean() * 100)}


def run_forecast(df: pd.DataFrame) -> dict:
    f = add_features(df)
    train = f[(f.split == "train") & ~f.is_anomaly]
    val = f[f.split == "validation"].copy()

    model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=SEED)
    model.fit(train[FEATURES], train.facility_power_kw)
    # 90% band by split conformal: a twin model fitted on the earlier part of the
    # training window is scored on its last CAL_DAYS days; the 90th percentile of
    # those absolute errors gives the band half-width.
    day = (train.timestamp - f.timestamp.iloc[0]).dt.days
    fit, cal = train[day < TRAIN_DAYS - CAL_DAYS], train[day >= TRAIN_DAYS - CAL_DAYS]
    twin = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, random_state=SEED)
    twin.fit(fit[FEATURES], fit.facility_power_kw)
    half_width = float(np.quantile(np.abs(cal.facility_power_kw - twin.predict(cal[FEATURES])), 0.9))

    hist_avg = train.groupby(["dow", "hour"]).facility_power_kw.mean().rename("hist_avg")
    val = val.join(hist_avg, on=["dow", "hour"])
    val["persistence"] = val.lag_24h
    val["ml"] = model.predict(val[FEATURES])
    val["ml_lo"] = val.ml - half_width
    val["ml_hi"] = val.ml + half_width

    scored = val[~val.is_anomaly]   # anomalies are judged separately
    y = scored.facility_power_kw
    table = pd.DataFrame([
        {"Method": "Historical average (same weekday-hour, training period)", **_metrics(y, scored.hist_avg)},
        {"Method": "Persistence (same hour yesterday)", **_metrics(y, scored.persistence)},
        {"Method": "ML: gradient-boosted trees", **_metrics(y, scored.ml)},
    ])
    coverage = float(((y >= scored.ml_lo) & (y <= scored.ml_hi)).mean() * 100)

    daily = scored.assign(date=scored.timestamp.dt.date).groupby("date").apply(
        lambda d: pd.Series({
            "Historical average": (abs(d.facility_power_kw - d.hist_avg) / d.facility_power_kw).mean() * 100,
            "Persistence": (abs(d.facility_power_kw - d.persistence) / d.facility_power_kw).mean() * 100,
            "ML model": (abs(d.facility_power_kw - d.ml) / d.facility_power_kw).mean() * 100,
        }), include_groups=False).reset_index()

    return {
        "val": val, "table": table, "coverage": coverage, "half_width": half_width, "daily": daily,
        "n_train": len(train), "n_val_scored": len(scored),
        "train_window": (train.timestamp.min(), train.timestamp.max()),
        "val_window": (val.timestamp.min(), val.timestamp.max()),
    }


# ---------------------------------------------------------- anomaly detection

def _expected_X(d: pd.DataFrame) -> np.ndarray:
    h = d.timestamp.dt.hour.to_numpy()
    return np.column_stack([
        d.it_load_kw, d.outside_temp_c, d.it_load_kw * d.outside_temp_c,
        np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24),
    ])


def score_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Robust z-scores of residuals from simple 'expected value' models, plus a flatline rule."""
    f = add_features(df)
    train = f[(f.split == "train") & ~f.is_anomaly]
    out = f[["timestamp", "split", "is_anomaly", "anomaly_type",
             "facility_power_kw", "zone_temp_c", "humidity_pct", "it_load_kw"]].copy()
    for target, name in [("facility_power_kw", "z_power"),
                         ("zone_temp_c", "z_temp"),
                         ("humidity_pct", "z_humidity")]:
        reg = LinearRegression().fit(_expected_X(train), train[target])
        resid_train = train[target] - reg.predict(_expected_X(train))
        scale = 1.4826 * np.median(np.abs(resid_train - np.median(resid_train)))
        out["exp_" + target] = reg.predict(_expected_X(f))
        out[name] = (f[target] - out["exp_" + target]) / scale
    p = f.facility_power_kw
    run_id = (p != p.shift()).cumsum()
    out["flat_run"] = p.groupby(run_id).transform("size")
    return out


CHANNELS = {
    "z_power": ("Facility power vs IT load", "Facility team",
                "Check cooling plant and power meter against IT load"),
    "z_temp": ("Zone temperature", "Facility team",
               "Inspect zone airflow and cooling unit"),
    "z_humidity": ("Humidity", "Facility team",
                   "Check humidifier and humidity sensor calibration"),
    "flat": ("Power meter flatline", "IT infrastructure",
             "Check meter communication and data pipeline"),
}


def detect(scores: pd.DataFrame, k: float, events: pd.DataFrame, period: str) -> dict:
    s = scores.copy()
    zcols = ["z_power", "z_temp", "z_humidity"]
    s["flat"] = s.flat_run >= FLATLINE_HOURS
    s["flag"] = (s[zcols].abs() >= k).any(axis=1) | s.flat
    s["score"] = s[zcols].abs().max(axis=1)
    s = s[s.split == period].reset_index(drop=True)

    # group flagged hours into alerts (gaps of 1 hour are merged)
    alerts = []
    flagged = s.index[s.flag].tolist()
    groups = []
    for i in flagged:
        if groups and i - groups[-1][-1] <= 2:
            groups[-1].append(i)
        else:
            groups.append([i])
    for n, g in enumerate(groups, start=1):
        part = s.loc[g[0]:g[-1]]
        trig = [c for c in zcols if (part[c].abs() >= k).any()]
        if part.flat.any():
            trig.append("flat")
        main = max(trig, key=lambda c: 99 if c == "flat" else part[c].abs().max())
        peak = float(part.score.max())
        severity = ("High" if part.flat.any() or peak >= 2 * k
                    else "Medium" if peak >= 1.5 * k else "Low")
        alerts.append({
            "alert_id": f"A{n:03d}",
            "start": part.timestamp.iloc[0], "end": part.timestamp.iloc[-1],
            "hours": len(part), "source_metric": CHANNELS[main][0],
            "triggers": ", ".join(CHANNELS[c][0] for c in trig),
            "peak_score": round(peak, 1), "severity": severity,
            "recommendation": CHANNELS[main][2], "owner": CHANNELS[main][1],
            "review_status": "Pending review",
        })
    alerts = pd.DataFrame(alerts, columns=[
        "alert_id", "start", "end", "hours", "source_metric", "triggers", "peak_score",
        "severity", "recommendation", "owner", "review_status"])

    lo, hi = s.timestamp.min(), s.timestamp.max()
    ev = events[(events.start >= lo) & (events.start <= hi)].copy()
    flagged_times = set(s.timestamp[s.flag])

    def hit(e):
        rng_ = pd.date_range(e.start, e.end, freq="h")
        return any(t in flagged_times for t in rng_)

    ev["detected"] = ev.apply(hit, axis=1) if len(ev) else []

    def matches(a):
        m = events[(events.start <= a.end) & (events.end >= a.start)]
        return ", ".join(m.event_id) if len(m) else "none (false alarm)"

    if len(alerts):
        alerts["matches_injected_event"] = alerts.apply(matches, axis=1)
    else:
        alerts["matches_injected_event"] = []
    tp_alerts = int((alerts.matches_injected_event != "none (false alarm)").sum())
    n_ev = len(ev)
    detected = int(ev.detected.sum()) if n_ev else 0
    return {
        "series": s, "alerts": alerts, "events": ev,
        "n_events": n_ev, "detected": detected, "missed": n_ev - detected,
        "false_alerts": len(alerts) - tp_alerts, "n_alerts": len(alerts),
        "recall": detected / n_ev * 100 if n_ev else float("nan"),
        "precision": tp_alerts / len(alerts) * 100 if len(alerts) else float("nan"),
    }


def run_pipeline() -> dict:
    df, events = make_telemetry()
    return {
        "df": df, "events": events,
        "forecast": run_forecast(df),
        "scores": score_anomalies(df),
        "validated_at": datetime.now(timezone.utc),
    }
