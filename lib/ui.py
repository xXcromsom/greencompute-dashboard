"""Visual system: tokens, global CSS, provenance tags, stat cards and the Plotly template.

See DESIGN.md for the reasoning behind these values.
"""
from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---- tokens
ACCENT = "#46c28e"
ACCENT_FILL = "rgba(70,194,142,0.14)"
INK, INK2, MUTED = "#ededed", "#a1a1a6", "#85858b"
GRAY, GRAY_D = "#8e8e93", "#5b5b60"
PAGE, SIDEBAR, CARD, RAISED = "#141415", "#0f0f10", "#19191b", "#232325"
HAIR = "rgba(237,237,237,0.08)"
GOOD, BAD, WARN = "#46c28e", "#e5484d", "#e0a43a"
SEVERITY = {"High": BAD, "Medium": WARN, "Low": MUTED}
MONO = "'Geist Mono', ui-monospace, monospace"

PROV = {
    "synthetic": ("synthetic", WARN, "Generated in this app with a fixed seed. Not real facility data"),
    "measured": ("measured", ACCENT, "Measured live on the server running this app"),
    "projected": ("projected", "#9b8cf0", "Scenario output from stated assumptions. Not a promise"),
    "report": ("report", MUTED, "Planning figure taken from the group report"),
}

CSS = f"""
<style>
:root {{ --gc-accent:{ACCENT}; --gc-ink:{INK}; --gc-ink2:{INK2}; --gc-muted:{MUTED};
        --gc-card:{CARD}; --gc-raised:{RAISED}; --gc-hair:{HAIR}; --gc-mono:{MONO}; }}
[data-testid="stAppDeployButton"], [data-testid="stDecoration"] {{ display:none; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.block-container {{ max-width:1440px; padding:40px 32px 96px; }}
h1 {{ letter-spacing:-0.015em; line-height:1.15 !important; }}
h2, h3 {{ letter-spacing:-0.005em; }}
[data-testid="stCaptionContainer"] {{ color:var(--gc-muted); }}

/* sidebar */
[data-testid="stSidebarNav"] {{ padding-top:4px; }}
[data-testid="stSidebarNav"] a {{ min-height:34px; border-radius:8px; margin:2px 0; padding:0 12px; }}
[data-testid="stSidebarNav"] a span {{ font-size:14px; color:var(--gc-ink2); }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background:var(--gc-raised);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.06); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color:var(--gc-ink); }}
[data-testid="stSidebarNav"] a span[data-testid="stIconMaterial"] {{ font-size:18px; color:var(--gc-muted); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span[data-testid="stIconMaterial"] {{ color:var(--gc-accent); }}

/* custom sidebar nav (st.page_link) */
.st-key-gc_nav {{ margin-top:12px; gap:2px !important; }}
.st-key-gc_nav [data-testid="stPageLink"] a {{ min-height:34px; border-radius:8px; padding:0 12px; }}
.st-key-gc_nav [data-testid="stPageLink"] a p {{ font-size:14px; color:var(--gc-ink2); }}
.st-key-gc_nav [data-testid="stPageLink"] a span[data-testid="stIconMaterial"] {{ font-size:18px; color:var(--gc-muted); }}
.st-key-gc_nav [data-testid="stPageLink-NavLink"][aria-current="page"],
.st-key-gc_nav [data-testid="stPageLink"] a.active {{ background:var(--gc-raised); box-shadow:inset 0 1px 0 rgba(255,255,255,0.06); }}

/* tabs */
[data-baseweb="tab-list"] {{ gap:24px; border-bottom:1px solid var(--gc-hair); }}
[data-baseweb="tab"] {{ padding:0 0 12px; }}
[data-baseweb="tab"] p {{ font-size:14px; }}
[data-baseweb="tab-highlight"] {{ background:var(--gc-accent); height:2px; }}
[data-baseweb="tab-border"] {{ display:none; }}

/* bordered containers read as cards */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{ border-radius:12px; }}
[data-testid="stExpander"] details {{ border-radius:12px; border-color:var(--gc-hair); }}

/* building blocks */
.gc-eyebrow {{ font:400 12px/16px var(--gc-mono); color:var(--gc-muted); margin-bottom:12px; }}
.gc-title {{ font-size:32px; line-height:1.15; font-weight:500; letter-spacing:-0.015em; color:var(--gc-ink); margin:0; max-width:52rem; }}
.gc-sub {{ font-size:16px; line-height:24px; color:var(--gc-ink2); margin:12px 0 0; max-width:44rem; }}
.gc-tags {{ display:flex; flex-wrap:wrap; gap:16px; margin-top:16px; }}
.gc-tag {{ display:inline-flex; align-items:center; gap:6px; font:400 12px/16px var(--gc-mono); color:var(--gc-ink2); white-space:nowrap; }}
.gc-tag i {{ width:6px; height:6px; border-radius:50%; display:inline-block; }}
.gc-tag-note {{ color:var(--gc-muted); font:400 13px/20px inherit; font-family:inherit; white-space:normal; }}
.gc-note {{ border:1px solid var(--gc-hair); border-radius:12px; padding:12px 16px; color:var(--gc-ink2);
           font-size:14px; line-height:20px; display:flex; gap:12px; align-items:baseline; margin:24px 0 8px; }}
.gc-note b {{ font:500 12px/16px var(--gc-mono); color:var(--gc-ink); white-space:nowrap; font-weight:500; }}
.gc-stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:24px 0 8px; }}
.gc-stat {{ background:var(--gc-card); border:1px solid var(--gc-hair); border-radius:12px; padding:16px 20px 20px; display:flex; flex-direction:column; gap:8px; }}
.gc-stat-top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
.gc-stat-label {{ font-size:13px; line-height:20px; color:var(--gc-ink2); }}
.gc-stat-value {{ font:500 30px/1.1 var(--gc-mono); color:var(--gc-ink); font-variant-numeric:tabular-nums; letter-spacing:-0.02em; }}
.gc-stat-value.accent {{ color:var(--gc-accent); }}
.gc-stat-delta {{ font-size:13px; line-height:20px; color:var(--gc-muted); }}
.gc-stat-delta b {{ font-weight:500; color:var(--gc-ink2); font-family:var(--gc-mono); }}
.gc-stat-delta b.good {{ color:{GOOD}; }} .gc-stat-delta b.bad {{ color:{BAD}; }}
.gc-head {{ display:flex; justify-content:space-between; align-items:baseline; gap:16px; margin:32px 0 4px; flex-wrap:wrap; }}
.gc-head h4 {{ font-size:16px; line-height:24px; font-weight:500; color:var(--gc-ink); margin:0; padding:0; }}
.gc-head p {{ font-size:13px; line-height:20px; color:var(--gc-muted); margin:2px 0 0; max-width:48rem; }}
.gc-list {{ border:1px solid var(--gc-hair); border-radius:12px; background:var(--gc-card); padding:4px 0; }}
.gc-row {{ display:grid; grid-template-columns:12px 1fr auto; gap:10px; align-items:center; padding:10px 16px; border-top:1px solid var(--gc-hair); }}
.gc-row:first-child {{ border-top:none; }}
.gc-row i {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}
.gc-row .t {{ font-size:14px; line-height:20px; color:var(--gc-ink); }}
.gc-row .m {{ font:400 12px/16px var(--gc-mono); color:var(--gc-muted); margin-top:2px; }}
.gc-row .r {{ font:400 12px/16px var(--gc-mono); color:var(--gc-ink2); text-align:right; }}
.gc-dl {{ margin:0 !important; padding:0 !important; display:grid; grid-template-columns:132px 1fr; gap:12px 20px; font-size:14px; line-height:22px; }}
.gc-dl dt {{ color:var(--gc-muted); }} .gc-dl dd {{ margin:0; color:var(--gc-ink); }}
.gc-team {{ display:grid; grid-template-columns:auto 1fr auto; gap:0 16px; font-size:14px; line-height:20px; }}
.gc-team > div {{ padding:10px 0; border-top:1px solid var(--gc-hair); }}
.gc-team .code {{ font:400 12px/20px var(--gc-mono); color:var(--gc-accent); }}
.gc-team .role {{ color:var(--gc-muted); font-size:13px; }}
.gc-team .roll {{ font:400 12px/20px var(--gc-mono); color:var(--gc-ink2); text-align:right; }}
.gc-wordmark {{ font-size:17px; font-weight:600; color:var(--gc-ink); display:flex; align-items:center; gap:8px; }}
.gc-wordmark i {{ width:8px; height:8px; border-radius:2px; background:var(--gc-accent); display:inline-block; }}
.gc-side-meta {{ font:400 12px/18px var(--gc-mono); color:var(--gc-muted); margin-top:4px; }}
.gc-legend {{ display:flex; flex-direction:column; gap:10px; }}
.gc-legend .gc-tag {{ white-space:normal; align-items:baseline; }}
.gc-legend span.d {{ color:var(--gc-muted); font-family:inherit; font-size:12px; }}
@media (max-width: 640px) {{
  .block-container {{ padding:24px 16px 64px; }}
  .gc-title {{ font-size:26px; }}
  .gc-dl {{ grid-template-columns:1fr; gap:2px 0; }} .gc-dl dd {{ margin-bottom:10px; }}
}}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


# ---- provenance signature
def tag(kind: str, note: str | None = None) -> str:
    label, color, _ = PROV[kind]
    extra = f'<span class="gc-tag-note">{escape(note)}</span>' if note else ""
    return f'<span class="gc-tag"><i style="background:{color}"></i>{label}</span>{extra}'


def header(title: str, sub: str = "", eyebrow: str = "", tags: list[str] | None = None) -> None:
    tags_html = "".join(tag(t) for t in (tags or []))
    st.html(
        (f'<div class="gc-eyebrow">{escape(eyebrow)}</div>' if eyebrow else "")
        + f'<h1 class="gc-title">{escape(title)}</h1>'
        + (f'<p class="gc-sub">{escape(sub)}</p>' if sub else "")
        + (f'<div class="gc-tags">{tags_html}</div>' if tags_html else "")
    )


def note(text: str, label: str = "note") -> None:
    st.html(f'<div class="gc-note"><b>{escape(label)}</b><span>{text}</span></div>')


def section(title: str, sub: str = "", kind: str | None = None) -> None:
    right = tag(kind) if kind else ""
    st.html(f'<div class="gc-head"><div><h4>{escape(title)}</h4>'
            + (f"<p>{sub}</p>" if sub else "") + f"</div><div>{right}</div></div>")


def stat(label: str, value: str, delta: str = "", kind: str | None = None,
         accent: bool = False) -> str:
    return (f'<div class="gc-stat"><div class="gc-stat-top"><span class="gc-stat-label">{escape(label)}</span>'
            + (tag(kind) if kind else "") + "</div>"
            + f'<div class="gc-stat-value{" accent" if accent else ""}">{escape(value)}</div>'
            + (f'<div class="gc-stat-delta">{delta}</div>' if delta else "") + "</div>")


def stats(cards: list[str]) -> None:
    st.html('<div class="gc-stats">' + "".join(cards) + "</div>")


def delta(value: str, rest: str, tone: str = "") -> str:
    return f'<b class="{tone}">{escape(value)}</b> {escape(rest)}'


def sidebar_legend() -> str:
    rows = "".join(
        f'<div class="gc-tag"><i style="background:{c}"></i><span>{l}<br><span class="d">{escape(m)}</span></span></div>'
        for l, c, m in PROV.values())
    return f'<div class="gc-legend">{rows}</div>'


# ---- charts
pio.templates["gc"] = go.layout.Template(layout=dict(
    font=dict(family="Geist, system-ui, sans-serif", size=12, color=INK2),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[ACCENT, GRAY, GRAY_D, WARN],
    margin=dict(l=8, r=8, t=36, b=8),
    hovermode="x unified",
    hoverlabel=dict(bgcolor=RAISED, bordercolor="#2f2f32",
                    font=dict(family="Geist, sans-serif", size=12, color=INK)),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, xanchor="left",
                bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=INK2), title_text=""),
    xaxis=dict(showgrid=False, zeroline=False, ticks="", linecolor="rgba(237,237,237,0.14)",
               tickfont=dict(family=MONO, size=11, color=MUTED), title_font=dict(size=12, color=MUTED)),
    yaxis=dict(gridcolor="rgba(237,237,237,0.06)", zeroline=False, ticks="", showline=False,
               tickfont=dict(family=MONO, size=11, color=MUTED), title_font=dict(size=12, color=MUTED)),
))
pio.templates.default = "gc"


def chart(fig: go.Figure, height: int = 340, unified: bool = True, sans_y: bool = False,
          sans_x: bool = False) -> None:
    # Streamlit re-themes figures in the browser, so every style is set explicitly here.
    lay = pio.templates["gc"].layout
    fig.update_layout(
        template="gc", height=height, hovermode="x unified" if unified else "closest",
        font=lay.font, paper_bgcolor=lay.paper_bgcolor, plot_bgcolor=lay.plot_bgcolor,
        hoverlabel=lay.hoverlabel, margin=dict(l=8, r=8, t=36, b=8),
    )
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, xanchor="left",
                                  bgcolor="rgba(0,0,0,0)", font=dict(size=12, color=INK2), title_text=""))
    fig.update_xaxes(showgrid=False, zeroline=False, ticks="", automargin=True,
                     linecolor="rgba(237,237,237,0.14)", tickfont=dict(family=MONO, size=11, color=MUTED),
                     title_font=dict(size=12, color=MUTED))
    fig.update_yaxes(gridcolor="rgba(237,237,237,0.06)", zeroline=False, ticks="", showline=False,
                     automargin=True, tickfont=dict(family=MONO, size=11, color=MUTED),
                     title_font=dict(size=12, color=MUTED))
    fig.update_annotations(font=dict(size=12, color=INK2))
    sans = dict(family="Geist, sans-serif", size=13, color=INK2)
    if sans_y:
        fig.update_yaxes(tickfont=sans, gridcolor="rgba(0,0,0,0)")
    if sans_x:
        fig.update_xaxes(tickfont=sans)
    st.plotly_chart(fig, theme=None, width="stretch", config={"displayModeBar": False})
