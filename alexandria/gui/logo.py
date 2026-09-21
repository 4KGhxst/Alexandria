"""An animated header emblem: three diamonds in a pinwheel, spinning via
the faux-3D trick in logo_geometry.py, with a static wordmark underneath.

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
)

WORDMARK_TEXT = "MizuBibi"

CANVAS_SIZE = 100
DIAMOND_WIDTH = 26
DIAMOND_HEIGHT = 40
PINWHEEL_RADIUS = 22
SPIN_DEGREES_PER_FRAME = 4
FRAME_MS = 40

FRONT_COLOR = theme.ACCENT
BACK_COLOR = "#1b6f66"  # a darker shade of the accent, for the "back face"


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

        self._diamonds: list[tuple[int, tuple[float, float]]] = []
        for center in pinwheel_diamond_centers(self._axis_x, center_y, PINWHEEL_RADIUS):
            points = diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT)
            polygon_id = self.canvas.create_polygon(_flatten(points), fill=FRONT_COLOR, outline="")
            self._diamonds.append((polygon_id, center))

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
        color = FRONT_COLOR if is_facing_viewer(self._angle) else BACK_COLOR

        for polygon_id, center in self._diamonds:
            base_points = diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT)
            spun_points = apply_spin_squish(base_points, self._axis_x, self._angle)
            self.canvas.coords(polygon_id, _flatten(spun_points))
            self.canvas.itemconfig(polygon_id, fill=color)

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
