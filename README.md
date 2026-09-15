# Reducing UK vehicle emissions by optimising traffic flow

A microscopic traffic simulation harness for researching how smoothing
traffic flow -- reducing stop-start driving through better signal timing,
ramp metering, and coordinated ("platooned") movement -- can reduce road
transport CO2 and NOx emissions on UK-style corridors and junctions.

## Motivation

Stop-start driving is disproportionately polluting: hard acceleration
after a stop demands much more instantaneous engine power (and produces
much more NOx) than the same average speed achieved smoothly, and every
full stop pays an "idle-to-cruise" energy penalty that a vehicle gliding
through at a lower, steadier speed never pays. Traffic engineering
interventions that reduce the *number and severity* of stop-start events
-- without necessarily changing average journey speed much, or even
while slightly reducing it -- are a comparatively cheap lever on
transport emissions relative to fleet electrification or demand
reduction, and are broadly applicable to the UK's existing signalised
urban corridors, motorway ramps, and roundabouts.

This project builds a standalone (no external simulator required)
microscopic traffic simulator with an emissions model attached, so that
candidate interventions -- green wave signal coordination, variable
speed limits, ramp metering -- can be compared against a matched
baseline under identical demand, and the emissions/stop-count/travel-time
trade-off quantified.

## Architecture

```
src/traffic_sim/
    idm.py            Intelligent Driver Model (car-following)
    lane_change.py     Gap-acceptance merge model (ramp / roundabout entry)
    vehicle.py         Per-vehicle state (position, speed, emissions, stops)
    signals.py         Fixed-time traffic signals + green-wave offset calculation
    network.py         Road topology: CorridorNetwork, RoundaboutNetwork
    emissions.py       Instantaneous CO2/NOx emissions model
    simulation.py      The time-stepping simulation engine
    metrics.py         Aggregate metrics from a simulation run
    scenario.py        YAML scenario config -> Simulation
    sumo_stub.py        Optional, off-by-default SUMO/TraCI integration path

experiments/
    common.py                     Shared multi-seed run / CSV / plot helpers
    exp1_green_wave.py             Green wave vs uncoordinated signals
    exp2_ramp_metering.py          Ramp metering vs uncontrolled merging
    scenarios/*.yaml                Scenario configs used by the above
    output/                        CSV + PNG results (generated, gitignored)

data/
    README.md                      Plan for ingesting real UK datasets
    generate_synthetic_demand.py   Synthetic diurnal demand generator

tests/                              pytest unit tests for idm/emissions/metrics/etc.
```

### Simulation core

The engine is a single-lane microscopic car-following simulation built
on the **Intelligent Driver Model** (Treiber, Hennecke & Helbing, 2000),
which gives each vehicle a smooth, collision-free acceleration as a
function of its own speed, its speed difference to the vehicle (or red
light) ahead, and the gap between them. Traffic signals are modelled as
virtual stationary vehicles at the stop line while red, so the same
car-following logic naturally produces queuing and dissipation at
junctions. Ramp and roundabout-entry merging uses a simple
gap-acceptance model (`lane_change.py`): a vehicle waiting to merge needs
an acceptable gap both ahead and behind, where "acceptable" grows with
closing speed.

This is pure Python/numpy and has no dependency on SUMO. An optional,
off-by-default SUMO/TraCI integration stub (`sumo_stub.py`) is included
as a placeholder for later work that might want SUMO's richer network
import or emission classes -- it is never imported by default and SUMO
does not need to be installed to use anything else in this repository.

### Emissions model

`emissions.py` computes instantaneous CO2 and NOx emission rates (g/s)
from each vehicle's speed and acceleration at every simulation step,
using a small polynomial model: an idle term, a cruise term (rolling
resistance + aerodynamic drag, dominated by a cubic-in-speed term), and
an acceleration term that only applies during positive acceleration --
this last term is what makes stop-start driving disproportionately
polluting in the model, matching the real-world mechanism it represents.

**The coefficients are explicitly-documented placeholders**, chosen for
plausible order of magnitude and shape (loosely inspired by COPERT's
hot-emission curve shape and VSP/VT-Micro-style acceleration
sensitivity), not calibrated to real vehicles. See the module docstring
in `emissions.py` and `data/README.md` for the real UK data (NAEI/DEFRA
emission factors) that should replace them before drawing real-world
conclusions.

### Scenario configuration

Scenarios are YAML files (see `experiments/scenarios/*.yaml`) describing
a network topology (`corridor` or `roundabout`), IDM driver parameters,
demand rates, and the intervention under test (signal plan / green wave
on/off, on-ramp presence/metering, variable speed limit zones).
`traffic_sim.scenario.load_scenario()` turns one of these files into a
ready-to-run `Simulation`.

## Running the experiments

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python experiments/exp1_green_wave.py
python experiments/exp2_ramp_metering.py
```

Each script runs baseline and intervention policies across several
random seeds, prints a summary table, and writes to `experiments/output/`:
a per-seed results CSV, a summary CSV (mean baseline vs intervention and
% reduction per metric), and a comparison PNG plot.

Indicative results from this repository's default scenarios (illustrative,
not calibrated -- see emissions model caveat above):

| Experiment | CO2 | NOx | Stops |
|---|---|---|---|
| Green wave signals vs uncoordinated | ~6% lower | ~14% lower | ~8% fewer |
| Ramp metering vs uncontrolled merge | ~1% lower | ~18% lower | ~90% fewer |

## Running the tests

```bash
pip install -e ".[dev]"
pytest
```

Tests cover the IDM car-following model, the emissions function, the
metrics aggregation, the gap-acceptance merge model, and end-to-end
simulation behaviour (signals causing stops, green wave reducing stops
vs baseline, ramp metering bounding the merge rate, roundabout
throughput).

## Known simplifications

- Single lane per direction (no overtaking/multi-lane discretionary lane
  changes; only ramp/roundabout-entry merging).
- The roundabout topology is a simplified single-entry ring; a
  multi-arm roundabout is future work.
- Emission factors are illustrative placeholders (see above).
- Demand is a flat-rate Poisson-ish arrival process per scenario; the
  synthetic diurnal profile generator in `data/generate_synthetic_demand.py`
  is a first step toward time-varying demand but isn't yet wired into
  the simulation engine.
