"""Shared project constants, team data and formatting helpers."""
from __future__ import annotations

PROJECT = "GreenCompute"
SUBTITLE = "AI-driven energy and computing optimization for sustainable data centres"
COURSE = "NAT Consulting and Project Management · BBA Semester 5"
GROUP = "WAS Group 2"
CLIENT = "GreenCore Data Services Pvt. Ltd., Bengaluru (hypothetical client)"
SUBMITTED = "8 November 2026"

# Roles M1-M6 come from the report's RACI table. People are mapped in the
# order the team list was given; change ROLE_OF if the group decides otherwise.
TEAM = [
    ("Adithya Pradeep", "246213368"),
    ("Sankarshana Mulugundam", "246213080"),
    ("Faizan Ali Siddiqui", "246213110"),
    ("Samiksha Sandeep Das", "246213076"),
    ("Anupama Sahu", "246213502"),
    ("Prathamesh Prabhu", "246213290"),
]
ROLES = [
    ("M1", "PM / Client"),
    ("M2", "Tech / AI"),
    ("M3", "Delivery / QA"),
    ("M4", "Finance"),
    ("M5", "Research"),
    ("M6", "Prototype / Adoption"),
]
PRESENTING = [
    "Introduction, hypothetical client, problem and discovery",
    "Research, evidence and alternatives assessment",
    "AI/IoT solution architecture and energy prototype",
    "Code optimization prototype, scope and project plan",
    "Budget, commercial model, financial scenarios and risks",
    "Adoption, KPIs, limitations and conclusion",
]
ROLE_OF = {code: name for (code, _), (name, _) in zip(ROLES, TEAM)}

def member(code: str) -> str:
    return f"{code} · {ROLE_OF[code]}"


def owner_names(owner: str) -> str:
    """Expand 'M2 / Client IT' into 'M2 (Name) / Client IT'."""
    parts = []
    for p in owner.split("/"):
        p = p.strip()
        parts.append(f"{p} ({ROLE_OF[p]})" if p in ROLE_OF else p)
    return " / ".join(parts)


def inr(x: float, decimals: int = 0) -> str:
    """Indian digit grouping: 820000 -> ₹8,20,000."""
    neg = x < 0
    x = abs(x)
    whole = int(round(x)) if decimals == 0 else int(x)
    frac = "" if decimals == 0 else f"{x - whole:.{decimals}f}"[1:]
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups) + "," + tail
    return ("-" if neg else "") + "₹" + s + frac
