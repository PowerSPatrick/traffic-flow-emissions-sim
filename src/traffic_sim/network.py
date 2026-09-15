"""Road network topology definitions.

Three topologies are supported, matching the scenarios used in the
experiments:

  * :class:`CorridorNetwork` -- a straight single-lane corridor, optionally
    with one or more signalised junctions, variable speed limit zones, and
    a single on-ramp merge.
  * :class:`RoundaboutNetwork` -- a simplified single-entry roundabout: a
    circular circulating lane (position wraps modulo the circumference)
    fed by one approach arm whose traffic must gap-accept into the
    circulating flow, exactly like an on-ramp merge but on a ring road.
    Vehicles exit after travelling a (randomly drawn) arc length,
    representing different drivers taking different exits.

Both topologies are deliberately simple (single lane) so that the
travel-time / stop-count / emissions comparisons between baseline and
intervention policies are easy to attribute to the policy change rather
than to lane-changing noise. A basic lane-changing/merge model exists
(:mod:`traffic_sim.lane_change`) and is exercised by the on-ramp / entry
logic in :mod:`traffic_sim.simulation`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .signals import TrafficSignal


@dataclass(frozen=True)
class SpeedLimitZone:
    """A variable speed limit zone (a common ramp-metering-adjacent
    intervention: temporarily lowering the speed limit upstream of a
    bottleneck smooths inflow and can prevent breakdown into stop-and-go
    traffic)."""

    start: float   # m
    end: float     # m
    speed_limit: float  # m/s


@dataclass(frozen=True)
class OnRamp:
    """An on-ramp merging into the mainline at ``merge_position``."""

    merge_position: float  # m along the mainline
    demand_veh_per_hour: float = 300.0
    metering: bool = False
    metering_rate_veh_per_hour: float = 400.0  # max release rate when metered


@dataclass
class CorridorNetwork:
    """A straight single-lane road corridor."""

    length: float  # m
    base_speed_limit: float = 13.9  # m/s (~50 km/h)
    signals: list[TrafficSignal] = field(default_factory=list)
    speed_limit_zones: list[SpeedLimitZone] = field(default_factory=list)
    on_ramp: OnRamp | None = None

    def speed_limit_at(self, position: float) -> float:
        for zone in self.speed_limit_zones:
            if zone.start <= position < zone.end:
                return zone.speed_limit
        return self.base_speed_limit


@dataclass
class RoundaboutNetwork:
    """A simplified single-entry roundabout.

    The circulating lane is a ring of length ``circumference``; position
    is taken modulo the circumference. Traffic already circulating has
    priority (as in a real UK roundabout); vehicles waiting on the
    approach arm gap-accept into the circulating flow at ``entry_position``.
    Each vehicle is assigned an exit arc length at spawn time (drawn from
    ``exit_arc_range``) after which it leaves the simulation.
    """

    circumference: float  # m
    base_speed_limit: float = 8.3  # m/s (~30 km/h, typical roundabout speed)
    entry_position: float = 0.0
    exit_arc_range: tuple[float, float] = (60.0, 220.0)  # m travelled before exiting
    entry_demand_veh_per_hour: float = 300.0

    def speed_limit_at(self, position: float) -> float:
        return self.base_speed_limit
