"""YAML scenario configuration loader.

Turns a scenario YAML file into a ready-to-run :class:`~traffic_sim.simulation.Simulation`.
See ``experiments/scenarios/*.yaml`` for example files and
``docs``/README for the schema; the short version:

```yaml
name: corridor_baseline
topology: corridor            # corridor | roundabout
seed: 1
dt: 0.5
duration: 1200

demand:
  mainline_veh_per_hour: 900

idm:
  v0_kmh: 50
  T: 1.5
  a_max: 1.4
  b: 2.0
  delta: 4.0
  s0: 2.0

corridor:                      # present when topology: corridor
  length: 2000
  base_speed_limit_kmh: 50
  green_wave: false
  progression_speed_kmh: 50
  signals:
    - {position: 500, cycle_time: 60, green_time: 30}
  speed_limit_zones:            # optional variable speed limit intervention
    - {start: 400, end: 600, speed_limit_kmh: 30}
  on_ramp:                      # optional
    merge_position: 800
    demand_veh_per_hour: 300
    metering: false
    metering_rate_veh_per_hour: 400

roundabout:                     # present when topology: roundabout
  circumference: 300
  base_speed_limit_kmh: 30
  entry_position: 0
  entry_demand_veh_per_hour: 300
  exit_arc_range: [60, 220]
```
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .idm import IDMParams
from .lane_change import MergeParams
from .network import CorridorNetwork, OnRamp, RoundaboutNetwork, SpeedLimitZone
from .signals import build_signals
from .simulation import Simulation, SimulationConfig

KMH_TO_MPS = 1.0 / 3.6


def _build_idm_params(cfg: dict[str, Any]) -> IDMParams:
    return IDMParams(
        v0=cfg.get("v0_kmh", 50.0) * KMH_TO_MPS,
        T=cfg.get("T", 1.5),
        a_max=cfg.get("a_max", 1.4),
        b=cfg.get("b", 2.0),
        delta=cfg.get("delta", 4.0),
        s0=cfg.get("s0", 2.0),
    )


def _build_corridor(cfg: dict[str, Any]) -> CorridorNetwork:
    signal_positions = [s["position"] for s in cfg.get("signals", [])]
    green_wave = cfg.get("green_wave", False)
    progression_speed = cfg.get("progression_speed_kmh", 50.0) * KMH_TO_MPS

    signals = []
    if cfg.get("signals"):
        cycle_time = cfg["signals"][0].get("cycle_time", 60.0)
        green_time = cfg["signals"][0].get("green_time", 30.0)
        signals = build_signals(
            signal_positions,
            cycle_time=cycle_time,
            green_time=green_time,
            green_wave=green_wave,
            progression_speed=progression_speed,
        )

    zones = [
        SpeedLimitZone(
            start=z["start"], end=z["end"], speed_limit=z["speed_limit_kmh"] * KMH_TO_MPS
        )
        for z in cfg.get("speed_limit_zones", []) or []
    ]

    on_ramp_cfg = cfg.get("on_ramp")
    on_ramp = (
        OnRamp(
            merge_position=on_ramp_cfg["merge_position"],
            demand_veh_per_hour=on_ramp_cfg.get("demand_veh_per_hour", 300.0),
            metering=on_ramp_cfg.get("metering", False),
            metering_rate_veh_per_hour=on_ramp_cfg.get("metering_rate_veh_per_hour", 400.0),
        )
        if on_ramp_cfg
        else None
    )

    return CorridorNetwork(
        length=cfg["length"],
        base_speed_limit=cfg.get("base_speed_limit_kmh", 50.0) * KMH_TO_MPS,
        signals=signals,
        speed_limit_zones=zones,
        on_ramp=on_ramp,
    )


def _build_roundabout(cfg: dict[str, Any]) -> RoundaboutNetwork:
    low, high = cfg.get("exit_arc_range", [60.0, 220.0])
    return RoundaboutNetwork(
        circumference=cfg["circumference"],
        base_speed_limit=cfg.get("base_speed_limit_kmh", 30.0) * KMH_TO_MPS,
        entry_position=cfg.get("entry_position", 0.0),
        exit_arc_range=(low, high),
        entry_demand_veh_per_hour=cfg.get("entry_demand_veh_per_hour", 300.0),
    )


def build_simulation(cfg: dict[str, Any]) -> Simulation:
    """Build a :class:`Simulation` from a parsed scenario dict."""
    topology = cfg["topology"]
    if topology == "corridor":
        network = _build_corridor(cfg["corridor"])
    elif topology == "roundabout":
        network = _build_roundabout(cfg["roundabout"])
    else:
        raise ValueError(f"Unknown topology: {topology!r}")

    idm_params = _build_idm_params(cfg.get("idm", {}))
    demand_cfg = cfg.get("demand", {})

    sim_config = SimulationConfig(
        dt=cfg.get("dt", 0.5),
        duration=cfg.get("duration", 1200.0),
        mainline_demand_veh_per_hour=demand_cfg.get("mainline_veh_per_hour", 900.0),
        idm_params=idm_params,
        merge_params=MergeParams(),
        seed=cfg.get("seed", 0),
    )
    return Simulation(network=network, config=sim_config)


def load_scenario(path: str | Path) -> Simulation:
    """Load a scenario YAML file and build the corresponding Simulation."""
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return build_simulation(cfg)
