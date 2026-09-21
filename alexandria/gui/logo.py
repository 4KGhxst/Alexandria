"""An animated header emblem: three diamonds arranged like a tripod/peace
sign (one pointing straight up, the other two angled down-left and
down-right, each rotated to point outward from a shared center), spinning
via the faux-3D trick in logo_geometry.py, with a static wordmark
underneath.

Each diamond is also fake-extruded along a fixed screen-space depth
offset — the classic 90s-CGI-logo trick: a darker "side wall" quad per
edge, connecting the flat front face to a copy of itself offset by
(EXTRUDE_DX, EXTRUDE_DY), drawn *before* the front face so the front
face's fill covers the seam. No real 3D/Z-axis involved, just layered 2D
shapes that read as one.

An original geometric design — not a reproduction of any brand's actual
trademarked logo artwork.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass

from alexandria.gui import theme
from alexandria.gui.logo_geometry import (
    apply_spin_squish,
    diamond_points,
    extrusion_side_quads,
    is_facing_viewer,
    offset_points,
    pinwheel_diamond_centers,
    pinwheel_diamond_rotation,
    rotate_points,
    shade_color,
)

WORDMARK_TEXT = "MizuBibi"

CANVAS_SIZE = 110
DIAMOND_WIDTH = 26
DIAMOND_HEIGHT = 40
PINWHEEL_RADIUS = 22
SPIN_DEGREES_PER_FRAME = 4
FRAME_MS = 40

# Fixed screen-space depth offset for the fake extrusion — deliberately
# NOT re-rotated with the spin; a constant bevel direction reads fine
# stylistically and keeps the math simple.
EXTRUDE_DX = 5
EXTRUDE_DY = 6
SIDE_SHADE_FACTOR = 0.45

# Each diamond keeps its own fixed color identity through the whole spin
# (darkened when facing away, never swapped for a different diamond's
# color) rather than the whole group sharing one color.
DIAMOND_COLORS = ["#2dd4bf", "#f5a524", "#f87171"]
BACK_SHADE_FACTOR = 0.5


@dataclass
class _Diamond:
    front_id: int
    side_ids: list[int]
    center: tuple[float, float]
    base_color: str
    rotation: float


class SpinningLogo(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=theme.BG)
        self._angle = 0.0

        self._axis_x = CANVAS_SIZE / 2
        self._center_y = CANVAS_SIZE / 2 - 6

        self.canvas = tk.Canvas(
            self, width=CANVAS_SIZE, height=CANVAS_SIZE, bg=theme.BG, highlightthickness=0
        )
        self.canvas.pack()

        self._diamonds: list[_Diamond] = []
        centers = pinwheel_diamond_centers(self._axis_x, self._center_y, PINWHEEL_RADIUS)
        for i, (center, color) in enumerate(zip(centers, DIAMOND_COLORS)):
            rotation = pinwheel_diamond_rotation(i)
            front_points = rotate_points(
                diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT), center, rotation
            )
            back_points = offset_points(front_points, EXTRUDE_DX, EXTRUDE_DY)
            side_color = shade_color(color, SIDE_SHADE_FACTOR)

            # Side walls drawn first so the front face's fill (created
            # after, thus stacked on top) covers the seam between them.
            side_ids = [
                self.canvas.create_polygon(_flatten(quad), fill=side_color, outline="")
                for quad in extrusion_side_quads(front_points, back_points)
            ]
            front_id = self.canvas.create_polygon(_flatten(front_points), fill=color, outline="")

            self._diamonds.append(_Diamond(front_id, side_ids, center, color, rotation))

        self.wordmark = tk.Label(
            self,
            text=WORDMARK_TEXT,
            bg=theme.BG,
            fg=theme.ENTRY_TEXT,
            font=(theme.FONT_FAMILY, 13, "bold"),
        )
        self.wordmark.pack(pady=(2, 0))

        self._animate()

    def _animate(self) -> None:
        self._angle = (self._angle + SPIN_DEGREES_PER_FRAME) % 360
        facing = is_facing_viewer(self._angle)

        for diamond in self._diamonds:
            base_points = rotate_points(
                diamond_points(diamond.center[0], diamond.center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT),
                diamond.center,
                diamond.rotation,
            )
            front_points = apply_spin_squish(base_points, self._axis_x, self._angle)
            back_points = offset_points(front_points, EXTRUDE_DX, EXTRUDE_DY)

            front_color = diamond.base_color if facing else shade_color(diamond.base_color, BACK_SHADE_FACTOR)
            side_color = shade_color(front_color, SIDE_SHADE_FACTOR)

            quads = extrusion_side_quads(front_points, back_points)
            for side_id, quad in zip(diamond.side_ids, quads):
                self.canvas.coords(side_id, _flatten(quad))
                self.canvas.itemconfig(side_id, fill=side_color)

            self.canvas.coords(diamond.front_id, _flatten(front_points))
            self.canvas.itemconfig(diamond.front_id, fill=front_color)

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
