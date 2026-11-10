# Design brief (the prompt this dashboard is built against)

**Product.** A consulting dashboard that tests whether AI can cut a data centre's energy and compute waste, with every figure tagged by how real it is.

**Character.** Exact, sober, instrument-like.

**World.** A data-centre control room on a night shift: meters, rack telemetry, hairline panels.

**Moments.** (1) The forecast chart: observed power vs the ML forecast and its 90% band. (2) The alert log read as a ranked list with severity dots.

**Signature.** The provenance tag: a small dot plus a mono word (`synthetic`, `measured`, `projected`, `report`) next to every figure. Used everywhere a number appears, nowhere else.

## Rules
- Graphite dark ramp: page `#141415`, sidebar `#0f0f10`, card `#19191b`, raised `#232325`, hairline = text at 8%.
- Text roles: primary `#ededed`, secondary `#a1a1a6`, muted `#85858b`.
- One accent, GreenCompute green `#46c28e`: primary action, the lead series in each chart, key figures. Nothing else is green except "good" states.
- Charts: one accent per chart. Baselines and context series are grey (`#8e8e93`, `#5b5b60`), dashed when they are a comparison. Muted mono tick labels, hairline grid, no chart titles inside the plot (titles are HTML above it).
- Type: Geist for the interface, Geist Mono for figures, timestamps and meta. Weights 400/500, 600 only for the wordmark. Sentence case. No uppercase tracked labels.
- Spacing on a 4px grid. Cards 20px padding, radius 12. Controls radius 8.
- Severity: High `#e5484d`, Medium `#e0a43a`, Low `#85858b`, always with a word, never colour alone.
- Copy: short, plain, no trailing periods on labels, every change says what it compares to.
- Motion: none beyond Streamlit defaults.

Method credit: unslop by Damir Sokolovsky (@heydamir), CC BY 4.0.
