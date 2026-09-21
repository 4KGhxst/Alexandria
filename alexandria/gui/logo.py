"""An animated header emblem: three diamonds arranged like a tripod/peace
sign (one pointing straight up, the other two angled down-left and
down-right, each rotated to point outward from a shared center), spinning
via the faux-3D trick in logo_geometry.py, with a static wordmark
underneath.

Rendered as a wireframe — transparent interior, red outline only — via
Canvas's own fill="" (no fill drawn at all, so whatever's beneath shows
through). A second copy of the same three diamonds, in the exact same
red (no per-layer or facing-based shading — the whole emblem is one
uniform shade throughout the spin), sits at the same size, directly
behind the main one — not offset in screen space at all. "Behind" is
expressed as an actual depth coordinate fed into apply_spin_squish's
`depth` parameter: at the angles where the emblem faces the viewer
head-on, depth has zero effect, so the echo layer lands in the *exact
same place* as the front one (true occlusion, no visible duplicate);
only as the shape turns away from facing the viewer does the echo
visibly separate, which is what real parallax from an object with
actual depth looks like — a fixed pixel offset would be visible at every
angle instead, including head-on, which reads as a flat shadow rather
than depth. Connector lines are drawn between each corresponding corner
of the two shapes — the classic wireframe-box look, two matching outlines
with struts between them standing in for the edges a real 3D renderer
would draw between a front and back face; because both endpoints come
from the same depth-aware projection, the struts collapse to nothing at
the head-on angles too, exactly like the shapes they connect.

Every layer is driven off the exact same `self._angle` value in the same
`_animate()` tick, so there's a single source of truth for the rotation
and no possibility of layers drifting out of sync the way independently-
scheduled `after()` loops could.

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
    pinwheel_diamond_centers,
    pinwheel_diamond_rotation,
    rotate_points,
)

WORDMARK_TEXT = "MizuBibi"

# Scaled up 1.6x from the original 130/26/40/22/22 set — a uniform scale
# of every geometry constant around the same shared center, so the
# clipping-safety already established for those (see ARCHITECTURE.md)
# carries over rather than needing to be re-checked from scratch.
CANVAS_SIZE = 208
DIAMOND_WIDTH = 42
DIAMOND_HEIGHT = 64
PINWHEEL_RADIUS = 35
SPIN_DEGREES_PER_FRAME = 6
FRAME_MS = 40

OUTLINE_COLOR = "#ef4444"
OUTLINE_WIDTH = 2

# How far behind the front plane the echo layer actually sits, in the
# same faux-3D depth units apply_spin_squish uses — not a screen-space
# pixel offset. See the module docstring for why that distinction matters.
ECHO_DEPTH = 35.0
CONNECTOR_WIDTH = 1

WORDMARK_FONT_SIZE = 20


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
        self._center_y = CANVAS_SIZE / 2

        self.canvas = tk.Canvas(
            self, width=CANVAS_SIZE, height=CANVAS_SIZE, bg=theme.BG, highlightthickness=0
        )
        self.canvas.pack()

        self._diamonds: list[_Diamond] = []
        for i, center in enumerate(pinwheel_diamond_centers(self._axis_x, self._center_y, PINWHEEL_RADIUS)):
            rotation = pinwheel_diamond_rotation(i)
            # At angle 0 the depth term is zero, so front and echo start
            # out exactly coincident — no separate echo geometry needed
            # for this first static draw.
            points = rotate_points(
                diamond_points(center[0], center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT), center, rotation
            )

            # Drawn in back-to-front order so the main polygon's outline
            # ends up on top: echo first, then the connecting struts,
            # then the main polygon (tkinter Canvas stacks items in the
            # order they're created).
            echo_id = self.canvas.create_polygon(
                _flatten(points), fill="", outline=OUTLINE_COLOR, width=OUTLINE_WIDTH
            )
            connector_ids = [
                self.canvas.create_line(x, y, x, y, fill=OUTLINE_COLOR, width=CONNECTOR_WIDTH)
                for x, y in points
            ]
            polygon_id = self.canvas.create_polygon(
                _flatten(points), fill="", outline=OUTLINE_COLOR, width=OUTLINE_WIDTH
            )
            self._diamonds.append(_Diamond(polygon_id, echo_id, connector_ids, center, rotation))

        self.wordmark = tk.Label(
            self,
            text=WORDMARK_TEXT,
            bg=theme.BG,
            fg=OUTLINE_COLOR,
            font=(theme.FONT_FAMILY, WORDMARK_FONT_SIZE, "bold"),
        )
        self.wordmark.pack(pady=(4, 0))

        self._animate()

    def _animate(self) -> None:
        self._angle = (self._angle + SPIN_DEGREES_PER_FRAME) % 360

        for diamond in self._diamonds:
            base_points = rotate_points(
                diamond_points(diamond.center[0], diamond.center[1], DIAMOND_WIDTH, DIAMOND_HEIGHT),
                diamond.center,
                diamond.rotation,
            )
            front_points = apply_spin_squish(base_points, self._axis_x, self._angle, depth=0.0)
            echo_points = apply_spin_squish(base_points, self._axis_x, self._angle, depth=ECHO_DEPTH)

            self.canvas.coords(diamond.echo_id, _flatten(echo_points))

            for connector_id, (fx, fy), (ex, ey) in zip(diamond.connector_ids, front_points, echo_points):
                self.canvas.coords(connector_id, fx, fy, ex, ey)

            self.canvas.coords(diamond.polygon_id, _flatten(front_points))

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
