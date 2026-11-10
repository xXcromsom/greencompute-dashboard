import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import cached, energy, finance, ui
from lib.common import COURSE, GROUP, ROLES, SUBMITTED, TEAM

ui.header(
    "Can AI cut a data centre's energy and compute waste without risking uptime",
    "GreenCompute is a 12-week proof-of-concept proposal for GreenCore Data Services, a hypothetical "
    "Bengaluru operator. It tests an ML energy forecast and a code optimization against simpler methods, "
    "and tags every figure with where it comes from",
    eyebrow=f"{GROUP} · {COURSE} · submitted {SUBMITTED}",
)
ui.note("GreenCore is fictional. Energy data is generated in this app, the code benchmark runs on this "
        "server, and the money figures are scenarios from the report. Nothing here is a real saving.",
        label="read first")

# ---- figures
pipe = cached.energy_pipeline()
tbl = pipe["forecast"]["table"]
ml_mape, hist_mape = tbl["MAPE (%)"].iloc[2], tbl["MAPE (%)"].iloc[0]
det = cached.anomalies(4.0, "validation")
bm = cached.benchmark(20_000, 200, 5)
speedup = bm["median_baseline"] / bm["median_optimized"]
base = finance.scenario(**finance.DEFAULTS, reduction=0.05)

ui.stats([
    ui.stat("Forecast error", f"{ml_mape:.1f}%",
            ui.delta(f"{ml_mape - hist_mape:+.1f} pts", "vs baseline · held-out month · target ≤15%", "good"),
            "synthetic", accent=True),
    ui.stat("Anomalies caught", f"{det['detected']} of {det['n_events']}",
            ui.delta(f"{det['false_alerts']}", f"false alarms · recall target ≥{energy.RECALL_TARGET:.0f}%"),
            "synthetic"),
    ui.stat("Code runtime", f"{speedup:.0f}× faster",
            ui.delta("identical" if bm["equal"] else "different", "output vs baseline · not converted to kWh",
                     "good" if bm["equal"] else "bad"),
            "measured"),
    ui.stat("Payback, base case", f"{base['Payback (months)']:.1f} mo",
            ui.delta(f"{base['Annual ROI (%)']:.1f}%", "annual ROI at an assumed 5% energy cut"),
            "projected"),
])

# ---- moment: forecast + alert list
left, right = st.columns([2, 1], gap="large")
with left:
    ui.section("Facility power, last 14 days of the held-out month",
               "Observed vs the ML day-ahead forecast and its 90% band, with the historical-average baseline",
               "synthetic")
    v = pipe["forecast"]["val"]
    v = v[v.timestamp > v.timestamp.max() - pd.Timedelta(days=14)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.ml_hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.ml_lo, line=dict(width=0), fill="tonexty",
                             fillcolor=ui.ACCENT_FILL, name="90% band", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.hist_avg, name="Historical average",
                             line=dict(color=ui.GRAY_D, width=1.5, dash="dot"), hovertemplate="%{y:.0f} kW"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.facility_power_kw, name="Observed",
                             line=dict(color=ui.INK, width=1.5), hovertemplate="%{y:.0f} kW"))
    fig.add_trace(go.Scatter(x=v.timestamp, y=v.ml, name="ML forecast",
                             line=dict(color=ui.ACCENT, width=2), hovertemplate="%{y:.0f} kW"))
    fig.update_yaxes(ticksuffix=" kW")
    ui.chart(fig, 360)

with right:
    ui.section("Alerts, held-out month", "Threshold 4.0 · advisory only", "synthetic")
    a = det["alerts"].sort_values("peak_score", ascending=False)
    rows = "".join(
        f'<div class="gc-row"><i style="background:{ui.SEVERITY[r.severity]}"></i>'
        f'<div><div class="t">{r.source_metric}</div><div class="m">{r.start:%d %b %H:%M} · {r.hours} h · {r.severity.lower()}</div></div>'
        f'<div class="r">{r.peak_score:.1f}σ</div></div>'
        for r in a.head(7).itertuples())
    st.html(f'<div class="gc-list">{rows}</div>')
    st.caption(f"Top {min(7, len(a))} of {len(a)} by score. Full log on the Energy page")

# ---- proposal + team
left, right = st.columns([3, 2], gap="large")
with left:
    ui.section("The proposal in five lines")
    st.html("""<dl class="gc-dl">
      <dt>Client</dt><dd>GreenCore Data Services Pvt. Ltd., Bengaluru. Hypothetical managed data-centre and cloud provider</dd>
      <dt>Problem</dt><dd>Energy, facility and workload data sit in separate tools, so decisions stay reactive</dd>
      <dt>Energy track</dt><dd>Forecast facility power and flag unusual patterns for human review. No live control of cooling</dd>
      <dt>Code track</dt><dd>Profile one Python workload, optimize it, prove the output is unchanged</dd>
      <dt>Recommendation</dt><dd>A bounded pilot. Keep AI only where it beats simpler methods without hurting reliability</dd>
    </dl>""")
with right:
    ui.section("Team", "Roles M1–M6 from the report's RACI, mapped in team-list order")
    rows = "".join(
        f'<div class="code">{code}</div><div>{name}<div class="role">{role}</div></div><div class="roll">{roll}</div>'
        for (code, role), (name, roll) in zip(ROLES, TEAM))
    st.html(f'<div class="gc-team">{rows}</div>')
