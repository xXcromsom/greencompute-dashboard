import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import ui
from lib.common import ROLE_OF, ROLES

ui.header(
    "Plan and governance",
    "Six phases over 12 weeks, each closed by a milestone sign-off. Real timing would depend on "
    "access approvals, data availability and integration",
    eyebrow="05 · Delivery",
    tags=["report"],
)

PHASES = pd.DataFrame([
    (1, "Initiation and discovery", 1, 2, "Kick-off; confirm sponsor and stakeholders; document current-state assumptions; gather requirements and constraints.", "M1", "Approved project charter and discovery brief"),
    (2, "Data and feasibility", 3, 4, "Review data availability, quality, security and permissions; define workload; compare baseline methods; confirm architecture.", "M2", "Data readiness and solution design decision"),
    (3, "Prototype development", 5, 7, "Prepare energy dataset; develop baseline and ML models; profile and optimize selected code; build dashboard.", "M3", "Energy and code proof-of-concepts ready"),
    (4, "Testing and evaluation", 8, 9, "Validate forecast and anomaly metrics; repeat code benchmarks; test output correctness; conduct user review.", "M4", "Test report and acceptance review"),
    (5, "Training and pilot planning", 10, 11, "Prepare operating procedures; train users; refine dashboard; define pilot guardrails and rollback.", "M5", "Adoption and controlled-pilot readiness pack"),
    (6, "Handover and closure", 12, 12, "Deliver documentation, model limitations, source files, risk log, support plan and lessons learned.", "M6", "Formal handover and closure"),
], columns=["#", "Phase", "Start week", "End week", "Key activities", "Milestone", "Milestone output"])

ui.section("12-week roadmap", "Diamonds mark milestone sign-off. M1–M6 here are milestones, not team members", "report")
fig = go.Figure()
labels = [f"{r['#']}. {r.Phase}" for _, r in PHASES.iterrows()]
fig.add_trace(go.Bar(
    y=labels, x=PHASES["End week"] - PHASES["Start week"] + 1, base=PHASES["Start week"] - 1,
    orientation="h", marker_color="#3a3a3e", name="Phase", width=0.5,
    customdata=PHASES[["Start week", "End week", "Key activities"]],
    hovertemplate="%{y}<br>Weeks %{customdata[0]}–%{customdata[1]}<br>%{customdata[2]}<extra></extra>"))
fig.add_trace(go.Scatter(
    y=labels, x=PHASES["End week"], mode="markers+text", name="Milestone",
    marker=dict(symbol="diamond", size=12, color=ui.ACCENT, line=dict(width=2, color=ui.PAGE)),
    textfont=dict(family=ui.MONO, size=11, color=ui.INK2),
    text=PHASES.Milestone, textposition="middle right",
    customdata=PHASES["Milestone output"],
    hovertemplate="%{text}: %{customdata}<extra></extra>"))
fig.update_layout(showlegend=False, bargap=0.4)
fig.update_yaxes(autorange="reversed")
fig.update_xaxes(range=[0, 13.4], tickvals=[i - 0.5 for i in range(1, 13)],
                 ticktext=[f"W{i}" for i in range(1, 13)])
ui.chart(fig, 340, unified=False, sans_y=True)
st.dataframe(PHASES, hide_index=True, width="stretch", column_config={
    "#": st.column_config.NumberColumn(width="small"),
    "Key activities": st.column_config.TextColumn(width="large")})

ui.section("Work breakdown structure", "Eight work packages", "report")
WBS = pd.DataFrame([
    ("1.0", "Project initiation", "Charter, stakeholder register, governance."),
    ("2.0", "Discovery and research", "Client brief, requirements, current-state map, research summary."),
    ("3.0", "Solution and data design", "Data dictionary, architecture, privacy/security review."),
    ("4.0", "Energy prototype", "Prepared dataset, forecast model, anomaly detection, evaluation."),
    ("5.0", "Code optimization", "Baseline profile, optimized version, correctness and benchmark report."),
    ("6.0", "Integration and dashboard", "Unified dashboard, metric definitions, user review."),
    ("7.0", "Testing and acceptance", "Test plan, results, defect log, acceptance record."),
    ("8.0", "Adoption and handover", "Training material, SOP, support plan, final report."),
], columns=["WBS", "Work package", "Main outputs"])
st.dataframe(WBS, hide_index=True, width="stretch")

ui.section("Team responsibilities, RACI",
           "R responsible · A accountable · C consulted · I informed. Members mapped to roles M1–M6 in team-list order",
           "report")
RACI = [
    ("Project charter and coordination", "A/R", "C", "C", "I", "I", "I"),
    ("Discovery and client brief", "A/R", "C", "C", "C", "R", "I"),
    ("AI/IoT solution design", "C", "A/R", "C", "I", "C", "R"),
    ("WBS, schedule and risk", "A", "C", "R", "C", "C", "I"),
    ("Prototype testing and QA", "I", "R", "A/R", "I", "C", "R"),
    ("Budget and financial model", "C", "C", "C", "A/R", "I", "I"),
    ("Adoption and handover", "A", "C", "C", "I", "R", "R"),
    ("Final report and presentation", "A", "R", "R", "R", "R", "R"),
]
cols = ["Activity"] + [f"{code} {ROLE_OF[code].split()[0]} · {role}" for code, role in ROLES]
raci = pd.DataFrame(RACI, columns=cols)


def shade(v):
    if "A" in v:
        return "background-color: rgba(70,194,142,0.24); color: #ededed"
    if v == "R":
        return "background-color: rgba(70,194,142,0.10); color: #ededed"
    return "color: #85858b"


st.dataframe(raci.style.map(shade, subset=cols[1:]), hide_index=True, width="stretch")

ui.section("Monitoring and change control")
st.markdown(
    "- Weekly project review: schedule, deliverables, budget, risks, issues and decisions.\n"
    "- Sponsor checkpoint at the end of each major phase.\n"
    "- RAID log: risks, assumptions, issues and dependencies.\n"
    "- Change request for any change to scope, schedule, budget, data access or acceptance criteria; "
    "each assessed for cost, time, technical impact, security, safety and benefits.\n"
    "- Version control for code, datasets, model configurations and documents.\n"
    "- Stage-gate approval before prototype testing, user review and any future pilot."
)
