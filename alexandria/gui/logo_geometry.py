"""Pure geometry for the spinning emblem — no tkinter import, so the math
is unit-testable without a display or tkinter installed at all (this dev
sandbox has neither). logo.py turns this into an actual animated Canvas.

The "3D spin" is a classic 2D-canvas trick: scale every point's x-offset
from a shared center by cos(angle) each frame. A flat shape scaled that
way reads as a rigid object rotating in 3D around a vertical axis — it
flattens to a sliver at the 90/270 degree edge-on points and can swap to
a different shade past that, the same illusion as a spinning coin.

The three-diamond pinwheel arrangement here is an original layout built
from scratch (three diamonds 120 degrees apart around a center point),
not a reproduction of any brand's actual logo artwork.
"""

from __future__ import annotations

import math

Point = tuple[float, float]


def diamond_points(center_x: float, center_y: float, width: float, height: float) -> list[Point]:
    """A single diamond/rhombus centered at (center_x, center_y)."""
    return [
        (center_x, center_y - height / 2),
        (center_x + width / 2, center_y),
        (center_x, center_y + height / 2),
        (center_x - width / 2, center_y),
    ]


def pinwheel_diamond_centers(center_x: float, center_y: float, radius: float) -> list[Point]:
    """Centers for three diamonds arranged 120 degrees apart around a
    shared center, starting pointing straight up."""
    centers = []
    for i in range(3):
        angle = math.radians(90 + i * 120)
        centers.append((center_x + radius * math.cos(angle), center_y - radius * math.sin(angle)))
    return centers


def apply_spin_squish(points: list[Point], axis_x: float, angle_degrees: float) -> list[Point]:
    """Horizontally scales each point's offset from a shared vertical axis
    by cos(angle) — the faux-3D spin. Returns new points; doesn't mutate
    the input list."""
    scale_x = math.cos(math.radians(angle_degrees))
    return [(axis_x + (x - axis_x) * scale_x, y) for x, y in points]


def is_facing_viewer(angle_degrees: float) -> bool:
    """Which "face" of the spin should be showing right now — used to
    swap between a lighter/darker shade as a cheap lighting cue."""
    return math.cos(math.radians(angle_degrees)) >= 0
