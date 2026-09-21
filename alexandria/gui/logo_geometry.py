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


def pinwheel_diamond_rotation(index: int) -> float:
    """The rotation (degrees) that points a diamond's long axis radially
    outward at pinwheel position `index` (0, 1, 2) — matching
    pinwheel_diamond_centers' spacing, so each diamond's shape points the
    same direction its center sits away from the shared axis (one
    straight up, the other two angled down-left/down-right), instead of
    every diamond staying upright regardless of where it's positioned."""
    return -index * 120


def rotate_points(points: list[Point], center: Point, angle_degrees: float) -> list[Point]:
    """Rotates points around `center` by angle_degrees, clockwise in
    standard screen coordinates (y increases downward). Returns new
    points; doesn't mutate the input."""
    theta = math.radians(angle_degrees)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    center_x, center_y = center
    rotated = []
    for x, y in points:
        dx, dy = x - center_x, y - center_y
        rotated.append((center_x + dx * cos_t - dy * sin_t, center_y + dx * sin_t + dy * cos_t))
    return rotated


def apply_spin_squish(points: list[Point], axis_x: float, angle_degrees: float) -> list[Point]:
    """Horizontally scales each point's offset from a shared vertical axis
    by cos(angle) — the faux-3D spin. Returns new points; doesn't mutate
    the input list."""
    scale_x = math.cos(math.radians(angle_degrees))
    return [(axis_x + (x - axis_x) * scale_x, y) for x, y in points]


def is_facing_viewer(angle_degrees: float) -> bool:
    """Which "face" of the spin should be showing right now — used to
    darken each diamond's own color as a cheap lighting cue."""
    return math.cos(math.radians(angle_degrees)) >= 0


def offset_points(points: list[Point], dx: float, dy: float) -> list[Point]:
    """Translates every point by (dx, dy) — used to build the "back" face
    of a fake-extruded shape a fixed distance behind the front face, the
    classic 90s-CGI-logo trick for turning a flat shape into a solid-
    looking one without any real 3D rendering."""
    return [(x + dx, y + dy) for x, y in points]


def extrusion_side_quads(front_points: list[Point], back_points: list[Point]) -> list[list[Point]]:
    """Builds one quad per edge connecting corresponding front/back
    points — the "side walls" of a fake-extruded shape, filled with a
    darker shade to read as depth. front_points and back_points must be
    the same length and in matching order (e.g. both from diamond_points
    or a transformed copy of it)."""
    count = len(front_points)
    return [
        [front_points[i], front_points[(i + 1) % count], back_points[(i + 1) % count], back_points[i]]
        for i in range(count)
    ]


def shade_color(hex_color: str, factor: float) -> str:
    """Darkens (factor < 1) or lightens (factor > 1, clamped to 255) a
    "#rrggbb" color by a multiplier — used to shade each diamond's own
    fixed color when it's facing away, instead of swapping to some other
    shared color, so every diamond keeps its own identity through the
    whole spin."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (min(255, max(0, round(channel * factor))) for channel in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"
