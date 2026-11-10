"""Code-optimization workstream: a small deterministic workload, benchmarked live.

Task: roll up hourly energy readings per rack (total kWh, reading count, mean
kWh, peak hour). The baseline rescans every record once per rack; the optimized
version makes a single pass. Both add the same numbers in the same order, so
outputs must match exactly.

Results are runtime, CPU time and memory on whatever machine runs this app.
They are NOT converted to kWh or rupees (report section 8.4).
"""
from __future__ import annotations

import hashlib
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from collections import defaultdict
from datetime import datetime, timezone

MIN_RUN_S = 0.25  # each timed run lasts at least this long


def make_records(n: int, n_racks: int, seed: int = 7):
    rng = random.Random(seed)
    return [(f"R{rng.randrange(n_racks):03d}", rng.randrange(24), round(rng.uniform(0.5, 9.5), 3))
            for _ in range(n)]


def baseline_rollup(records):
    racks = []
    for rack_id, _, _ in records:
        if rack_id not in racks:          # list membership: slow lookup
            racks.append(rack_id)
    racks.sort()
    out = {}
    for rack in racks:
        total, count, hourly = 0.0, 0, [0.0] * 24
        for rack_id, hour, kwh in records:  # rescans all records for every rack
            if rack_id == rack:
                total += kwh
                count += 1
                hourly[hour] += kwh
        out[rack] = (round(total, 6), count, round(total / count, 6), hourly.index(max(hourly)))
    return out


def optimized_rollup(records):
    totals = defaultdict(float)
    counts = defaultdict(int)
    hourly = defaultdict(lambda: [0.0] * 24)
    for rack_id, hour, kwh in records:      # one pass, dictionary lookups
        totals[rack_id] += kwh
        counts[rack_id] += 1
        hourly[rack_id][hour] += kwh
    return {rack: (round(totals[rack], 6), counts[rack], round(totals[rack] / counts[rack], 6),
                   hourly[rack].index(max(hourly[rack])))
            for rack in sorted(totals)}


def _digest(result) -> str:
    return hashlib.sha256(repr(result).encode()).hexdigest()[:16]


def _time_runs(fn, records, repeats):
    wall, cpu = [], []
    # The CPU clock ticks every ~16 ms on Windows, so each timed run repeats the call
    # until at least MIN_RUN_S has passed and reports the per-call average.
    calls = []
    for _ in range(repeats):
        n = 0
        w0, c0 = time.perf_counter(), time.process_time()
        while True:
            fn(records)
            n += 1
            if time.perf_counter() - w0 >= MIN_RUN_S:
                break
        wall.append((time.perf_counter() - w0) / n)
        cpu.append((time.process_time() - c0) / n)
        calls.append(n)
    return wall, cpu, calls


def _peak_memory(fn, records):
    tracemalloc.start()
    fn(records)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def run_benchmark(n: int = 20_000, n_racks: int = 200, repeats: int = 5) -> dict:
    records = make_records(n, n_racks)
    base_out, opt_out = baseline_rollup(records), optimized_rollup(records)  # also warm-up
    b_wall, b_cpu, b_calls = _time_runs(baseline_rollup, records, repeats)
    o_wall, o_cpu, o_calls = _time_runs(optimized_rollup, records, repeats)
    return {
        "n": n, "n_racks": n_racks, "repeats": repeats,
        "baseline": {"wall": b_wall, "cpu": b_cpu, "calls": b_calls,
                     "peak_bytes": _peak_memory(baseline_rollup, records)},
        "optimized": {"wall": o_wall, "cpu": o_cpu, "calls": o_calls,
                      "peak_bytes": _peak_memory(optimized_rollup, records)},
        "equal": base_out == opt_out,
        "digest_baseline": _digest(base_out), "digest_optimized": _digest(opt_out),
        "racks_in_output": len(opt_out),
        "median_baseline": statistics.median(b_wall),
        "median_optimized": statistics.median(o_wall),
        "env": {
            "Python": sys.version.split()[0],
            "Platform": platform.platform(),
            "Machine": platform.machine() or "unknown",
            "Logical CPUs": os.cpu_count(),
        },
        "measured_at": datetime.now(timezone.utc),
    }
