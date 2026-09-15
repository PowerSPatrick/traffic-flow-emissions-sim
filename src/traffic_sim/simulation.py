"""Core microscopic simulation engine.

Single-lane car-following (IDM) simulation supporting the two network
topologies in :mod:`traffic_sim.network`. Traffic signals are modelled as
virtual stationary "phantom vehicles" at the stop line while red -- a
standard microsimulation trick that lets the IDM car-following logic
handle both real leaders and red lights uniformly. Ramp/roundabout-entry
merging uses the gap-acceptance model in :mod:`traffic_sim.lane_change`.

This is intentionally a simplified, pure-Python/numpy engine (no SUMO
dependency) so the whole harness runs standalone. See
:mod:`traffic_sim.sumo_stub` for an optional, off-by-default TraCI
integration path for later work with the real SUMO simulator.
"""

from __future__ import annotations

import bisect
import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np

from .emissions import EmissionFactors, step_emissions_grams
from .idm import IDMParams, idm_acceleration
from .lane_change import MergeParams, can_merge
from .network import CorridorNetwork, OnRamp, RoundaboutNetwork
from .vehicle import Vehicle

_INF = math.inf


@dataclass
class SimulationConfig:
    dt: float = 0.5                       # s, integration timestep
    duration: float = 1200.0              # s, total simulated time
    mainline_demand_veh_per_hour: float = 900.0
    idm_params: IDMParams = field(default_factory=IDMParams)
    merge_params: MergeParams = field(default_factory=MergeParams)
    emission_factors: EmissionFactors = field(default_factory=EmissionFactors)
    stop_speed_threshold: float = 0.5     # m/s, below this counts as "stopped"
    vehicle_length: float = 4.5
    max_speed: float = 33.0               # m/s, ~120 km/h
    ramp_approach_speed: float = 8.0      # m/s, speed ramp vehicles merge at
    seed: int = 0


@dataclass
class SimulationResult:
    completed: list[Vehicle]
    active: list[Vehicle]
    duration: float
    network_length: float | None
    config: SimulationConfig


class Simulation:
    """Runs a single scenario (one network + one policy configuration)."""

    def __init__(
        self,
        network: CorridorNetwork | RoundaboutNetwork,
        config: SimulationConfig | None = None,
    ) -> None:
        self.network = network
        self.config = config or SimulationConfig()
        self.rng = np.random.default_rng(self.config.seed)

        self.t = 0.0
        self._next_id = 0
        self.vehicles: list[Vehicle] = []      # sorted ascending by position
        self.queue: list[Vehicle] = []         # waiting to merge (ramp / roundabout entry)
        self.completed: list[Vehicle] = []
        self._last_ramp_release_t = -_INF

    # -- setup helpers ----------------------------------------------------

    def _new_vehicle(self, position: float, speed: float) -> Vehicle:
        v = Vehicle(
            id=self._next_id,
            lane=0,
            position=position,
            speed=speed,
            length=self.config.vehicle_length,
            max_speed=self.config.max_speed,
            depart_time=self.t,
        )
        self._next_id += 1
        return v

    def _desired_speed_limit(self, position: float) -> float:
        return self.network.speed_limit_at(position)

    # -- main loop ----------------------------------------------------------

    def run(self) -> SimulationResult:
        n_steps = int(round(self.config.duration / self.config.dt))
        for _ in range(n_steps):
            self.step()
        network_length = (
            self.network.length if isinstance(self.network, CorridorNetwork) else None
        )
        return SimulationResult(
            completed=self.completed,
            active=list(self.vehicles) + list(self.queue),
            duration=self.t,
            network_length=network_length,
            config=self.config,
        )

    def step(self) -> None:
        dt = self.config.dt
        if isinstance(self.network, CorridorNetwork):
            self._step_corridor(dt)
        else:
            self._step_roundabout(dt)
        self.t += dt

    # -- corridor topology --------------------------------------------------

    def _step_corridor(self, dt: float) -> None:
        net: CorridorNetwork = self.network

        # 1) accelerations
        accels = [0.0] * len(self.vehicles)
        for i, veh in enumerate(self.vehicles):
            leader = self.vehicles[i + 1] if i + 1 < len(self.vehicles) else None
            gap, v_lead = self._corridor_obstacle(veh, leader, net)
            local_v0 = min(self.config.idm_params.v0, self._desired_speed_limit(veh.position))
            params = dataclasses.replace(self.config.idm_params, v0=max(local_v0, 0.1))
            accels[i] = float(idm_acceleration(veh.speed, v_lead, gap, params))

        # 2) integrate + emissions + stop bookkeeping
        for veh, a in zip(self.vehicles, accels):
            self._integrate_vehicle(veh, a, dt)

        # 3) waiting-in-queue vehicles idle (ramp queue)
        for veh in self.queue:
            self._idle_vehicle(veh, dt)

        # 4) remove vehicles that reached the end of the corridor
        self._drain_completed_corridor(net.length)

        # 5) ramp merging
        if net.on_ramp is not None:
            self._maybe_spawn_ramp(net.on_ramp)
            self._maybe_merge_ramp(net.on_ramp)

        # 6) mainline spawn
        self._maybe_spawn_mainline()

    def _corridor_obstacle(
        self, veh: Vehicle, leader: Vehicle | None, net: CorridorNetwork
    ) -> tuple[float, float]:
        """Nearest obstacle ahead of ``veh``: real leader or a red signal."""
        best_gap = _INF
        best_v = veh.speed  # dv = 0 if no obstacle -> free road

        if leader is not None:
            gap = leader.rear - veh.position
            if gap < best_gap:
                best_gap, best_v = gap, leader.speed

        for sig in net.signals:
            if sig.position <= veh.position:
                continue
            if leader is not None and sig.position > leader.position:
                continue  # a real leader is already closer than this signal
            if not sig.is_green(self.t):
                gap = sig.position - veh.position
                if gap < best_gap:
                    best_gap, best_v = gap, 0.0

        return best_gap, best_v

    def _drain_completed_corridor(self, length: float) -> None:
        while self.vehicles and self.vehicles[-1].position >= length:
            veh = self.vehicles.pop()
            veh.arrival_time = self.t
            self.completed.append(veh)

    def _maybe_spawn_mainline(self) -> None:
        p = self.config.mainline_demand_veh_per_hour / 3600.0 * self.config.dt
        if self.rng.random() >= p:
            return
        entry_pos = 0.0
        desired = min(self.config.idm_params.v0, self._desired_speed_limit(entry_pos))
        if self.vehicles:
            nearest = self.vehicles[0]
            gap = nearest.position - nearest.length - entry_pos
            if gap < self.config.idm_params.s0 + 2.0:
                return  # no room -- demand not served this step
            speed = min(desired, nearest.speed)
        else:
            speed = desired
        veh = self._new_vehicle(entry_pos, speed)
        bisect.insort(self.vehicles, veh, key=lambda v: v.position)

    def _maybe_spawn_ramp(self, ramp: OnRamp) -> None:
        p = ramp.demand_veh_per_hour / 3600.0 * self.config.dt
        if self.rng.random() >= p:
            return
        veh = self._new_vehicle(ramp.merge_position, self.config.ramp_approach_speed)
        self.queue.append(veh)

    def _maybe_merge_ramp(self, ramp: OnRamp) -> None:
        if not self.queue:
            return
        if ramp.metering:
            min_gap_t = 3600.0 / max(ramp.metering_rate_veh_per_hour, 1e-6)
            if self.t - self._last_ramp_release_t < min_gap_t:
                return

        candidate = self.queue[0]
        idx = bisect.bisect_left([v.position for v in self.vehicles], ramp.merge_position)
        leader_ahead = self.vehicles[idx] if idx < len(self.vehicles) else None
        follower_behind = self.vehicles[idx - 1] if idx > 0 else None

        gap_ahead = (leader_ahead.rear - ramp.merge_position) if leader_ahead else _INF
        speed_ahead = leader_ahead.speed if leader_ahead else 0.0
        gap_behind = (
            (ramp.merge_position - follower_behind.position) if follower_behind else _INF
        )
        speed_behind = follower_behind.speed if follower_behind else 0.0

        merge_speed = min(self.config.ramp_approach_speed, speed_ahead) if leader_ahead else (
            self.config.ramp_approach_speed
        )

        if can_merge(
            merge_speed, gap_ahead, speed_ahead, gap_behind, speed_behind, self.config.merge_params
        ):
            self.queue.pop(0)
            candidate.position = ramp.merge_position
            candidate.speed = merge_speed
            bisect.insort(self.vehicles, candidate, key=lambda v: v.position)
            self._last_ramp_release_t = self.t

    # -- roundabout topology -------------------------------------------------

    def _step_roundabout(self, dt: float) -> None:
        net: RoundaboutNetwork = self.network
        c = net.circumference

        accels = [0.0] * len(self.vehicles)
        n = len(self.vehicles)
        for i, veh in enumerate(self.vehicles):
            if n <= 1:
                gap, v_lead = _INF, veh.speed
            else:
                leader = self.vehicles[(i + 1) % n]
                gap = (leader.position - veh.position) % c - leader.length
                v_lead = leader.speed
            local_v0 = min(self.config.idm_params.v0, net.base_speed_limit)
            params = dataclasses.replace(self.config.idm_params, v0=max(local_v0, 0.1))
            accels[i] = float(idm_acceleration(veh.speed, v_lead, max(gap, 1e-3), params))

        for veh, a in zip(self.vehicles, accels):
            old_pos = veh.position
            self._integrate_vehicle(veh, a, dt, wrap=c)
            travelled = (veh.position - old_pos) % c
            if veh.exit_arc is not None:
                veh.exit_arc -= travelled

        for veh in self.queue:
            self._idle_vehicle(veh, dt)

        self._drain_completed_roundabout()
        self._maybe_spawn_entry(net)
        self._maybe_merge_entry(net)

    def _drain_completed_roundabout(self) -> None:
        remaining = []
        for veh in self.vehicles:
            if veh.exit_arc is not None and veh.exit_arc <= 0:
                veh.arrival_time = self.t
                self.completed.append(veh)
            else:
                remaining.append(veh)
        self.vehicles = remaining

    def _maybe_spawn_entry(self, net: RoundaboutNetwork) -> None:
        p = net.entry_demand_veh_per_hour / 3600.0 * self.config.dt
        if self.rng.random() >= p:
            return
        veh = self._new_vehicle(net.entry_position, self.config.ramp_approach_speed)
        low, high = net.exit_arc_range
        veh.exit_arc = float(self.rng.uniform(low, high))
        self.queue.append(veh)

    def _maybe_merge_entry(self, net: RoundaboutNetwork) -> None:
        if not self.queue:
            return
        candidate = self.queue[0]
        c = net.circumference
        n = len(self.vehicles)
        if n == 0:
            gap_ahead = gap_behind = _INF
            speed_ahead = speed_behind = 0.0
        else:
            sorted_positions = self.vehicles  # already sorted ascending
            idx = bisect.bisect_left(
                [v.position for v in sorted_positions], net.entry_position
            )
            leader_ahead = sorted_positions[idx % n]
            follower_behind = sorted_positions[(idx - 1) % n]
            gap_ahead = (leader_ahead.position - net.entry_position) % c - leader_ahead.length
            speed_ahead = leader_ahead.speed
            gap_behind = (net.entry_position - follower_behind.position) % c
            speed_behind = follower_behind.speed

        merge_speed = min(self.config.ramp_approach_speed, speed_ahead) if n else (
            self.config.ramp_approach_speed
        )
        if can_merge(
            merge_speed, gap_ahead, speed_ahead, gap_behind, speed_behind, self.config.merge_params
        ):
            self.queue.pop(0)
            candidate.position = net.entry_position
            candidate.speed = merge_speed
            bisect.insort(self.vehicles, candidate, key=lambda v: v.position)

    # -- shared physics / bookkeeping ---------------------------------------

    def _integrate_vehicle(
        self, veh: Vehicle, a: float, dt: float, wrap: float | None = None
    ) -> None:
        a = max(a, -6.0)  # bound extreme braking for numerical sanity
        new_speed = min(max(veh.speed + a * dt, 0.0), veh.max_speed)
        # If braking hard from a low speed, don't overshoot into reverse.
        if veh.speed + a * dt < 0.0:
            dx = -(veh.speed**2) / (2 * a) if a != 0 else 0.0
        else:
            dx = veh.speed * dt + 0.5 * a * dt**2
        dx = max(dx, 0.0)

        veh.accel = a
        veh.speed = new_speed
        veh.position = (veh.position + dx) if wrap is None else (veh.position + dx) % wrap
        veh.distance_travelled += dx

        veh.update_stop_count(dt, self.config.stop_speed_threshold)
        co2, nox = step_emissions_grams(veh.speed, a, dt, self.config.emission_factors)
        veh.cum_co2_g += co2
        veh.cum_nox_g += nox

    def _idle_vehicle(self, veh: Vehicle, dt: float) -> None:
        veh.accel = 0.0
        veh.update_stop_count(dt, self.config.stop_speed_threshold)
        co2, nox = step_emissions_grams(0.0, 0.0, dt, self.config.emission_factors)
        veh.cum_co2_g += co2
        veh.cum_nox_g += nox
