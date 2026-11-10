import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import finance, ui
from lib.common import inr

ui.header(
    "Financials",
    f"An illustrative {inr(finance.TOTAL)} budget for the 12-week pilot, paid on accepted milestones, and a "
    "calculator that shows what energy cut would be needed to pay it back",
    eyebrow="04 · Budget and business case",
    tags=["report", "projected"],
)

# ------------------------------------------------------------------ budget + billing
left, right = st.columns([1, 1], gap="large")
with left:
    ui.section("Budget by item", "Planning figures, not vendor quotes. Excludes taxes and capital spending", "report")
    bud = finance.BUDGET.sort_values("Amount")
    colors = [ui.ACCENT if v == bud.Amount.max() else ui.GRAY_D for v in bud.Amount]
    fig = go.Figure(go.Bar(
        y=bud["Cost item"], x=bud.Amount, orientation="h", marker_color=colors,
        text=[f"{inr(v)}  {v / finance.TOTAL:.0%}" for v in bud.Amount], textposition="outside",
        textfont=dict(family=ui.MONO, size=11, color=ui.INK2), cliponaxis=False,
        customdata=bud["Basis / note"], hovertemplate="%{y}<br>%{customdata}<extra></extra>"))
    fig.update_xaxes(range=[0, bud.Amount.max() * 1.7], showticklabels=False, showline=False)
    fig.update_layout(bargap=0.45)
    ui.chart(fig, 300, unified=False, sans_y=True)
    st.caption(f"Consulting and delivery is {540_000 / finance.TOTAL:.0%} of the total. Contingency is "
               f"{75_000 / finance.TOTAL:.0%}")
with right:
    ui.section("Milestone billing", "Fixed fee, released only when a deliverable is accepted", "report")
    m = finance.MILESTONES.copy()
    m["Cumulative"] = m.Amount.cumsum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=m.Week, y=m.Amount, name="Payment", marker_color=ui.GRAY_D, width=0.5,
                         customdata=np.stack([m.Milestone, m.Share * 100], axis=1),
                         hovertemplate="%{customdata[0]}<br>₹%{y:,.0f} · %{customdata[1]:.0f}%<extra></extra>"))
    fig.add_trace(go.Scatter(x=m.Week, y=m.Cumulative, name="Billed to date", mode="lines+markers",
                             line=dict(color=ui.ACCENT, width=2, shape="hv"), marker=dict(size=7),
                             hovertemplate="₹%{y:,.0f} billed<extra></extra>"))
    fig.update_xaxes(dtick=1, range=[0.5, 12.5], tickprefix="W")
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    ui.chart(fig, 300, unified=False)
    st.caption("20% · 20% · 30% · 20% · 10%. Cloud, AI and licence usage is billed separately with monthly "
               "cost reports")

# ------------------------------------------------------------------ calculator
ui.section("Scenario calculator", "Defaults are the report's assumptions. Change them to test the case. "
           "These are scenarios, not measured or promised savings", "projected")
d = finance.DEFAULTS
with st.container(border=True):
    c = st.columns(5, gap="medium")
    kwh = c[0].number_input("Annual electricity, kWh", 100_000, 50_000_000, d["kwh"], 50_000)
    tariff = c[1].number_input("Tariff, ₹ per kWh", 1.0, 30.0, d["tariff"], 0.25)
    initial = c[2].number_input("Initial cost, ₹", 50_000, 50_000_000, d["initial"], 10_000)
    recurring = c[3].number_input("Recurring cost, ₹ a year", 0, 10_000_000, d["recurring"], 10_000)
    custom = c[4].number_input("Your scenario, % cut", 0.5, 20.0, 5.0, 0.5) / 100

rows = [{"Scenario": n, **finance.scenario(kwh, tariff, initial, recurring, p)} for n, p in finance.SCENARIOS]
rows.append({"Scenario": "Your scenario", **finance.scenario(kwh, tariff, initial, recurring, custom)})
res = pd.DataFrame(rows)


def months(v):
    return "never" if np.isnan(v) else f"{v:.1f} mo"


ui.stats([
    ui.stat(f"{r.Scenario} · {r['Energy reduction']:.1%} cut", months(r["Payback (months)"]),
            ui.delta(f"{r['Annual ROI (%)']:.1f}%", f"annual ROI · net {inr(r['Net annual benefit'])} a year",
                     "bad" if r["Net annual benefit"] <= 0 else ""),
            accent=r.Scenario == "Base case")
    for _, r in res.iterrows()
])
be = finance.break_even_reduction(kwh, tariff, recurring)
st.caption(f"Break-even cut, just covering the recurring cost: {be:.2%}. Below that the pilot never pays back")

left, right = st.columns(2, gap="large")
with left:
    ui.section("Payback vs assumed cut", "Months to recover the initial cost", "projected")
    grid = np.linspace(max(be * 1.02, 0.002), 0.15, 240)
    pb = [finance.scenario(kwh, tariff, initial, recurring, g)["Payback (months)"] for g in grid]
    fig = go.Figure(go.Scatter(x=grid * 100, y=pb, mode="lines", line=dict(color=ui.GRAY, width=1.5),
                               name="Payback", hovertemplate="%{x:.1f}% cut → %{y:.1f} months<extra></extra>"))
    for _, r in res.iterrows():
        if np.isnan(r["Payback (months)"]):
            continue
        lead = r.Scenario == "Base case"
        fig.add_trace(go.Scatter(
            x=[r["Energy reduction"] * 100], y=[r["Payback (months)"]], mode="markers+text",
            marker=dict(size=10 if lead else 8, color=ui.ACCENT if lead else ui.INK2,
                        line=dict(width=2, color=ui.PAGE)),
            text=[f"{r.Scenario} {r['Payback (months)']:.1f}"], textposition="middle right",
            textfont=dict(family=ui.MONO, size=11, color=ui.INK if lead else ui.INK2), showlegend=False,
            hovertemplate=f"{r.Scenario}: %{{y:.1f}} months<extra></extra>"))
    fig.update_xaxes(ticksuffix="%", range=[0, 15.5])
    fig.update_yaxes(range=[0, 140], title_text="months")
    fig.update_layout(showlegend=False)
    ui.chart(fig, 320, unified=False)
with right:
    ui.section("Cash position over five years", "Initial cost, then net benefit month by month", "projected")
    mo = np.arange(0, 61)
    fig = go.Figure()
    styles = {"Conservative": (ui.GRAY_D, 1.5, "dot"), "Base case": (ui.ACCENT, 2, None),
              "Optimistic": (ui.GRAY, 1.5, "dash"), "Your scenario": (ui.INK, 1.5, None)}
    for _, r in res.iterrows():
        color, width, dash = styles[r.Scenario]
        fig.add_trace(go.Scatter(x=mo, y=-initial + r["Net annual benefit"] / 12 * mo, name=r.Scenario,
                                 line=dict(color=color, width=width, dash=dash), hovertemplate="₹%{y:,.0f}"))
    fig.add_hline(y=0, line=dict(color="rgba(237,237,237,0.25)", width=1))
    fig.update_xaxes(title_text="month")
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    ui.chart(fig, 320)

show = res.assign(**{
    "Energy reduction": res["Energy reduction"].map("{:.1%}".format),
    "kWh saved": res["kWh saved"].map("{:,.0f}".format),
    "Gross annual saving": res["Gross annual saving"].map(inr),
    "Net annual benefit": res["Net annual benefit"].map(inr),
    "Payback (months)": res["Payback (months)"].map(lambda v: "never" if np.isnan(v) else f"{v:.1f}"),
    "Annual ROI (%)": res["Annual ROI (%)"].map("{:.1f}".format),
})
st.dataframe(show, hide_index=True, width="stretch")

with st.expander("Formulas and the check against the report"):
    st.code(
        "Gross annual saving = annual kWh × cut × tariff\n"
        "Net annual benefit  = gross annual saving − recurring cost\n"
        "Payback, months     = initial cost ÷ net annual benefit × 12   (only when net benefit > 0)\n"
        "Annual ROI, %       = net annual benefit ÷ initial cost × 100",
        language=None)
    st.markdown(
        "With the report's defaults: payback **117.1 / 25.2 / 14.1 months** and ROI **10.2% / 47.6% / 84.9%** "
        "for the 2% / 5% / 8% cuts, matching the report text. Two payback cells in the report's table carry a "
        "stray character before the number; the values here are the correct ones. Code savings are not added "
        "to avoid double-counting (report 8.4)")
