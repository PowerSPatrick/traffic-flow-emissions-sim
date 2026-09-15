"""Traffic signal timing plans.

Supports simple fixed-time signals, each independently offset. A "green
wave" intervention is just a particular choice of offsets, computed from
the free-flow travel time between consecutive signals so that a platoon
of vehicles released from one signal on green tends to arrive at the next
signal while it is still green.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrafficSignal:
    """A fixed-time signalised stop line on a corridor.

    The signal cycles with period ``cycle_time``, green for the first
    ``green_time`` seconds of each cycle (starting at ``offset``), then red
    for the remainder.
    """

    position: float  # metres along the corridor
    cycle_time: float = 60.0
    green_time: float = 30.0
    offset: float = 0.0

    def __post_init__(self) -> None:
        if self.green_time > self.cycle_time:
            raise ValueError("green_time cannot exceed cycle_time")
        if self.green_time < 0 or self.cycle_time <= 0:
            raise ValueError("green_time/cycle_time must be positive")

    def is_green(self, t: float) -> bool:
        phase = (t - self.offset) % self.cycle_time
        return phase < self.green_time

    def time_to_next_green(self, t: float) -> float:
        """Seconds until the signal next turns (or remains) green."""
        if self.is_green(t):
            return 0.0
        phase = (t - self.offset) % self.cycle_time
        return self.cycle_time - phase


def compute_green_wave_offsets(
    positions: list[float],
    cycle_time: float,
    green_time: float,
    progression_speed: float,
) -> list[float]:
    """Offsets that create a "green wave" through a line of signals.

    Each signal's green window is shifted so that a vehicle travelling at
    ``progression_speed`` from the first signal (offset 0) arrives at each
    subsequent signal exactly when it turns green, modulo the cycle time.
    This is the standard traffic-engineering coordination scheme; it does
    not guarantee every vehicle avoids every red light (arrival spread
    within a platoon, queueing, turning traffic, etc. all matter in
    reality) but it substantially reduces stops for a coordinated corridor
    compared to independently-timed signals.

    Args:
        positions: Signal positions along the corridor, in order, metres.
        cycle_time: Common cycle time for all signals, s.
        green_time: Common green duration for all signals, s.
        progression_speed: Design (target) progression speed, m/s.

    Returns:
        List of offsets (s), one per signal, same order as ``positions``.
    """
    if not positions:
        return []
    base = positions[0]
    offsets = [
        ((pos - base) / progression_speed) % cycle_time for pos in positions
    ]
    return offsets


def build_signals(
    positions: list[float],
    cycle_time: float = 60.0,
    green_time: float = 30.0,
    green_wave: bool = False,
    progression_speed: float = 13.9,  # ~50 km/h
) -> list[TrafficSignal]:
    """Construct a list of :class:`TrafficSignal` for given positions.

    If ``green_wave`` is False, all signals share offset 0 (uncoordinated,
    but identical -- deliberately the more pessimistic baseline where
    every signal turns red/green in lockstep with no progression benefit
    for a moving platoon spread out along the corridor). If True, offsets
    are computed with :func:`compute_green_wave_offsets`.
    """
    if green_wave:
        offsets = compute_green_wave_offsets(
            positions, cycle_time, green_time, progression_speed
        )
    else:
        offsets = [0.0 for _ in positions]
    return [
        TrafficSignal(position=p, cycle_time=cycle_time, green_time=green_time, offset=o)
        for p, o in zip(positions, offsets)
    ]
