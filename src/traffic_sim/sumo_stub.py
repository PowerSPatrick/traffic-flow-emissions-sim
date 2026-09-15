"""Optional SUMO/TraCI integration stub.

The rest of this package is a standalone pure-Python/numpy simulation
engine that requires no external simulator. This module is a placeholder
for later work that would drive the (much more detailed) SUMO traffic
simulator via its TraCI Python API instead, for scenarios that need
SUMO's richer network import (e.g. real OSM-derived UK road geometry) or
its emissions models (SUMO ships HBEFA-based emission classes).

It is never imported by default and SUMO/TraCI does not need to be
installed to use the rest of this package -- only import this module,
or set ``use_sumo=True`` on :func:`run_via_traci`, if you have SUMO
installed and want to experiment with it.
"""

from __future__ import annotations

from typing import Any


class SumoNotAvailable(RuntimeError):
    """Raised when SUMO/TraCI integration is requested but not installed."""


def run_via_traci(
    sumo_cfg_path: str,
    use_sumo: bool = False,
    step_length: float = 0.5,
    max_steps: int = 1000,
) -> dict[str, Any]:
    """Run a scenario through SUMO via TraCI instead of the built-in engine.

    This is a stub: it only performs the import/connect handshake and a
    minimal step loop, collecting basic per-step vehicle counts. It is
    intended as a starting point for future integration work, not a
    complete replacement for :class:`traffic_sim.simulation.Simulation`.

    Args:
        sumo_cfg_path: Path to a SUMO ``.sumocfg`` file.
        use_sumo: Must be explicitly set True to attempt this path; the
            rest of the package never requires SUMO to be installed.
        step_length: Simulation step length in seconds.
        max_steps: Maximum number of TraCI steps to run.

    Returns:
        A dict with a ``vehicle_counts`` list (one entry per step).

    Raises:
        SumoNotAvailable: If ``use_sumo`` is True but the ``traci``
            package (installed alongside SUMO) is not importable.
    """
    if not use_sumo:
        raise SumoNotAvailable(
            "SUMO integration is opt-in; pass use_sumo=True and ensure SUMO/TraCI "
            "is installed (see https://sumo.dlr.de/docs/TraCI.html)."
        )
    try:
        import traci  # type: ignore
        import sumolib  # type: ignore  # noqa: F401
    except ImportError as exc:  # pragma: no cover - requires external SUMO install
        raise SumoNotAvailable(
            "The 'traci' package was not found. Install SUMO "
            "(https://sumo.dlr.de/docs/Installing/index.html) and ensure its "
            "'tools' directory is on PYTHONPATH."
        ) from exc

    traci.start(["sumo", "-c", sumo_cfg_path, "--step-length", str(step_length)])
    vehicle_counts: list[int] = []
    try:
        for _ in range(max_steps):
            traci.simulationStep()
            vehicle_counts.append(traci.vehicle.getIDCount())
    finally:
        traci.close()

    return {"vehicle_counts": vehicle_counts}
