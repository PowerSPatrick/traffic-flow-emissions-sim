"""Unit tests for the Intelligent Driver Model."""

from __future__ import annotations

import math

import numpy as np
import pytest

from traffic_sim.idm import IDMParams, desired_gap, idm_acceleration


@pytest.fixture
def params() -> IDMParams:
    return IDMParams(v0=30.0, T=1.5, a_max=1.4, b=2.0, delta=4.0, s0=2.0)


def test_free_road_accelerates_towards_desired_speed(params):
    a = idm_acceleration(v=10.0, v_lead=10.0, gap=math.inf, params=params)
    assert a > 0.0


def test_at_desired_speed_free_road_has_zero_acceleration(params):
    a = idm_acceleration(v=params.v0, v_lead=params.v0, gap=math.inf, params=params)
    assert a == pytest.approx(0.0, abs=1e-9)


def test_above_desired_speed_free_road_decelerates(params):
    a = idm_acceleration(v=params.v0 * 1.2, v_lead=params.v0, gap=math.inf, params=params)
    assert a < 0.0


def test_stopped_leader_close_ahead_causes_braking(params):
    # Own vehicle moving fast, leader stationary very close ahead.
    a = idm_acceleration(v=20.0, v_lead=0.0, gap=3.0, params=params)
    assert a < -1.0


def test_larger_gap_gives_less_braking(params):
    a_close = idm_acceleration(v=20.0, v_lead=15.0, gap=5.0, params=params)
    a_far = idm_acceleration(v=20.0, v_lead=15.0, gap=50.0, params=params)
    assert a_far > a_close


def test_equilibrium_following_gives_near_zero_acceleration(params):
    # The IDM's analytic equilibrium (constant-speed car-following) gap
    # solves 0 = 1 - (v/v0)^delta - (s*/s)^2, i.e. s_eq = s* / sqrt(1 -
    # (v/v0)^delta). Feeding that gap back in at the same speed as the
    # leader should give (near) zero net acceleration.
    v = 0.7 * params.v0
    s_star = float(desired_gap(v=np.array(v), dv=np.array(0.0), params=params))
    denom = math.sqrt(1.0 - (v / params.v0) ** params.delta)
    gap = s_star / denom
    a = idm_acceleration(v=v, v_lead=v, gap=gap, params=params)
    assert a == pytest.approx(0.0, abs=1e-6)


def test_desired_gap_increases_with_speed(params):
    g_slow = desired_gap(v=np.array(5.0), dv=np.array(0.0), params=params)
    g_fast = desired_gap(v=np.array(20.0), dv=np.array(0.0), params=params)
    assert g_fast > g_slow


def test_desired_gap_floor_is_s0_when_stationary(params):
    g = desired_gap(v=np.array(0.0), dv=np.array(0.0), params=params)
    assert g == pytest.approx(params.s0)


def test_vectorized_inputs_broadcast(params):
    v = np.array([5.0, 10.0, 15.0])
    v_lead = np.array([5.0, 10.0, 15.0])
    gap = np.array([10.0, 20.0, 30.0])
    a = idm_acceleration(v, v_lead, gap, params)
    assert a.shape == (3,)


def test_invalid_params_raise():
    with pytest.raises(ValueError):
        IDMParams(v0=-1.0)
    with pytest.raises(ValueError):
        IDMParams(a_max=0.0)
    with pytest.raises(ValueError):
        IDMParams(b=-2.0)
