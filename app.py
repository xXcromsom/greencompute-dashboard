"""GreenCompute dashboard - entry point. Run: streamlit run app.py"""
import streamlit as st

from lib import ui
from lib.common import GROUP, PROJECT

st.set_page_config(page_title=f"{PROJECT} · {GROUP}", page_icon=":material/eco:", layout="wide")
ui.inject_css()

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/space_dashboard:", default=True),
    st.Page("views/energy.py", title="Energy workstream", icon=":material/bolt:"),
    st.Page("views/code.py", title="Code optimization", icon=":material/terminal:"),
    st.Page("views/financials.py", title="Financials", icon=":material/payments:"),
    st.Page("views/plan.py", title="Plan and governance", icon=":material/view_timeline:"),
    st.Page("views/risks.py", title="Risks", icon=":material/shield:"),
    st.Page("views/kpis.py", title="KPIs and conclusion", icon=":material/task_alt:"),
]
nav = st.navigation(pages, position="hidden")

with st.sidebar:
    st.html(f'<div class="gc-wordmark"><i></i>{PROJECT}</div>'
            f'<div class="gc-side-meta">{GROUP} · NAT CPM · Sem 5</div>')
    with st.container(gap="small", key="gc_nav"):
        for p in pages:
            st.page_link(p)
    st.divider()
    st.html('<div class="gc-side-meta" style="margin:0 0 12px">Where each figure comes from</div>'
            + ui.sidebar_legend())
    st.divider()
    st.caption("GreenCore Data Services is a hypothetical client. No real savings are claimed")

nav.run()
