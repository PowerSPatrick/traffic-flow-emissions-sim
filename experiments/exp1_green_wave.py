"""Experiment 1: green-wave signal coordination vs uncoordinated signals.

Runs the same signalised urban corridor under two policies:

  * baseline      -- three fixed-time signals, all with offset 0 (no
                     coordination between them).
  * green_wave    -- the same three signals, offsets coordinated so a
                     platoon travelling at the design speed rides a
                     "green wave" through all of them.

across several random seeds (to average out demand-arrival noise), then
reports the change in CO2/NOx emissions, stop-start counts and travel
time, and writes a CSV + comparison plot to experiments/output/.

Run with: python experiments/exp1_green_wave.py
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
    baseline_cfg = load_cfg(SCENARIOS_DIR / "corridor_baseline.yaml")
    green_wave_cfg = load_cfg(SCENARIOS_DIR / "corridor_green_wave.yaml")

    print(f"Running baseline ({len(SEEDS)} seeds)...")
    baseline_df = run_many(baseline_cfg, SEEDS)
    baseline_df["policy"] = "baseline"

    print(f"Running green wave ({len(SEEDS)} seeds)...")
    green_wave_df = run_many(green_wave_cfg, SEEDS)
    green_wave_df["policy"] = "green_wave"

    combined = pd.concat([baseline_df, green_wave_df], ignore_index=True)

    OUTPUT_DIR.mkdir(exist_ok=True)
    csv_path = OUTPUT_DIR / "exp1_green_wave_results.csv"
    combined.to_csv(csv_path, index=False)
    print(f"Wrote per-seed results to {csv_path}")

    summary = summarize(baseline_df, green_wave_df, METRICS + ["avg_speed_kmh", "total_travel_time_s"])
    summary_path = OUTPUT_DIR / "exp1_green_wave_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Wrote summary to {summary_path}\n")
    print(summary.to_string(index=False))

    plot_path = OUTPUT_DIR / "exp1_green_wave.png"
    plot_comparison_bars(
        summary,
        METRICS,
        TITLES,
        UNITS,
        plot_path,
        suptitle="Green wave signal coordination vs uncoordinated baseline",
    )
    print(f"\nWrote plot to {plot_path}")


if __name__ == "__main__":
    main()
