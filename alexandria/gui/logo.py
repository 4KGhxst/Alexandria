"""An animated header emblem: three diamonds arranged like a tripod/peace
sign (one pointing straight up, the other two angled down-left and
down-right, each rotated to point outward from a shared center), spinning
via the faux-3D trick in logo_geometry.py, with a static wordmark
underneath.

An original geometric design — not a reproduction of any brand's actual
trademarked logo artwork.
"""

from __future__ import annotations

import tkinter as tk

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

CANVAS_SIZE = 100
DIAMOND_WIDTH = 26
DIAMOND_HEIGHT = 40
PINWHEEL_RADIUS = 22
SPIN_DEGREES_PER_FRAME = 4
FRAME_MS = 40

# Each diamond keeps its own fixed color identity through the whole spin
# (darkened when facing away, never swapped for a different diamond's
# color) rather than the whole group sharing one color.
DIAMOND_COLORS = ["#2dd4bf", "#f5a524", "#f87171"]
BACK_SHADE_FACTOR = 0.5


class SpinningLogo(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=theme.BG)
        self._angle = 0.0

        self._axis_x = CANVAS_SIZE / 2
        center_y = CANVAS_SIZE / 2 - 6

        self.canvas = tk.Canvas(
            self, width=CANVAS_SIZE, height=CANVAS_SIZE, bg=theme.BG, highlightthickness=0
        )
        self.canvas.pack()

        self._diamonds: list[tuple[int, tuple[float, float], str, float]] = []
        centers = pinwheel_diamond_centers(self._axis_x, center_y, PINWHEEL_RADIUS)
        for i, (center, color) in enumerate(zip(centers, DIAMOND_COLORS)):
            rotation = pinwheel_diamond_rotation(i)
            points = rotate_points(
                diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT), center, rotation
            )
            polygon_id = self.canvas.create_polygon(_flatten(points), fill=color, outline="")
            self._diamonds.append((polygon_id, center, color, rotation))

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

        for polygon_id, center, base_color, rotation in self._diamonds:
            base_points = rotate_points(
                diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT), center, rotation
            )
            spun_points = apply_spin_squish(base_points, self._axis_x, self._angle)
            color = base_color if facing else shade_color(base_color, BACK_SHADE_FACTOR)
            self.canvas.coords(polygon_id, _flatten(spun_points))
            self.canvas.itemconfig(polygon_id, fill=color)

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
