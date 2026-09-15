"""Shared helpers for experiment scripts: multi-seed runs, CSV/plot output."""

from __future__ import annotations

import copy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import yaml

from traffic_sim.metrics import compute_metrics
from traffic_sim.scenario import build_simulation

OUTPUT_DIR = Path(__file__).parent / "output"

# Categorical colors from the project's validated data-viz palette
# (references/palette.md, slots 1 and 2): baseline is blue, intervention
# is orange. Fixed order, never cycled -- these mean "baseline" and
# "intervention" everywhere in this project's plots.
COLOR_BASELINE = "#2a78d6"
COLOR_INTERVENTION = "#eb6834"
COLOR_TEXT = "#0b0b0b"
COLOR_TEXT_SECONDARY = "#52514e"


def load_cfg(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_many(cfg: dict, seeds: list[int]) -> pd.DataFrame:
    """Run the same scenario config across several seeds, return a metrics DataFrame."""
    rows = []
    for seed in seeds:
        cfg_run = copy.deepcopy(cfg)
        cfg_run["seed"] = seed
        sim = build_simulation(cfg_run)
        result = sim.run()
        row = compute_metrics(result).to_dict()
        row["seed"] = seed
        rows.append(row)
    return pd.DataFrame(rows)


def pct_reduction(baseline: float, intervention: float) -> float:
    """Percentage reduction from baseline to intervention (positive = improvement)."""
    if baseline == 0:
        return 0.0
    return (baseline - intervention) / baseline * 100.0


def summarize(baseline_df: pd.DataFrame, intervention_df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Mean baseline vs intervention for each metric, plus % reduction."""
    rows = []
    for metric in metrics:
        b = baseline_df[metric].mean()
        i = intervention_df[metric].mean()
        rows.append(
            {
                "metric": metric,
                "baseline_mean": b,
                "intervention_mean": i,
                "pct_reduction": pct_reduction(b, i),
            }
        )
    return pd.DataFrame(rows)


def plot_comparison_bars(
    summary: pd.DataFrame,
    metrics: list[str],
    titles: list[str],
    units: list[str],
    out_path: Path,
    suptitle: str,
) -> None:
    """Small-multiples bar chart: one subplot per metric, baseline vs
    intervention as two bars each (single y-axis per subplot -- never a
    dual-axis chart for the differently-scaled metrics)."""
    fig, axes = plt.subplots(1, len(metrics), figsize=(4.2 * len(metrics), 4.2))
    if len(metrics) == 1:
        axes = [axes]

    for ax, metric, title, unit in zip(axes, metrics, titles, units):
        row = summary[summary["metric"] == metric].iloc[0]
        values = [row["baseline_mean"], row["intervention_mean"]]
        colors = [COLOR_BASELINE, COLOR_INTERVENTION]
        bars = ax.bar(["Baseline", "Intervention"], values, color=colors, width=0.6)
        for bar, val in zip(bars, values):
            ax.annotate(
                f"{val:,.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                xytext=(0, 4),
                textcoords="offset points",
                ha="center",
                fontsize=9,
                color=COLOR_TEXT,
            )
        ax.set_title(f"{title}\n({row['pct_reduction']:.1f}% reduction)", fontsize=11, color=COLOR_TEXT)
        ax.set_ylabel(unit, fontsize=9, color=COLOR_TEXT_SECONDARY)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(colors=COLOR_TEXT_SECONDARY)
        ax.set_ylim(0, max(values) * 1.2 if max(values) > 0 else 1.0)

    fig.suptitle(suptitle, fontsize=13, color=COLOR_TEXT)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    OUTPUT_DIR.mkdir(exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
