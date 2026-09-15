"""Vehicle state representation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Vehicle:
    """A single simulated vehicle.

    Positions are measured in metres along the centreline of the road the
    vehicle currently occupies, increasing in the direction of travel.
    ``position`` refers to the vehicle's front bumper.
    """

    id: int
    lane: int
    position: float
    speed: float
    length: float = 4.5
    max_speed: float = 33.0  # m/s, ~120 km/h, vehicle's own top speed
    accel: float = 0.0
    vtype: str = "car"

    depart_time: float = 0.0
    arrival_time: float | None = None
    distance_travelled: float = 0.0
    # Roundabout-only: remaining arc length before this vehicle exits.
    exit_arc: float | None = None

    # Stop-start / emissions bookkeeping.
    is_stopped: bool = False
    stop_count: int = 0
    time_stopped: float = 0.0
    cum_co2_g: float = 0.0
    cum_nox_g: float = 0.0

    @property
    def rear(self) -> float:
        """Position of the rear bumper."""
        return self.position - self.length

    def update_stop_count(self, dt: float, stop_speed_threshold: float = 0.5) -> None:
        """Update stop/start bookkeeping given the vehicle's current speed.

        A "stop" is counted each time the vehicle transitions from moving
        to being (near-)stationary. This is the metric used to quantify
        stop-start driving, which is strongly correlated with excess CO2
        and NOx emissions relative to smooth-flow driving at the same
        average speed.
        """
        currently_stopped = self.speed < stop_speed_threshold
        if currently_stopped:
            self.time_stopped += dt
            if not self.is_stopped:
                self.stop_count += 1
        self.is_stopped = currently_stopped
