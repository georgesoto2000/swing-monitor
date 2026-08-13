"""Derived swing metrics computed from buffered ACCEL/GYRO samples.

These are first-pass metrics: a peak (max magnitude) over whatever samples
are currently buffered, with no swing-event segmentation (address/top/
impact/finish) yet. That means they describe the visible window as a
whole rather than a single detected swing — a starting point ahead of the
README's "Swing event detection" project-plan step, not a replacement
for it.
"""

import math
from typing import NamedTuple

# The sensor sits a fixed distance up from the clubface regardless of
# club — only the hands-to-sensor segment changes with club length. That
# segment is measured for PW and extrapolated for the rest using the
# ~0.5" length step typical between adjacent iron numbers.
SENSOR_TO_CLUBFACE_M = 0.1
_MEASURED_HAND_TO_SENSOR_PW_M = 0.75
_IRON_LENGTH_STEP_M = 0.0127  # ~0.5"

# Ordered PW (shortest) -> 5-iron (longest).
CLUBS = ["PW", "9i", "8i", "7i", "6i", "5i"]

# Full lever arm (hands to clubface) per club, used to turn the sensor's
# angular velocity into an estimated clubhead speed. The per-club step is
# a rough extrapolation, not individually measured — see the README's
# "Calibration & validation" project-plan step.
CLUB_LEVER_ARM_M = {
    club: _MEASURED_HAND_TO_SENSOR_PW_M + i * _IRON_LENGTH_STEP_M + SENSOR_TO_CLUBFACE_M
    for i, club in enumerate(CLUBS)
}


class PeakSample(NamedTuple):
    """The largest-magnitude sample in a buffer, plus its local sharpness."""

    magnitude: float
    time: float
    sharpness: float | None


def magnitude(row: dict) -> float:
    """Return the Euclidean magnitude of a row's x/y/z fields."""
    return math.sqrt(row["x"] ** 2 + row["y"] ** 2 + row["z"] ** 2)


def peak_sample(rows: list[dict]) -> PeakSample | None:
    """Return the row with the largest |x,y,z| vector, or None if empty.

    ``sharpness`` is the centred slope of the magnitude (units/s) across
    the peak's immediate neighbours in the buffer — how fast the signal
    rises and falls through the peak. It's None at the very ends of the
    buffer, where there's no neighbour on one side.
    """
    if not rows:
        return None
    mags = [magnitude(r) for r in rows]
    idx = max(range(len(mags)), key=lambda i: mags[i])

    sharpness = None
    if 0 < idx < len(mags) - 1:
        dt = rows[idx + 1]["time"] - rows[idx - 1]["time"]
        if dt > 0:
            sharpness = (mags[idx + 1] - mags[idx - 1]) / dt

    return PeakSample(magnitude=mags[idx], time=rows[idx]["time"], sharpness=sharpness)


def estimated_clubhead_speed_mps(peak_gyro_rad_s: float, lever_arm_m: float) -> float:
    """Estimate clubhead speed (m/s) from a peak angular velocity (rad/s).

    Scales by ``lever_arm_m`` — the hands-to-clubface distance for the
    club in use, see ``CLUB_LEVER_ARM_M``.
    """
    return peak_gyro_rad_s * lever_arm_m
