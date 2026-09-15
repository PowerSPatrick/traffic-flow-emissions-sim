"""Instantaneous vehicle emissions model.

IMPORTANT — approximation notice
---------------------------------
The coefficients in :class:`EmissionFactors` are illustrative placeholders
of the right order of magnitude and qualitative shape (high emissions at
idle / low speed and during hard acceleration, a broad efficiency minimum
around typical cruise speeds, and rising drag-related emissions at high
speed). They are loosely inspired by the *shape* of COPERT (COmputer
Programme to calculate Emissions from Road Transport) hot-emission factor
curves and by power-based (VSP/VT-Micro style) instantaneous emissions
models used to add acceleration-sensitivity on top of COPERT's
average-speed curves.

They are **not** calibrated to real vehicles and MUST be replaced with
published factors before any real-world conclusions are drawn, e.g.:

  * COPERT 5 hot-emission functions (EMISIA / EEA Emission Inventory
    Guidebook), per Euro class / fuel / segment.
  * UK National Atmospheric Emissions Inventory (NAEI) road transport
    emission factors (DEFRA/DfT).

See ``data/README.md`` for where to obtain these.

Model form
----------
Instantaneous emission rate (g/s) is split into an idle/base term, a
cruise term polynomial in speed (rolling resistance + aerodynamic drag,
the latter scaling roughly with v^3), and an acceleration term that is
only active during positive acceleration (extra tractive power demand),
which is what makes stop-start driving disproportionately polluting
compared to smooth driving at the same average speed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EmissionFactors:
    """Polynomial coefficients for the instantaneous emissions model.

    All rates are grams per second. ``v`` is speed in m/s, ``a`` is
    acceleration in m/s^2. Values are approximations -- see module
    docstring.
    """

    # CO2 (g/s)
    co2_idle: float = 0.55       # engine idling, v=0, a=0
    co2_v1: float = 0.045        # linear (rolling resistance) term
    co2_v2: float = 0.0006       # quadratic term
    co2_v3: float = 0.00045      # cubic (aerodynamic drag) term
    co2_accel: float = 0.9       # coefficient on max(0, a) * v (tractive power)

    # NOx (g/s) -- roughly 3 orders of magnitude smaller than CO2, but with
    # a much stronger relative sensitivity to hard acceleration, which is
    # characteristic of real NOx formation (combustion temperature/pressure
    # rise sharply under load).
    nox_idle: float = 0.0008
    nox_v1: float = 0.00006
    nox_v2: float = 0.0000025
    nox_accel: float = 0.006
    nox_accel2: float = 0.004    # coefficient on max(0, a)^2, hard-accel penalty


DEFAULT_FACTORS = EmissionFactors()


def instantaneous_emissions_gps(
    v: np.ndarray,
    a: np.ndarray,
    factors: EmissionFactors = DEFAULT_FACTORS,
) -> tuple[np.ndarray, np.ndarray]:
    """Instantaneous CO2 and NOx emission rates.

    Args:
        v: Speed(s), m/s. Must be >= 0.
        a: Acceleration(s), m/s^2. May be negative (braking/coasting).
        factors: Emission factor coefficients.

    Returns:
        Tuple ``(co2_gps, nox_gps)`` of emission rates in grams/second,
        each with the broadcast shape of ``v``/``a`` and never negative.
    """
    v = np.asarray(v, dtype=float)
    a = np.asarray(a, dtype=float)
    a_pos = np.maximum(a, 0.0)

    co2 = (
        factors.co2_idle
        + factors.co2_v1 * v
        + factors.co2_v2 * v**2
        + factors.co2_v3 * v**3
        + factors.co2_accel * a_pos * v
    )
    nox = (
        factors.nox_idle
        + factors.nox_v1 * v
        + factors.nox_v2 * v**2
        + factors.nox_accel * a_pos * v
        + factors.nox_accel2 * a_pos**2
    )
    return np.maximum(co2, 0.0), np.maximum(nox, 0.0)


def step_emissions_grams(
    v: float,
    a: float,
    dt: float,
    factors: EmissionFactors = DEFAULT_FACTORS,
) -> tuple[float, float]:
    """Grams of CO2 and NOx emitted over one simulation timestep ``dt``."""
    co2_gps, nox_gps = instantaneous_emissions_gps(v, a, factors)
    return float(co2_gps) * dt, float(nox_gps) * dt


def grams_per_km(total_grams: float, total_distance_km: float) -> float:
    """Average emission factor in g/km, given total emitted grams and
    total distance travelled in km. Returns 0.0 if no distance travelled.
    """
    if total_distance_km <= 0:
        return 0.0
    return total_grams / total_distance_km
