"""Experiment 2: ramp metering vs uncontrolled on-ramp merging.

Runs the same motorway-style corridor with an on-ramp under two policies:

  * baseline  -- ramp vehicles merge as soon as a gap is available, with
                 no control on the release rate (bursts of ramp demand
                 can force mainline traffic to brake hard).
  * metering  -- a ramp signal caps the release rate, spreading merges
                 out and smoothing the mainline flow.

across several random seeds, then reports the change in CO2/NOx
emissions, stop-start counts and travel time, and writes a CSV +
comparison plot to experiments/output/.

Run with: python experiments/exp2_ramp_metering.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from common import OUTPUT_DIR, load_cfg, plot_comparison_bars, run_many, summarize

SCENARIOS_DIR = Path(__file__).parent / "scenarios"
SEEDS = [1, 2, 3, 4, 5, 6, 7, 8]

METRICS = ["total_co2_g", "total_nox_g", "total_stops"]
TITLES = ["Total CO2", "Total NOx", "Total stops"]
UNITS = ["grams", "grams", "count"]


def main() -> None:
    baseline_cfg = load_cfg(SCENARIOS_DIR / "ramp_baseline.yaml")
    metering_cfg = load_cfg(SCENARIOS_DIR / "ramp_metering.yaml")

    print(f"Running uncontrolled ramp merge ({len(SEEDS)} seeds)...")
    baseline_df = run_many(baseline_cfg, SEEDS)
    baseline_df["policy"] = "baseline"

    print(f"Running ramp metering ({len(SEEDS)} seeds)...")
    metering_df = run_many(metering_cfg, SEEDS)
    metering_df["policy"] = "ramp_metering"

    combined = pd.concat([baseline_df, metering_df], ignore_index=True)

    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / "exp2_ramp_metering_results.csv"
    combined.to_csv(csv_path, index=False)
    print(f"Wrote per-seed results to {csv_path}")

    summary = summarize(baseline_df, metering_df, METRICS + ["avg_speed_kmh", "total_travel_time_s"])
    summary_path = OUTPUT_DIR / "exp2_ramp_metering_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Wrote summary to {summary_path}\n")
    print(summary.to_string(index=False))

    plot_path = OUTPUT_DIR / "exp2_ramp_metering.png"
    plot_comparison_bars(
        summary,
        METRICS,
        TITLES,
        UNITS,
        plot_path,
        suptitle="Ramp metering vs uncontrolled on-ramp merging",
    )
    print(f"\nWrote plot to {plot_path}")


if __name__ == "__main__":
    main()
