"""Unit tests for metrics aggregation.

These construct :class:`Vehicle`/:class:`SimulationResult` objects
directly (rather than running a full simulation) so the arithmetic in
``compute_metrics`` is tested in isolation with known expected values.
"""

from __future__ import annotations

from traffic_sim.metrics import compute_metrics
from traffic_sim.simulation import SimulationConfig, SimulationResult
from traffic_sim.vehicle import Vehicle


def _vehicle(**kwargs) -> Vehicle:
    defaults = dict(id=0, lane=0, position=0.0, speed=0.0)
    defaults.update(kwargs)
    return Vehicle(**defaults)


def test_total_travel_time_sums_completed_vehicles():
    v1 = _vehicle(id=1, depart_time=0.0, arrival_time=100.0, distance_travelled=1000.0)
    v2 = _vehicle(id=2, depart_time=10.0, arrival_time=160.0, distance_travelled=1000.0)
    result = SimulationResult(
        completed=[v1, v2], active=[], duration=200.0, network_length=1000.0,
        config=SimulationConfig(),
    )
    m = compute_metrics(result)
    assert m.total_travel_time_s == 100.0 + 150.0
    assert m.n_completed == 2
    assert m.n_active == 0


def test_avg_speed_is_space_mean_speed():
    # 1000 m in 100 s = 10 m/s.
    v1 = _vehicle(id=1, depart_time=0.0, arrival_time=100.0, distance_travelled=1000.0)
    result = SimulationResult(
        completed=[v1], active=[], duration=100.0, network_length=1000.0,
        config=SimulationConfig(),
    )
    m = compute_metrics(result)
    assert m.avg_speed_mps == 10.0
    assert m.avg_speed_kmh == 36.0


def test_avg_speed_zero_when_no_completed_vehicles():
    result = SimulationResult(
        completed=[], active=[], duration=100.0, network_length=1000.0,
        config=SimulationConfig(),
    )
    m = compute_metrics(result)
    assert m.avg_speed_mps == 0.0
    assert m.n_completed == 0


def test_stops_and_emissions_include_active_vehicles():
    completed = _vehicle(
        id=1, depart_time=0.0, arrival_time=50.0, distance_travelled=500.0,
        stop_count=2, cum_co2_g=100.0, cum_nox_g=1.0,
    )
    active = _vehicle(
        id=2, distance_travelled=200.0, stop_count=1, cum_co2_g=40.0, cum_nox_g=0.5,
    )
    result = SimulationResult(
        completed=[completed], active=[active], duration=50.0, network_length=1000.0,
        config=SimulationConfig(),
    )
    m = compute_metrics(result)
    assert m.total_stops == 3
    assert m.total_co2_g == 140.0
    assert m.total_nox_g == 1.5
    assert m.n_active == 1


def test_emissions_per_km_computed_from_total_distance():
    v1 = _vehicle(
        id=1, depart_time=0.0, arrival_time=100.0, distance_travelled=2000.0,
        cum_co2_g=400.0, cum_nox_g=2.0,
    )
    result = SimulationResult(
        completed=[v1], active=[], duration=100.0, network_length=2000.0,
        config=SimulationConfig(),
    )
    m = compute_metrics(result)
    assert m.total_distance_km == 2.0
    assert m.co2_g_per_km == 200.0
    assert m.nox_g_per_km == 1.0


def test_throughput_veh_per_hour():
    vehicles = [
        _vehicle(id=i, depart_time=0.0, arrival_time=10.0, distance_travelled=100.0)
        for i in range(5)
    ]
    result = SimulationResult(
        completed=vehicles, active=[], duration=3600.0 / 10, network_length=1000.0,
        config=SimulationConfig(),
    )
    m = compute_metrics(result)
    # 5 vehicles completed over 1/10th of an hour -> 50 veh/hour.
    assert m.throughput_veh_per_hour == 50.0


def test_metrics_to_dict_roundtrips_all_fields():
    result = SimulationResult(
        completed=[], active=[], duration=1.0, network_length=None, config=SimulationConfig()
    )
    m = compute_metrics(result)
    d = m.to_dict()
    assert set(d.keys()) == set(m.__dataclass_fields__.keys())
