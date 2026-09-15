"""Unit tests for the gap-acceptance merge model."""

from __future__ import annotations

import math

from traffic_sim.lane_change import MergeParams, can_merge, critical_gap


def test_critical_gap_grows_with_closing_speed():
    params = MergeParams(min_gap=5.0, reaction_time=1.0)
    assert critical_gap(0.0, params) == 5.0
    assert critical_gap(10.0, params) == 15.0


def test_critical_gap_floors_at_min_gap_for_opening_gap():
    params = MergeParams(min_gap=5.0, reaction_time=1.0)
    assert critical_gap(-10.0, params) == 5.0


def test_can_merge_true_with_large_gaps():
    assert can_merge(
        merge_speed=15.0, gap_ahead=100.0, speed_ahead=15.0,
        gap_behind=100.0, speed_behind=15.0,
    )


def test_can_merge_false_when_closing_fast_on_leader():
    # Merging vehicle much faster than a close leader ahead -> reject.
    accepted = can_merge(
        merge_speed=25.0, gap_ahead=5.0, speed_ahead=5.0,
        gap_behind=100.0, speed_behind=15.0,
    )
    assert not accepted


def test_can_merge_false_when_follower_closing_fast():
    accepted = can_merge(
        merge_speed=15.0, gap_ahead=100.0, speed_ahead=15.0,
        gap_behind=5.0, speed_behind=30.0,
    )
    assert not accepted


def test_can_merge_true_with_infinite_gaps():
    assert can_merge(
        merge_speed=15.0, gap_ahead=math.inf, speed_ahead=0.0,
        gap_behind=math.inf, speed_behind=0.0,
    )
