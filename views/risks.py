import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import ui
from lib.common import owner_names

ui.header(
    "Risks",
    "Ten risks from the report on a likelihood × impact grid. Four sit at medium likelihood and high "
    "impact, and the prototype on this dashboard answers four of them directly",
    eyebrow="06 · Risk and quality",
    tags=["report"],
)

RISKS = pd.DataFrame([
    ("R1", "Insufficient or poor-quality telemetry", "Medium", "High", "Data readiness gate; validate completeness, units and timestamps; use labelled synthetic data only for prototype if needed.", "M2 / Client IT"),
    ("R2", "Forecast model performs poorly", "Medium", "Medium", "Compare against simple baseline; hold-out validation; disclose uncertainty; revert to simpler method if ML adds no value.", "M2"),
    ("R3", "False anomaly alerts", "Medium", "Medium", "Tune thresholds; report precision/recall; require human review; avoid automated control.", "M2 / Facility"),
    ("R4", "Code optimization changes output", "Medium", "High", "Unit tests, regression tests, code review, version control and rollback.", "M3 / Developer"),
    ("R5", "Cooling or operational safety issue", "Low", "Very High", "No live control in project; respect thermal and redundancy constraints; facility engineer approval for future pilot.", "Client Facility Manager"),
    ("R6", "Cybersecurity or data leakage", "Medium", "High", "Least-privilege access, encryption, approved storage, data minimization and no unauthorized source-code upload.", "Client IT Security"),
    ("R7", "Integration delays", "Medium", "Medium", "Use file-based prototype interfaces; confirm dependencies early; maintain schedule buffer.", "M3"),
    ("R8", "Budget overrun / AI usage charges", "Medium", "Medium", "Set usage limits, alerts and approvals; track actual consumption; contingency reserve.", "M4"),
    ("R9", "Low user adoption", "Medium", "Medium", "Involve users in design; provide training; make recommendations explainable; collect feedback.", "M5"),
    ("R10", "Overstated financial benefits", "Medium", "High", "Label scenarios; baseline measurement; independent review; no double-counting; report uncertainty.", "M4 / Sponsor"),
], columns=["ID", "Risk", "Likelihood", "Impact", "Mitigation", "Owner"])
RISKS["Owner"] = RISKS.Owner.map(owner_names)

LIK = ["Low", "Medium", "High"]
IMP = ["Low", "Medium", "High", "Very High"]
L_SCORE = {v: i + 1 for i, v in enumerate(LIK)}
I_SCORE = {v: i + 1 for i, v in enumerate(IMP)}
RISKS["Score"] = RISKS.Likelihood.map(L_SCORE) * RISKS.Impact.map(I_SCORE)

z, text, hover = [], [], []
for lik in reversed(LIK):
    zr, tr, hr = [], [], []
    for imp in IMP:
        cell = RISKS[(RISKS.Likelihood == lik) & (RISKS.Impact == imp)]
        zr.append(L_SCORE.get(lik, 0) * I_SCORE[imp])
        tr.append("<br>".join(cell.ID) if len(cell) else "")
        hr.append("<br>".join(f"{r.ID}: {r.Risk}" for _, r in cell.iterrows()) or "No risks")
    z.append(zr)
    text.append(tr)
    hover.append(hr)

left, right = st.columns([3, 2], gap="large")
with left:
    fig = go.Figure(go.Heatmap(
        z=z, x=IMP, y=list(reversed(LIK)), text=text, texttemplate="%{text}",
        customdata=hover, hovertemplate="Likelihood %{y} · Impact %{x}<br>%{customdata}<extra></extra>",
        colorscale=[[0, "#1d1d1f"], [0.25, "#3a2828"], [1, "#b8433f"]], zmin=1, zmax=12,
        xgap=4, ygap=4, showscale=False, textfont=dict(family=ui.MONO, size=12, color=ui.INK)))
    ui.section("Likelihood × impact", "Cell shade = likelihood × impact score. Hover a cell for risk names", "report")
    fig.update_xaxes(title_text="Impact")
    fig.update_yaxes(title_text="Likelihood")
    ui.chart(fig, 360, unified=False, sans_y=True, sans_x=True)
with right:
    ui.section("Read-out")
    st.markdown(
        "- **4 risks** are Medium likelihood / High impact: data quality, code changing output, "
        "cybersecurity and overstated benefits. These need the closest watch.\n"
        "- **Safety (R5)** is rare but Very High impact, so the project keeps **no live control** of "
        "cooling equipment.\n"
        "- No risk is rated High likelihood.\n"
        "- This dashboard tackles R2, R3, R4 and R10 directly: baseline comparison, "
        "precision/recall reporting, output-equality checks and data-type labels."
    )

ui.section("Risk register", "Sorted by likelihood × impact", "report")
owners = sorted({o.strip() for v in RISKS.Owner for o in v.split(" / ")})
pick = st.multiselect("Filter by owner", owners)
show = RISKS if not pick else RISKS[RISKS.Owner.apply(lambda v: any(p in v for p in pick))]
st.dataframe(show.sort_values("Score", ascending=False), hide_index=True, width="stretch",
             column_config={"Score": st.column_config.NumberColumn(
                 "Score", help="Likelihood (1–3) × impact (1–4), for sorting only", width="small"),
                 "Mitigation": st.column_config.TextColumn(width="large")})

ui.section("Quality assurance")
st.markdown(
    "- Data quality checks documented before model training.\n"
    "- Train/test separation to reduce leakage and overfitting.\n"
    "- Baseline comparison for every predictive metric.\n"
    "- Code outputs checked for equivalence before performance comparisons are accepted.\n"
    "- Benchmark runs repeated under consistent conditions.\n"
    "- Dashboard labels distinguish synthetic, measured and projected values.\n"
    "- Critical recommendations reviewed by the relevant facility or software owner."
)
