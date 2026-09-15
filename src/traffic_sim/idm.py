"""Intelligent Driver Model (IDM) car-following model.

Reference: Treiber, Hennecke & Helbing (2000), "Congested Traffic States in
Empirical Observations and Microscopic Simulations", Phys. Rev. E 62, 1805.

The IDM gives a smooth, collision-free acceleration law for a following
vehicle in terms of its own speed, the speed difference to its leader, and
the (bumper-to-bumper) gap to the leader. It is the workhorse car-following
model used throughout this simulation because it naturally reproduces
stop-and-go waves, which is the phenomenon this research project is trying
to smooth out to reduce emissions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class IDMParams:
    """Parameters of the Intelligent Driver Model.

    Attributes:
        v0: Desired (free-flow) speed, m/s.
        T: Desired time headway to the leader, s.
        a_max: Maximum acceleration, m/s^2.
        b: Comfortable (desired) deceleration, m/s^2 (positive number).
        delta: Free-road acceleration exponent (typically 4).
        s0: Minimum bumper-to-bumper gap at a standstill, m.
    """

    v0: float = 30.0
    T: float = 1.5
    a_max: float = 1.4
    b: float = 2.0
    delta: float = 4.0
    s0: float = 2.0

    def __post_init__(self) -> None:
        if self.v0 <= 0:
            raise ValueError("v0 must be positive")
        if self.T < 0:
            raise ValueError("T must be non-negative")
        if self.a_max <= 0:
            raise ValueError("a_max must be positive")
        if self.b <= 0:
            raise ValueError("b must be positive")
        if self.s0 < 0:
            raise ValueError("s0 must be non-negative")


def desired_gap(v: np.ndarray, dv: np.ndarray, params: IDMParams) -> np.ndarray:
    """Dynamic desired minimum gap s*(v, dv) of the IDM.

    Args:
        v: Own speed, m/s.
        dv: Approach rate = v - v_leader, m/s (positive = closing in).
        params: IDM parameters.
    """
    v = np.asarray(v, dtype=float)
    dv = np.asarray(dv, dtype=float)
    braking_term = (v * dv) / (2.0 * np.sqrt(params.a_max * params.b))
    return params.s0 + np.maximum(0.0, v * params.T + braking_term)


def idm_acceleration(
    v: np.ndarray,
    v_lead: np.ndarray,
    gap: np.ndarray,
    params: IDMParams,
) -> np.ndarray:
    """Compute IDM acceleration for a (vector of) following vehicle(s).

    Free-road driving is represented by passing ``gap=np.inf`` (and any
    ``v_lead``, e.g. equal to ``v``) for the vehicles with no leader in
    range -- the interaction term then vanishes exactly, so no branching
    is required.

    Args:
        v: Current speed(s) of the following vehicle(s), m/s.
        v_lead: Current speed(s) of the leading vehicle(s), m/s.
        gap: Net (bumper-to-bumper) space headway to the leader, m. Must be
            strictly positive; use a small epsilon rather than zero.
        params: IDM parameters.

    Returns:
        Acceleration(s), m/s^2. Can be negative (braking); this model does
        not impose a hard minimum deceleration.
    """
    v = np.asarray(v, dtype=float)
    v_lead = np.asarray(v_lead, dtype=float)
    gap = np.asarray(gap, dtype=float)

    dv = v - v_lead
    s_star = desired_gap(v, dv, params)
    gap_safe = np.maximum(gap, 1e-3)

    free_road_term = (v / params.v0) ** params.delta
    interaction_term = (s_star / gap_safe) ** 2

    return params.a_max * (1.0 - free_road_term - interaction_term)
