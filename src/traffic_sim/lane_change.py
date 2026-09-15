"""Simple gap-acceptance merge / lane-change model.

This is deliberately much simpler than a full MOBIL lane-changing model.
It is used for two situations in this project's scenarios:

  * A vehicle waiting on an on-ramp merging onto the mainline corridor.
  * A vehicle waiting at a roundabout entry merging into the circulating
    lane.

Both are modelled the same way: the merging vehicle needs an acceptable
gap in the target traffic stream, both ahead of and behind the point it
would enter at. The critical gap grows with the closing speed, reflecting
that a driver needs a bigger gap to merge safely in front of a fast
car than a slow one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MergeParams:
    """Parameters controlling gap-acceptance merge behaviour."""

    min_gap: float = 5.0          # m, minimum accepted gap regardless of speed
    reaction_time: float = 1.2    # s, extra gap per m/s of adverse closing speed


def critical_gap(closing_speed: float, params: MergeParams = MergeParams()) -> float:
    """Minimum acceptable gap given the closing speed (m/s).

    ``closing_speed`` > 0 means the gap is shrinking (the other vehicle is
    approaching / being approached), so a larger gap is required. Negative
    or zero closing speed (gap steady or opening) only requires the base
    minimum gap.
    """
    return params.min_gap + params.reaction_time * max(0.0, closing_speed)


def can_merge(
    merge_speed: float,
    gap_ahead: float,
    speed_ahead: float,
    gap_behind: float,
    speed_behind: float,
    params: MergeParams = MergeParams(),
) -> bool:
    """Whether a vehicle travelling at ``merge_speed`` can merge into a gap.

    Args:
        merge_speed: Speed the merging vehicle would enter the target lane
            at, m/s.
        gap_ahead: Space headway to the next vehicle ahead in the target
            lane, m. Use ``math.inf`` if there is none.
        speed_ahead: Speed of that leading vehicle, m/s (ignored if no
            leader).
        gap_behind: Space headway to the nearest vehicle behind in the
            target lane, m. Use ``math.inf`` if there is none.
        speed_behind: Speed of that following vehicle, m/s (ignored if no
            follower).
        params: Gap-acceptance parameters.

    Returns:
        True if both the front and rear gaps exceed their critical gap.
    """
    closing_ahead = merge_speed - speed_ahead  # merging vehicle catching up to leader
    closing_behind = speed_behind - merge_speed  # follower catching up to merging vehicle

    ahead_ok = gap_ahead >= critical_gap(closing_ahead, params)
    behind_ok = gap_behind >= critical_gap(closing_behind, params)
    return ahead_ok and behind_ok
