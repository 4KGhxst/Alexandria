"""An animated header emblem: three diamonds arranged like a tripod/peace
sign (one pointing straight up, the other two angled down-left and
down-right, each rotated to point outward from a shared center), spinning
via the faux-3D trick in logo_geometry.py, with a static wordmark
underneath.

Rendered as a wireframe — transparent interior, red outline only — via
Canvas's own fill="" (no fill drawn at all, so whatever's beneath shows
through), rather than the solid-filled/fake-extruded look from an
earlier iteration. logo_geometry.py's extrusion helpers (offset_points,
extrusion_side_quads) are still there and tested if that depth effect
gets reused for something later; this widget just doesn't call them
right now.

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
    is_facing_viewer,
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

OUTLINE_COLOR = "#ef4444"
OUTLINE_WIDTH = 2
BACK_SHADE_FACTOR = 0.5  # how much darker the outline gets when facing away


@dataclass
class _Diamond:
    polygon_id: int
    center: tuple[float, float]
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
        for i, center in enumerate(centers):
            rotation = pinwheel_diamond_rotation(i)
            points = rotate_points(
                diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT), center, rotation
            )
            polygon_id = self.canvas.create_polygon(
                _flatten(points), fill="", outline=OUTLINE_COLOR, width=OUTLINE_WIDTH
            )
            self._diamonds.append(_Diamond(polygon_id, center, rotation))

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
        outline_color = OUTLINE_COLOR if facing else shade_color(OUTLINE_COLOR, BACK_SHADE_FACTOR)

        for diamond in self._diamonds:
            base_points = rotate_points(
                diamond_points(diamond.center[0], diamond.center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT),
                diamond.center,
                diamond.rotation,
            )
            spun_points = apply_spin_squish(base_points, self._axis_x, self._angle)
            self.canvas.coords(diamond.polygon_id, _flatten(spun_points))
            self.canvas.itemconfig(diamond.polygon_id, outline=outline_color)

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
