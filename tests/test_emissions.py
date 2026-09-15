"""Unit tests for the instantaneous emissions model."""

from __future__ import annotations

import numpy as np
import pytest

from traffic_sim.emissions import (
    DEFAULT_FACTORS,
    EmissionFactors,
    grams_per_km,
    instantaneous_emissions_gps,
    step_emissions_grams,
)


def test_idle_emissions_are_positive():
    co2, nox = instantaneous_emissions_gps(v=0.0, a=0.0)
    assert co2 > 0.0
    assert nox > 0.0


def test_idle_emissions_match_idle_factor():
    co2, nox = instantaneous_emissions_gps(v=0.0, a=0.0)
    assert co2 == pytest.approx(DEFAULT_FACTORS.co2_idle)
    assert nox == pytest.approx(DEFAULT_FACTORS.nox_idle)


def test_emissions_increase_with_cruise_speed():
    co2_slow, nox_slow = instantaneous_emissions_gps(v=5.0, a=0.0)
    co2_fast, nox_fast = instantaneous_emissions_gps(v=25.0, a=0.0)
    assert co2_fast > co2_slow
    assert nox_fast > nox_slow


def test_acceleration_increases_emissions_relative_to_cruise():
    co2_cruise, nox_cruise = instantaneous_emissions_gps(v=15.0, a=0.0)
    co2_accel, nox_accel = instantaneous_emissions_gps(v=15.0, a=1.5)
    assert co2_accel > co2_cruise
    assert nox_accel > nox_cruise


def test_braking_does_not_reduce_below_cruise_baseline():
    # Negative acceleration should not add the tractive-power penalty
    # (max(0, a) clips it out) so braking emissions equal the cruise
    # emissions at the same speed, not less.
    co2_cruise, nox_cruise = instantaneous_emissions_gps(v=15.0, a=0.0)
    co2_brake, nox_brake = instantaneous_emissions_gps(v=15.0, a=-2.0)
    assert co2_brake == pytest.approx(co2_cruise)
    assert nox_brake == pytest.approx(nox_cruise)


def test_emissions_never_negative_for_extreme_inputs():
    co2, nox = instantaneous_emissions_gps(v=0.0, a=-10.0)
    assert co2 >= 0.0
    assert nox >= 0.0


def test_hard_acceleration_penalises_nox_more_than_co2_relatively():
    factors = EmissionFactors()
    co2_cruise, nox_cruise = instantaneous_emissions_gps(v=15.0, a=0.0, factors=factors)
    co2_hard, nox_hard = instantaneous_emissions_gps(v=15.0, a=3.0, factors=factors)
    co2_ratio = co2_hard / co2_cruise
    nox_ratio = nox_hard / nox_cruise
    assert nox_ratio > co2_ratio


def test_vectorized_inputs():
    v = np.array([0.0, 10.0, 20.0])
    a = np.array([0.0, 1.0, -1.0])
    co2, nox = instantaneous_emissions_gps(v, a)
    assert co2.shape == (3,)
    assert nox.shape == (3,)
    assert np.all(co2 >= 0.0)


def test_step_emissions_scale_with_dt():
    co2_1s, nox_1s = step_emissions_grams(v=10.0, a=0.0, dt=1.0)
    co2_2s, nox_2s = step_emissions_grams(v=10.0, a=0.0, dt=2.0)
    assert co2_2s == pytest.approx(2 * co2_1s)
    assert nox_2s == pytest.approx(2 * nox_1s)


def test_grams_per_km_basic():
    assert grams_per_km(total_grams=1000.0, total_distance_km=10.0) == pytest.approx(100.0)


def test_grams_per_km_zero_distance_returns_zero():
    assert grams_per_km(total_grams=1000.0, total_distance_km=0.0) == 0.0
