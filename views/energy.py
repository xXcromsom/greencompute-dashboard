import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from lib import cached, energy, ui

pipe = cached.energy_pipeline()
df, events, fc = pipe["df"], pipe["events"], pipe["forecast"]

ui.header(
    "Energy workstream",
    f"Forecast facility power a day ahead and flag unusual readings for human review. "
    f"{energy.DAYS} days of hourly synthetic telemetry with {len(events)} injected test anomalies, "
    f"split by date: first {energy.TRAIN_DAYS} days to train, last {energy.DAYS - energy.TRAIN_DAYS} held out",
    eyebrow="02 · Workstream A",
    tags=["synthetic"],
)

t_fc, t_an, t_tr, t_card = st.tabs(["Forecast", "Anomaly alerts", "Telemetry trends", "Model card"])

# ------------------------------------------------------------------ forecast
with t_fc:
    tbl = fc["table"].set_index("Method")
    ml, hist, pers = tbl.iloc[2], tbl.iloc[0], tbl.iloc[1]
    ui.stats([
        ui.stat("ML forecast MAPE", f"{ml['MAPE (%)']:.2f}%",
                ui.delta("meets" if ml["MAPE (%)"] <= energy.MAPE_TARGET else "misses",
                         f"the ≤{energy.MAPE_TARGET:.0f}% target",
                         "good" if ml["MAPE (%)"] <= energy.MAPE_TARGET else "bad"), accent=True),
        ui.stat("Historical average MAPE", f"{hist['MAPE (%)']:.2f}%", "Same weekday and hour, training mean"),
        ui.stat("Persistence MAPE", f"{pers['MAPE (%)']:.2f}%", "Same hour yesterday"),
        ui.stat("ML mean absolute error", f"{ml['MAE (kW)']:.1f} kW",
                ui.delta(f"{(ml['MAE (kW)'] / hist['MAE (kW)'] - 1) * 100:+.0f}%", "vs historical average", "good")),
    ])

    ui.section("Forecast vs observed", f"Facility power in kW. The 90% band is ±{fc['half_width']:.0f} kW and held "
               f"{fc['coverage']:.0f}% of held-out hours. Spikes outside it are mostly the injected anomalies",
               "synthetic")
    c1, c2 = st.columns([3, 1])
    days = c1.segmented_control("Window", ["7 days", "14 days", "30 days"], default="7 days",
                                label_visibility="collapsed")
    show_pers = c2.toggle("Show persistence", value=False)
    n_days = int((days or "7 days").split()[0])
    v = fc["val"]
    v = v[v.timestamp > v.timestamp.max() - pd.Timedelta(days=n_days)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.ml_hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.ml_lo, line=dict(width=0), fill="tonexty",
                             fillcolor=ui.ACCENT_FILL, name="90% band", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.hist_avg, name="Historical average",
                             line=dict(color=ui.GRAY_D, width=1.5, dash="dot"), hovertemplate="%{y:.0f} kW"))
    if show_pers:
        fig.add_trace(go.Scatter(x=v.timestamp, y=v.persistence, name="Persistence",
                                 line=dict(color=ui.GRAY, width=1.5, dash="dash"), hovertemplate="%{y:.0f} kW"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.facility_power_kw, name="Observed",
                             line=dict(color=ui.INK, width=1.5), hovertemplate="%{y:.0f} kW"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.ml, name="ML forecast",
                             line=dict(color=ui.ACCENT, width=2), hovertemplate="%{y:.0f} kW"))
    fig.update_yaxes(ticksuffix=" kW")
    ui.chart(fig, 400)

    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.section("Daily error vs simple baselines", "Mean absolute percentage error per held-out day")
        d = fc["daily"]
        fig2 = go.Figure()
        for name, color, dash in [("Historical average", ui.GRAY_D, "dot"), ("Persistence", ui.GRAY, "dash"),
                                  ("ML model", ui.ACCENT, None)]:
            fig2.add_trace(go.Scatter(x=d.date, y=d[name], name=name, mode="lines",
                                      line=dict(color=color, width=2 if dash is None else 1.5, dash=dash),
                                      hovertemplate="%{y:.1f}%"))
        fig2.update_yaxes(ticksuffix="%", rangemode="tozero")
        ui.chart(fig2, 280)
    with right:
        ui.section("Scores on held-out hours", f"{fc['n_val_scored']} hours, injected anomalies excluded")
        st.dataframe(fc["table"], hide_index=True, width="stretch", column_config={
            "Method": st.column_config.TextColumn(width="medium"),
            "MAE (kW)": st.column_config.NumberColumn(format="%.1f"),
            "MAPE (%)": st.column_config.NumberColumn(format="%.2f")})
        st.caption("Well inside the 15% target, but so is the persistence baseline. On synthetic data the "
                   "pattern is regular by construction, so the gap over baselines matters more than the level")

# ------------------------------------------------------------------ anomalies
with t_an:
    a, b = st.columns([2, 1], gap="large")
    k = a.slider("Alert threshold, robust z-score", 2.5, 10.0, 4.0, 0.5,
                 help="An hour is flagged when a reading is this many robust standard deviations from "
                      "its expected value. Lower means more alerts and more false alarms")
    period = b.radio("Period", ["validation", "train"], horizontal=True,
                     format_func=lambda p: "Held-out month" if p == "validation" else "Training months")
    det = cached.anomalies(k, period)
    ok = det["recall"] >= energy.RECALL_TARGET
    ui.stats([
        ui.stat("Recall", f"{det['recall']:.0f}%",
                ui.delta("meets" if ok else "misses", f"the ≥{energy.RECALL_TARGET:.0f}% target",
                         "good" if ok else "bad"), accent=True),
        ui.stat("Caught", f"{det['detected']} of {det['n_events']}", f"{det['missed']} missed"),
        ui.stat("False alarms", f"{det['false_alerts']}",
                f"precision {det['precision']:.0f}%" if det["n_alerts"] else "no alerts raised"),
        ui.stat("Alerts raised", f"{det['n_alerts']}", "Advisory only, never change equipment"),
    ])
    st.caption("Threshold 4.0 was fixed before looking at the held-out month. Synthetic faults are cleaner "
               "than real ones, so real recall would likely be lower")

    alerts = det["alerts"]
    ui.section("Alert log", "Review status is editable for the demo and lasts only for your session", "synthetic")
    if len(alerts):
        st.data_editor(
            alerts, key=f"review_{period}_{k}", hide_index=True, width="stretch",
            disabled=[c for c in alerts.columns if c != "review_status"],
            column_config={
                "alert_id": "Alert",
                "start": st.column_config.DatetimeColumn("Start", format="DD MMM HH:mm"),
                "end": st.column_config.DatetimeColumn("End", format="DD MMM HH:mm"),
                "hours": "Hours", "source_metric": "Source metric", "triggers": "All triggers",
                "peak_score": st.column_config.NumberColumn("Peak σ", format="%.1f"),
                "severity": "Severity",
                "recommendation": st.column_config.TextColumn("Recommendation", width="medium"),
                "owner": "Owner",
                "review_status": st.column_config.SelectboxColumn(
                    "Review status", required=True,
                    options=["Pending review", "Under review", "Confirmed issue", "False alarm", "Closed"]),
                "matches_injected_event": "Injected label",
            })

        idx = alerts.set_index("alert_id")
        pick = st.selectbox("Inspect an alert", alerts.alert_id,
                            format_func=lambda i: f"{i} · {idx.loc[i, 'source_metric']} · "
                                                  f"{idx.loc[i, 'start']:%d %b %H:%M} · {idx.loc[i, 'severity'].lower()}")
        row = idx.loc[pick]
        s = det["series"]
        w = s[(s.timestamp >= row.start - pd.Timedelta(hours=24)) & (s.timestamp <= row.end + pd.Timedelta(hours=24))]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                            subplot_titles=("Facility power, kW", "Zone temperature, °C", "Humidity, %"))
        for i, (obs, exp) in enumerate([("facility_power_kw", "exp_facility_power_kw"),
                                        ("zone_temp_c", "exp_zone_temp_c"),
                                        ("humidity_pct", "exp_humidity_pct")], start=1):
            fig.add_trace(go.Scatter(x=w.timestamp, y=w[exp], name="Expected", legendgroup="e", showlegend=i == 1,
                                     line=dict(color=ui.GRAY_D, width=1.5, dash="dot"), hovertemplate="%{y:.1f}"),
                          row=i, col=1)
            fig.add_trace(go.Scatter(x=w.timestamp, y=w[obs], name="Observed", legendgroup="o", showlegend=i == 1,
                                     line=dict(color=ui.INK, width=1.5), hovertemplate="%{y:.1f}"), row=i, col=1)
        fig.add_vrect(x0=row.start - pd.Timedelta(minutes=30), x1=row.end + pd.Timedelta(minutes=30),
                      fillcolor=ui.SEVERITY[row.severity], opacity=0.16, line_width=0)
        fig.update_annotations(x=0, xanchor="left")
        ui.chart(fig, 520)
        st.caption(f"Shaded: {pick}, {row.severity.lower()} severity. Expected values come from a linear model of "
                   "IT load, outside temperature and hour, fitted on normal training hours")
    else:
        st.info("No alerts at this threshold")

    ev = det["events"].copy()
    if len(ev):
        ui.section("Injected test anomalies", "The ground truth used for scoring")
        ev["detected"] = ev.detected.map({True: "Caught", False: "Missed"})
        st.dataframe(ev, hide_index=True, width="stretch", column_config={
            "event_id": "Event", "type": "Type",
            "start": st.column_config.DatetimeColumn("Start", format="DD MMM HH:mm"),
            "end": st.column_config.DatetimeColumn("End", format="DD MMM HH:mm"),
            "hours": "Hours", "detail": "Injected change", "detected": "Result"})

# ------------------------------------------------------------------ trends
with t_tr:
    c1, c2 = st.columns([1, 2], gap="large")
    res = c1.segmented_control("Resolution", ["Hourly", "Daily average"], default="Daily average")
    lo, hi = df.timestamp.min().date(), df.timestamp.max().date()
    rng = c2.slider("Date range", lo, hi, (lo, hi), format="DD MMM")
    d = df[(df.timestamp.dt.date >= rng[0]) & (df.timestamp.dt.date <= rng[1])]
    if res != "Hourly":
        d = d.set_index("timestamp").resample("D").mean(numeric_only=True).reset_index()
    pue = d.facility_power_kw.sum() / d.it_load_kw.sum()
    ui.stats([
        ui.stat("Mean zone temperature", f"{d.zone_temp_c.mean():.1f} °C", f"outside {d.outside_temp_c.mean():.1f} °C"),
        ui.stat("Mean humidity", f"{d.humidity_pct.mean():.0f}%", "relative humidity, server zone"),
        ui.stat("Mean IT load", f"{d.it_load_kw.mean():.0f} kW", f"facility {d.facility_power_kw.mean():.0f} kW"),
        ui.stat("Facility ÷ IT power", f"{pue:.2f}", "a PUE-style ratio, synthetic", accent=True),
    ])
    ui.section("Temperature, humidity and IT load", "Daily averages hide the short anomalies. Switch to hourly to see them",
               "synthetic")
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        subplot_titles=("Temperature, °C", "Humidity, %", "Load and power, kW"))
    fig.add_trace(go.Scatter(x=d.timestamp, y=d.outside_temp_c, name="Outside air",
                             line=dict(color=ui.GRAY_D, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.timestamp, y=d.zone_temp_c, name="Server zone",
                             line=dict(color=ui.ACCENT, width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.timestamp, y=d.humidity_pct, name="Humidity",
                             line=dict(color=ui.INK, width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=d.timestamp, y=d.facility_power_kw, name="Facility power",
                             line=dict(color=ui.GRAY, width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=d.timestamp, y=d.it_load_kw, name="IT load",
                             line=dict(color=ui.INK, width=1.5)), row=3, col=1)
    fig.update_annotations(x=0, xanchor="left")
    ui.chart(fig, 620)

# ------------------------------------------------------------------ model card
with t_card:
    tw, vw = fc["train_window"], fc["val_window"]
    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.section("Model card", "", "synthetic")
        rows = [
            ("Model version", energy.MODEL_VERSION),
            ("Last validation", f"{pipe['validated_at']:%d %b %Y, %H:%M} UTC · re-runs when the server restarts"),
            ("Target", "Facility power, kW, day-ahead, hourly"),
            ("Forecast model", "Gradient-boosted trees, scikit-learn HistGradientBoostingRegressor, 300 iterations, learning rate 0.05"),
            ("Features", ", ".join(energy.FEATURES)),
            ("Baselines", "Historical average by weekday and hour; persistence, same hour yesterday"),
            ("Training", f"{tw[0]:%d %b} – {tw[1]:%d %b %Y}, {fc['n_train']:,} normal hours"),
            ("Held out", f"{vw[0]:%d %b} – {vw[1]:%d %b %Y}, chronological split"),
            ("90% band", f"Split conformal, sized on the last {energy.CAL_DAYS} training days"),
            ("Anomalies", f"Robust z-score of residuals from linear expected-value models for power, zone "
                          f"temperature and humidity, plus a meter flatline rule (≥{energy.FLATLINE_HOURS} identical hours)"),
            ("Threshold", "4.0, fixed before validation"),
        ]
        st.html('<dl class="gc-dl">' + "".join(f"<dt>{a}</dt><dd>{b}</dd>" for a, b in rows) + "</dl>")
    with right:
        ui.section("Assumptions and limits")
        st.markdown(
            "- The client is fictional and so is this data. It shows the method, not real performance\n"
            "- Facility power = IT load + cooling that rises with outside temperature + fixed overhead + noise\n"
            "- The weather forecast is actual temperature plus noise of ±0.8 °C\n"
            "- Injected anomaly hours are left out of training, a documented data-quality exclusion\n"
            "- Synthetic faults are cleaner than real ones\n"
            "- Recommendations go to people. Nothing here controls equipment")
        st.download_button("Download synthetic telemetry, CSV",
                           df.assign(data_type="SYNTHETIC").to_csv(index=False).encode(),
                           "greencompute_synthetic_telemetry.csv", "text/csv", icon=":material/download:")
    ui.section("Data dictionary")
    st.dataframe(energy.DATA_DICTIONARY, hide_index=True, width="stretch")
