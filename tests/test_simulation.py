"""Integration-level tests for the simulation engine.

These exercise the IDM + signals + emissions + metrics pipeline together,
checking qualitative behaviour we know must hold (vehicles progress
forward, red lights cause stops, green-wave coordination reduces stops
relative to an uncoordinated baseline with the same demand/seed).
"""

from __future__ import annotations

from traffic_sim.idm import IDMParams
from traffic_sim.metrics import compute_metrics
from traffic_sim.network import CorridorNetwork, OnRamp, RoundaboutNetwork
from traffic_sim.signals import build_signals
from traffic_sim.simulation import Simulation, SimulationConfig


def _corridor_config(seed: int = 1, demand: float = 900.0) -> SimulationConfig:
    return SimulationConfig(
        dt=0.5,
        duration=900.0,
        mainline_demand_veh_per_hour=demand,
        idm_params=IDMParams(v0=13.9, T=1.5, a_max=1.4, b=2.0, s0=2.0),
        seed=seed,
    )


def test_vehicles_progress_and_complete_on_a_free_corridor():
    net = CorridorNetwork(length=1000.0, base_speed_limit=13.9)
    sim = Simulation(net, _corridor_config())
    result = sim.run()
    assert len(result.completed) > 0
    for v in result.completed:
        assert v.arrival_time is not None
        assert v.arrival_time > v.depart_time
        assert v.distance_travelled >= 1000.0


def test_red_signal_causes_vehicles_to_stop():
    # A signal with a very short green window will force queuing.
    signals = build_signals([500.0], cycle_time=120.0, green_time=10.0, green_wave=False)
    net = CorridorNetwork(length=1000.0, base_speed_limit=13.9, signals=signals)
    sim = Simulation(net, _corridor_config(demand=1200.0))
    result = sim.run()
    m = compute_metrics(result)
    assert m.total_stops > 0


def test_no_signals_means_no_forced_stops_on_light_demand():
    net = CorridorNetwork(length=1000.0, base_speed_limit=13.9)
    sim = Simulation(net, _corridor_config(demand=200.0))
    result = sim.run()
    m = compute_metrics(result)
    assert m.total_stops == 0


def test_green_wave_reduces_stops_vs_uncoordinated_baseline():
    positions = [400.0, 900.0, 1400.0]
    progression_speed = 13.9

    baseline_signals = build_signals(
        positions, cycle_time=60.0, green_time=25.0, green_wave=False
    )
    green_wave_signals = build_signals(
        positions,
        cycle_time=60.0,
        green_time=25.0,
        green_wave=True,
        progression_speed=progression_speed,
    )

    baseline_net = CorridorNetwork(length=1800.0, base_speed_limit=13.9, signals=baseline_signals)
    green_wave_net = CorridorNetwork(
        length=1800.0, base_speed_limit=13.9, signals=green_wave_signals
    )

    baseline_result = Simulation(baseline_net, _corridor_config(seed=7)).run()
    green_wave_result = Simulation(green_wave_net, _corridor_config(seed=7)).run()

    baseline_metrics = compute_metrics(baseline_result)
    green_wave_metrics = compute_metrics(green_wave_result)

    assert green_wave_metrics.total_stops < baseline_metrics.total_stops


def test_ramp_metering_bounds_release_rate():
    on_ramp = OnRamp(
        merge_position=500.0,
        demand_veh_per_hour=1800.0,
        metering=True,
        metering_rate_veh_per_hour=300.0,
    )
    net = CorridorNetwork(length=1000.0, base_speed_limit=13.9, on_ramp=on_ramp)
    sim = Simulation(net, _corridor_config(demand=0.0))
    result = sim.run()
    # Over 900s at a 300 veh/h cap, at most 300/3600*900 = 75 releases can
    # have made it onto the mainline (completed + still on it).
    on_mainline_or_completed = len(result.completed) + len(sim.vehicles)
    assert on_mainline_or_completed <= 80  # small slack for boundary effects


def test_roundabout_vehicles_enter_circulate_and_exit():
    net = RoundaboutNetwork(circumference=250.0, entry_demand_veh_per_hour=500.0)
    config = SimulationConfig(dt=0.5, duration=600.0, mainline_demand_veh_per_hour=0.0, seed=3)
    sim = Simulation(net, config)
    result = sim.run()
    assert len(result.completed) > 0
    for v in result.completed:
        assert v.distance_travelled > 0.0
        assert v.arrival_time is not None


def test_simulation_result_metrics_are_internally_consistent():
    net = CorridorNetwork(length=1000.0, base_speed_limit=13.9)
    sim = Simulation(net, _corridor_config())
    result = sim.run()
    m = compute_metrics(result)
    assert m.n_completed == len(result.completed)
    assert m.total_co2_g >= 0.0
    assert m.total_nox_g >= 0.0
    assert m.co2_g_per_km > 0.0
