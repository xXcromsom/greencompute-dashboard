import inspect
import statistics

import plotly.graph_objects as go
import streamlit as st

from lib import bench, cached, ui

ui.header(
    "Code optimization",
    "One small Python workload, rewritten and benchmarked live on this server: roll up hourly energy "
    "readings per rack. The baseline rescans every record once per rack. The optimized version makes "
    "one pass with dictionaries. Same input, same output",
    eyebrow="03 · Workstream B",
    tags=["measured"],
)

with st.form("bench", border=False):
    c = st.columns([1, 1, 1, 1], vertical_alignment="bottom")
    n = c[0].select_slider("Records", [5_000, 10_000, 20_000, 40_000], value=20_000)
    racks = c[1].select_slider("Racks", [50, 100, 200, 400], value=200)
    reps = c[2].select_slider("Timed runs", [3, 5, 7, 9], value=5)
    c[3].form_submit_button("Run benchmark", type="primary", width="stretch")

if "bench_run" not in st.session_state:
    st.session_state.bench_run = 0
r = cached.benchmark(n, racks, reps, st.session_state.bench_run)

b, o = r["baseline"], r["optimized"]
mb, mo = r["median_baseline"], r["median_optimized"]
cb, co = statistics.median(b["cpu"]), statistics.median(o["cpu"])
mem_change = (o["peak_bytes"] / b["peak_bytes"] - 1) * 100

ui.stats([
    ui.stat("Runtime, median", f"{mo * 1000:,.1f} ms",
            ui.delta(f"{(mo / mb - 1) * 100:.1f}%", f"vs {mb * 1000:,.0f} ms baseline", "good"), "measured", accent=True),
    ui.stat("CPU time, median", f"{co * 1000:,.1f} ms",
            ui.delta(f"{(co / cb - 1) * 100:.1f}%", f"vs {cb * 1000:,.0f} ms baseline", "good"), "measured"),
    ui.stat("Peak memory", f"{o['peak_bytes'] / 1024:,.0f} KB",
            ui.delta(f"{mem_change:+.0f}%", f"vs {b['peak_bytes'] / 1024:,.0f} KB baseline",
                     "bad" if mem_change > 0 else "good"), "measured"),
    ui.stat("Output check", "Identical" if r["equal"] else "Different",
            f"SHA-256 {r['digest_optimized']} on {r['racks_in_output']} racks", "measured"),
])
if not r["equal"]:
    st.error("Outputs differ. The optimization must not be accepted", icon=":material/error:")

left, right = st.columns([3, 2], gap="large")
with left:
    ui.section("Runtime per timed run", "Milliseconds per call, log scale. Each run repeats the call for at least 0.25 s and averages", "measured")
    runs = [f"Run {i}" for i in range(1, reps + 1)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=runs, y=[x * 1000 for x in b["wall"]], name="Baseline", marker_color=ui.GRAY_D,
                         hovertemplate="%{y:,.1f} ms"))
    fig.add_trace(go.Bar(x=runs, y=[x * 1000 for x in o["wall"]], name="Optimized", marker_color=ui.ACCENT,
                         hovertemplate="%{y:,.1f} ms"))
    fig.update_layout(barmode="group", bargap=0.35, bargroupgap=0.08)
    fig.update_yaxes(type="log", tickvals=[1, 3, 10, 30, 100, 300, 1000, 3000], ticksuffix=" ms")
    ui.chart(fig, 320)
with right:
    ui.section("The trade-off", "")
    st.html(f"""<dl class="gc-dl">
      <dt>Faster</dt><dd>{mb / mo:.0f}× less wall time, because each record is read once instead of once per rack</dd>
      <dt>Heavier</dt><dd>Peak memory rose {mem_change:.0f}%, since it keeps a running total for every rack at once</dd>
      <dt>Not energy</dt><dd>Runtime and CPU time are not electricity. Without a calibrated power meter they are not turned into kWh or rupees (report 8.4)</dd>
    </dl>""")
    if st.button("Measure again", icon=":material/refresh:",
                 help="Results are cached per setting. This forces a fresh measurement"):
        st.session_state.bench_run += 1
        st.rerun()

ui.section("Benchmark record", "So anyone can rerun it the same way")
env = {"Input": f"{r['n']:,} records, {r['n_racks']} racks, seed 7",
       "Runs": f"{r['repeats']} timed runs per version after one warm-up; each run repeats the call for ≥0.25 s "
            f"({min(b['calls'])}–{max(b['calls'])} baseline calls, {min(o['calls'])}–{max(o['calls'])} optimized calls per run)",
       **{k: str(v) for k, v in r["env"].items()},
       "Measured": f"{r['measured_at']:%d %b %Y, %H:%M:%S} UTC",
       "Timers": "time.perf_counter for wall time, time.process_time for CPU, tracemalloc in a separate run"}
st.html('<dl class="gc-dl">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in env.items()) + "</dl>")

c1, c2 = st.columns(2, gap="large")
with c1:
    ui.section("Baseline")
    st.code(inspect.getsource(bench.baseline_rollup), language="python")
with c2:
    ui.section("Optimized")
    st.code(inspect.getsource(bench.optimized_rollup), language="python")
