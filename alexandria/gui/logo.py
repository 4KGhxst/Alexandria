"""An animated header emblem: three diamonds arranged like a tripod/peace
sign (one pointing straight up, the other two angled down-left and
down-right, each rotated to point outward from a shared center), spinning
via the faux-3D trick in logo_geometry.py, with a static wordmark
underneath.

Rendered as a wireframe — transparent interior, red outline only — via
Canvas's own fill="" (no fill drawn at all, so whatever's beneath shows
through). A second, dimmer copy of the same three diamonds sits directly
above the main one (offset only vertically, so both share the same
horizontal axis) as an echo layer, with connector lines drawn between
each corresponding corner of the main and echo shapes — the classic
wireframe-box look: two matching outlines with straight struts between
them, standing in for edges a real 3D renderer would draw between a front
and back face. Every layer is driven off the exact same `self._angle`
value in the same `_animate()` tick, so there's a single source of truth
for the rotation and no possibility of layers drifting out of sync the
way independently-scheduled `after()` loops could.

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
    offset_points,
    pinwheel_diamond_centers,
    pinwheel_diamond_rotation,
    rotate_points,
    scale_points,
    shade_color,
)

WORDMARK_TEXT = "MizuBibi"

CANVAS_SIZE = 140
DIAMOND_WIDTH = 26
DIAMOND_HEIGHT = 40
PINWHEEL_RADIUS = 22
SPIN_DEGREES_PER_FRAME = 4
FRAME_MS = 40

OUTLINE_COLOR = "#ef4444"
OUTLINE_WIDTH = 2
BACK_SHADE_FACTOR = 0.5  # how much darker the outline gets when facing away

# The echo copy: shifted straight up (no horizontal offset, so it lines
# up evenly on the same axis as the main logo instead of sitting
# diagonally offset from it) AND scaled down around the shared axis
# center — the combination is what reads as real distance rather than a
# same-size shape nudged sideways (which just looks like a shadow, not a
# second layer sitting farther back in space).
ECHO_OFFSET_X = 0
ECHO_OFFSET_Y = -26
ECHO_SCALE = 0.72
ECHO_SHADE_FACTOR = 0.45
CONNECTOR_WIDTH = 1


@dataclass
class _Diamond:
    polygon_id: int
    echo_id: int
    connector_ids: list[int]
    center: tuple[float, float]
    rotation: float


class SpinningLogo(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=theme.BG)
        self._angle = 0.0

        self._axis_x = CANVAS_SIZE / 2
        # Pushed down from center (rather than the old "- 6") to leave
        # headroom above for the echo layer, which now sits noticeably
        # higher up (see ECHO_OFFSET_Y) to read as real depth.
        self._center_y = CANVAS_SIZE / 2 + 10

        self.canvas = tk.Canvas(
            self, width=CANVAS_SIZE, height=CANVAS_SIZE, bg=theme.BG, highlightthickness=0
        )
        self.canvas.pack()

        layout = []
        for i, center in enumerate(pinwheel_diamond_centers(self._axis_x, self._center_y, PINWHEEL_RADIUS)):
            rotation = pinwheel_diamond_rotation(i)
            points = rotate_points(
                diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT), center, rotation
            )
            layout.append((center, rotation, points))

        echo_outline = shade_color(OUTLINE_COLOR, ECHO_SHADE_FACTOR)
        self._diamonds: list[_Diamond] = []
        for center, rotation, points in layout:
            echo_points = self._echo_points(points)

            # Drawn in back-to-front order so the main polygon's outline
            # ends up on top: echo first, then the connecting struts,
            # then the main polygon (tkinter Canvas stacks items in the
            # order they're created).
            echo_id = self.canvas.create_polygon(
                _flatten(echo_points), fill="", outline=echo_outline, width=OUTLINE_WIDTH
            )
            connector_ids = [
                self.canvas.create_line(fx, fy, ex, ey, fill=echo_outline, width=CONNECTOR_WIDTH)
                for (fx, fy), (ex, ey) in zip(points, echo_points)
            ]
            polygon_id = self.canvas.create_polygon(
                _flatten(points), fill="", outline=OUTLINE_COLOR, width=OUTLINE_WIDTH
            )
            self._diamonds.append(_Diamond(polygon_id, echo_id, connector_ids, center, rotation))

        self.wordmark = tk.Label(
            self,
            text=WORDMARK_TEXT,
            bg=theme.BG,
            fg=theme.ENTRY_TEXT,
            font=(theme.FONT_FAMILY, 13, "bold"),
        )
        self.wordmark.pack(pady=(2, 0))

        self._animate()

    def _echo_points(self, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Scale-then-shift: shrink toward the shared axis (perspective —
        smaller reads as farther away), then nudge up, so the echo layer
        looks like real distance rather than a same-size shape shifted
        sideways."""
        scaled = scale_points(points, (self._axis_x, self._center_y), ECHO_SCALE)
        return offset_points(scaled, ECHO_OFFSET_X, ECHO_OFFSET_Y)

    def _animate(self) -> None:
        self._angle = (self._angle + SPIN_DEGREES_PER_FRAME) % 360
        facing = is_facing_viewer(self._angle)
        outline_color = OUTLINE_COLOR if facing else shade_color(OUTLINE_COLOR, BACK_SHADE_FACTOR)
        echo_outline_color = shade_color(outline_color, ECHO_SHADE_FACTOR)

        for diamond in self._diamonds:
            base_points = rotate_points(
                diamond_points(diamond.center[0], diamond.center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT),
                diamond.center,
                diamond.rotation,
            )
            spun_points = apply_spin_squish(base_points, self._axis_x, self._angle)
            echo_points = self._echo_points(spun_points)

            self.canvas.coords(diamond.echo_id, _flatten(echo_points))
            self.canvas.itemconfig(diamond.echo_id, outline=echo_outline_color)

            for connector_id, (fx, fy), (ex, ey) in zip(diamond.connector_ids, spun_points, echo_points):
                self.canvas.coords(connector_id, fx, fy, ex, ey)
                self.canvas.itemconfig(connector_id, fill=echo_outline_color)

            self.canvas.coords(diamond.polygon_id, _flatten(spun_points))
            self.canvas.itemconfig(diamond.polygon_id, outline=outline_color)

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
