"""Financial figures and scenario maths from report section 8 and Appendix B."""
from __future__ import annotations

import pandas as pd

BUDGET = pd.DataFrame([
    ("Consulting and project delivery", 540_000, "Discovery, design, project management, analytics, development and reporting."),
    ("Cloud / software / AI usage", 45_000, "Limited development and testing usage; actual charges depend on workload and provider."),
    ("Sensors / data simulation / test setup", 65_000, "Small-scale test instruments or controlled data preparation; not industrial installation."),
    ("Dashboard and integration effort", 70_000, "Prototype dashboard, data connectors and testing."),
    ("Training, documentation and workshops", 25_000, "User sessions, SOPs and handover."),
    ("Contingency", 75_000, "Allowance for uncertainty and minor rework."),
], columns=["Cost item", "Amount", "Basis / note"])
TOTAL = int(BUDGET.Amount.sum())  # 8,20,000

MILESTONES = pd.DataFrame([
    ("Initiation and discovery acceptance", 0.20, 2),
    ("Solution and data design acceptance", 0.20, 4),
    ("Prototype development and integration", 0.30, 7),
    ("Testing and evaluation", 0.20, 9),
    ("Handover and closure", 0.10, 12),
], columns=["Milestone", "Share", "Week"])
MILESTONES["Amount"] = (MILESTONES.Share * TOTAL).round().astype(int)

DEFAULTS = {"kwh": 1_200_000, "tariff": 8.50, "initial": 820_000, "recurring": 120_000}
SCENARIOS = [("Conservative", 0.02), ("Base case", 0.05), ("Optimistic", 0.08)]


def scenario(kwh: float, tariff: float, initial: float, recurring: float, reduction: float) -> dict:
    gross = kwh * reduction * tariff
    net = gross - recurring
    payback = initial / net * 12 if net > 0 else float("nan")
    roi = net / initial * 100 if initial > 0 else float("nan")
    return {"Energy reduction": reduction, "kWh saved": kwh * reduction,
            "Gross annual saving": gross, "Net annual benefit": net,
            "Payback (months)": payback, "Annual ROI (%)": roi}


def break_even_reduction(kwh: float, tariff: float, recurring: float) -> float:
    """Reduction needed just to cover the recurring cost."""
    return recurring / (kwh * tariff) if kwh * tariff > 0 else float("nan")
