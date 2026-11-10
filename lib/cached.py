"""Cached entry points so every page shares one run of the heavy work."""
import streamlit as st

from lib import bench, energy


@st.cache_resource(show_spinner="Generating synthetic telemetry and training models...")
def energy_pipeline():
    return energy.run_pipeline()


@st.cache_data(show_spinner="Running anomaly detection...")
def anomalies(k: float, period: str):
    p = energy_pipeline()
    return energy.detect(p["scores"], k, p["events"], period)


@st.cache_data(show_spinner="Benchmarking baseline vs optimized code...")
def benchmark(n: int, n_racks: int, repeats: int, run_id: int = 0):
    return bench.run_benchmark(n, n_racks, repeats)
