"""Aggregate metrics computed from a completed simulation run."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .simulation import SimulationResult
from .vehicle import Vehicle


@dataclass
class Metrics:
    n_completed: int
    n_active: int
    total_travel_time_s: float
    avg_speed_mps: float
    avg_speed_kmh: float
    total_stops: int
    avg_stops_per_vehicle: float
    total_distance_km: float
    total_co2_g: float
    total_nox_g: float
    co2_g_per_km: float
    nox_g_per_km: float
    throughput_veh_per_hour: float

    def to_dict(self) -> dict:
        return asdict(self)


def _all_vehicles(result: SimulationResult) -> list[Vehicle]:
    return list(result.completed) + list(result.active)


def compute_metrics(result: SimulationResult) -> Metrics:
    """Compute summary metrics from a :class:`SimulationResult`.

    Travel-time and average-speed metrics only use vehicles that
    completed their trip (a well-defined arrival time). Emissions,
    distance and stop counts are accumulated over *every* vehicle that
    existed during the run, including ones still in transit at the end,
    since they emitted and moved regardless of whether they finished.
    """
    completed = list(result.completed)
    all_vehicles = _all_vehicles(result)

    total_travel_time = sum(
        (v.arrival_time - v.depart_time) for v in completed if v.arrival_time is not None
    )
    total_completed_distance = sum(v.distance_travelled for v in completed)

    # Space-mean speed: total distance / total time, the standard
    # traffic-engineering definition (as opposed to averaging individual
    # vehicle speeds, which would be biased by slow vehicles spending more
    # time in the sample).
    avg_speed_mps = (
        total_completed_distance / total_travel_time if total_travel_time > 0 else 0.0
    )

    total_stops = sum(v.stop_count for v in all_vehicles)
    total_distance_km = sum(v.distance_travelled for v in all_vehicles) / 1000.0
    total_co2_g = sum(v.cum_co2_g for v in all_vehicles)
    total_nox_g = sum(v.cum_nox_g for v in all_vehicles)

    duration_hours = result.duration / 3600.0

    return Metrics(
        n_completed=len(completed),
        n_active=len(result.active),
        total_travel_time_s=total_travel_time,
        avg_speed_mps=avg_speed_mps,
        avg_speed_kmh=avg_speed_mps * 3.6,
        total_stops=total_stops,
        avg_stops_per_vehicle=(total_stops / len(all_vehicles)) if all_vehicles else 0.0,
        total_distance_km=total_distance_km,
        total_co2_g=total_co2_g,
        total_nox_g=total_nox_g,
        co2_g_per_km=(total_co2_g / total_distance_km) if total_distance_km > 0 else 0.0,
        nox_g_per_km=(total_nox_g / total_distance_km) if total_distance_km > 0 else 0.0,
        throughput_veh_per_hour=(len(completed) / duration_hours) if duration_hours > 0 else 0.0,
    )
