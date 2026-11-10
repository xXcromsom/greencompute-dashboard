import pandas as pd
import streamlit as st

from lib import cached, energy, ui

ui.header(
    "KPIs and conclusion",
    "What the prototype shows against the report's acceptance criteria, what a real pilot would track, "
    "and why the recommendation is a bounded pilot rather than a rollout",
    eyebrow="07 · Results",
)

# ------------------------------------------------------------------ acceptance
ui.section("Acceptance criteria", "Report section 6, checked live against this dashboard")
pipe = cached.energy_pipeline()
tbl = pipe["forecast"]["table"]
ml_mape, hist_mape = tbl["MAPE (%)"].iloc[2], tbl["MAPE (%)"].iloc[0]
det = cached.anomalies(4.0, "validation")
bm = cached.benchmark(20_000, 200, 5)
speed = (1 - bm["median_optimized"] / bm["median_baseline"]) * 100


STATUS = {"Met": ui.GOOD, "Not met": ui.BAD, "Not tested": ui.MUTED, "Supported": ui.GOOD,
          "Partly supported": ui.WARN, "Untestable here": ui.MUTED}


def ok(cond):
    return "Met" if cond else "Not met"


def status_list(rows):
    """rows: (title, detail, status, provenance or None)."""
    html = "".join(
        f'<div class="gc-row" style="grid-template-columns:12px 1fr auto auto">'
        f'<i style="background:{STATUS[s]}"></i>'
        f'<div><div class="t">{t}</div><div class="m">{d}</div></div>'
        f'<div>{ui.tag(k) if k else ""}</div><div class="r" style="min-width:112px;color:{ui.INK}">{s}</div></div>'
        for t, d, s, k in rows)
    st.html(f'<div class="gc-list">{html}</div>')


status_list([
    ("Forecast error ≤ 15% MAPE and better than a simple baseline",
     f"ML {ml_mape:.1f}% vs historical average {hist_mape:.1f}%",
     ok(ml_mape <= energy.MAPE_TARGET and ml_mape < hist_mape), "synthetic"),
    ("Detect ≥ 90% of predefined test anomalies and report false positives",
     f"recall {det['recall']:.0f}% · precision {det['precision']:.0f}% · {det['false_alerts']} false alarms · threshold 4.0",
     ok(det["recall"] >= energy.RECALL_TARGET), "synthetic"),
    ("Measurable runtime or resource gain with identical outputs",
     f"{speed:.0f}% less runtime · outputs {'identical' if bm['equal'] else 'different'}",
     ok(speed > 0 and bm["equal"]), "measured"),
    ("Dashboard shows both workstreams with synthetic, measured and projected labels",
     "every figure carries a provenance tag", "Met", None),
    ("Financial benefit verified on real metered data",
     "only scenarios exist · no client data", "Not tested", "projected"),
])
st.caption("Met on synthetic data shows the method works end to end. It does not show it would work on a "
           "real facility")

# ------------------------------------------------------------------ hypotheses
ui.section("Hypotheses", "H1–H4 from report section 3.4")
status_list([
    ("H1 · ML forecasts demand better than a historical-average baseline",
     "energy workstream → forecast", "Supported", "synthetic"),
    ("H2 · Anomaly detection finds a defined set of injected abnormal patterns",
     "energy workstream → anomaly alerts", "Supported", "synthetic"),
    ("H3 · Optimizing one program cuts runtime or resources while keeping output correct",
     "code optimization · runtime and CPU fell, peak memory rose", "Partly supported", "measured"),
    ("H4 · Integrated monitoring helps decisions; return depends on measured savings",
     "financials · scenarios only, needs client data", "Untestable here", "projected"),
])

# ------------------------------------------------------------------ KPIs
ui.section("KPIs for a real pilot", "Report section 11. Each would be tracked against a metered baseline", "report")
KPIS = pd.DataFrame([
    ("Facility electricity (kWh)", "Metered facility energy over an agreed period.", "Primary energy measure; normalize for workload and operating conditions."),
    ("PUE", "Total facility energy ÷ IT equipment energy.", "Facility efficiency indicator; does not measure application efficiency."),
    ("Energy per workload unit", "kWh ÷ agreed functional unit (e.g. 1,000 transactions).", "Links energy to service output; needs a stable functional unit."),
    ("Forecast error", "MAE or MAPE on unseen data, compared with a simple baseline.", "Tests whether ML improves prediction."),
    ("Anomaly recall / precision", "True positives ÷ actual anomalies; true positives ÷ all alerts.", "Balances missed anomalies against false alerts."),
    ("Application runtime", "Elapsed time under controlled repeated runs.", "Performance measure; not an electricity measure."),
    ("CPU and memory use", "Average/peak CPU and memory for identical inputs.", "Resource demand; read alongside output and volume."),
    ("Output correctness", "Automated tests and output comparison.", "Must stay equivalent for accepted optimization."),
    ("Operating cost", "Verified energy cost plus recurring technology and support charges.", "Avoid double-counting; separate one-time from recurring."),
    ("Adoption", "Active users, reviewed recommendations, training completion, feedback.", "Shows whether the solution is used properly."),
], columns=["KPI", "Definition", "Purpose / caution"])
st.dataframe(KPIS, hide_index=True, width="stretch")

# ------------------------------------------------------------------ alternatives
ui.section("Alternatives", "Report section 4", "report")
c = st.columns(3)
ALTS = [
    ("A. Status quo", "Keep current monitoring, manual review and developer-led optimization.",
     "No new investment; familiar; low disruption.",
     "Stays reactive; metrics fragmented; depends on staff time.",
     "Baseline option. Keep it if the case for change is weak."),
    ("B. Conventional improvement", "Better thresholds, dashboards, scheduled reviews, rule-based alerts, manual profiling.",
     "Simple, explainable, often cheaper, easier to govern.",
     "Rules miss complex patterns; manual review is slow; little forecasting.",
     "Strong comparator and a possible first step."),
    ("C. AI-enabled GreenCompute", "ML forecasting and anomaly detection plus code profiling, shown in one dashboard.",
     "Finds patterns, anticipates demand, prioritizes checks; links facility and workload views.",
     "Needs reliable data, skills, model monitoring, cybersecurity; AI adds its own energy and cost.",
     "Recommended for a bounded proof of concept, only if it beats simpler baselines."),
]
for col, (name, desc, adv, lim, verdict) in zip(c, ALTS):
    with col, st.container(border=True):
        st.markdown(f"**{name}**")
        st.write(desc)
        st.markdown(f"**For:** {adv}")
        st.markdown(f"**Against:** {lim}")
        chosen = name.startswith("C")
        st.html(f'<div class="gc-tag" style="white-space:normal;align-items:baseline;margin-top:4px">'
                f'<i style="background:{ui.ACCENT if chosen else ui.MUTED}"></i>'
                f'<span style="color:{ui.INK if chosen else ui.INK2}">{verdict}</span></div>')

# ------------------------------------------------------------------ conclusion
ui.section("Conclusion")
st.markdown(
    "AI does not automatically cut energy use. GreenCompute should be tested against simpler methods "
    "and kept only where it gives a measurable gain without hurting availability, thermal limits, "
    "code correctness or service performance.\n\n"
    "**Next steps for a real client:**\n"
    "1. Confirm data access and safety constraints.\n"
    "2. Test ML forecasting against a simple baseline on real telemetry.\n"
    "3. Show code optimization on one non-critical workload with correctness checks.\n"
    "4. Review results with operations and finance.\n"
    "5. Consider a controlled production pilot only if the benefit is measured and reliability holds."
)
st.caption("Evidence for this report is limited to published research, a hypothetical client and the "
           "prototype on this dashboard. No real savings, client approval or live performance are claimed.")
