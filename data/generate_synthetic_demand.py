#!/usr/bin/env python3
"""Generate a synthetic diurnal traffic demand profile.

Produces a CSV of vehicle demand (veh/hour) over a 24-hour period with a
morning and evening peak and an inter-peak trough, loosely shaped like
typical UK urban traffic counts (see data/README.md for the real
datasets this is a placeholder for). This is synthetic data generation
only -- no real traffic data is fetched or used.

Usage:
    python data/generate_synthetic_demand.py --out data/synthetic/demand_profile.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def _gaussian_bump(hours: np.ndarray, centre: float, width: float, height: float) -> np.ndarray:
    return height * np.exp(-0.5 * ((hours - centre) / width) ** 2)


def generate_demand_profile(
    resolution_minutes: int = 15,
    base_demand_veh_per_hour: float = 150.0,
    am_peak_hour: float = 8.0,
    pm_peak_hour: float = 17.5,
    am_peak_height: float = 700.0,
    pm_peak_height: float = 850.0,
    peak_width_hours: float = 1.1,
    noise_std_veh_per_hour: float = 25.0,
    seed: int = 0,
) -> pd.DataFrame:
    """Build a 24h synthetic demand profile as a DataFrame.

    Columns: ``hour`` (0-24, exclusive of 24), ``demand_veh_per_hour``.
    """
    rng = np.random.default_rng(seed)
    n_steps = int(24 * 60 / resolution_minutes)
    hours = np.arange(n_steps) * (resolution_minutes / 60.0)

    demand = (
        base_demand_veh_per_hour
        + _gaussian_bump(hours, am_peak_hour, peak_width_hours, am_peak_height)
        + _gaussian_bump(hours, pm_peak_hour, peak_width_hours, pm_peak_height)
    )
    demand += rng.normal(0.0, noise_std_veh_per_hour, size=n_steps)
    demand = np.clip(demand, 0.0, None)

    return pd.DataFrame({"hour": hours, "demand_veh_per_hour": demand})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic/demand_profile.csv"))
    parser.add_argument("--resolution-minutes", type=int, default=15)
    parser.add_argument("--base-demand", type=float, default=150.0)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    df = generate_demand_profile(
        resolution_minutes=args.resolution_minutes,
        base_demand_veh_per_hour=args.base_demand,
        seed=args.seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out}")


if __name__ == "__main__":
    main()
