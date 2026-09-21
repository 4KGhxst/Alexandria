"""A full-window background emblem: three diamonds arranged like a
tripod/peace sign (one pointing straight up, the other two angled
down-left and down-right, each rotated to point outward from a shared
center), spinning via the faux-3D trick in logo_geometry.py, with a
wordmark underneath that spins and color-matches in sync.

Rendered as a wireframe — transparent interior, red outline only — via
Canvas's own fill="" (no fill drawn at all, so whatever's beneath shows
through). A second, dimmer copy of the same three diamonds sits at the
same size, directly behind the main one — not offset in screen space at
all. "Behind" is expressed as an actual depth coordinate fed into
apply_spin_squish's `depth` parameter: at the angles where the emblem
faces the viewer head-on, depth has zero effect, so the echo layer lands
in the *exact same place* as the front one (true occlusion, no visible
duplicate); only as the shape turns away from facing the viewer does the
echo visibly separate, which is what real parallax from an object with
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

The canvas fills whatever widget it's placed in (meant to be the whole
app window, as its own background layer, with the rest of the UI placed
on top of it) and re-centers/rescales the whole emblem on every resize —
see `_on_resize` and logo_geometry.scale_for_canvas. All the size
constants below (diamond size, pinwheel radius, echo depth, font size)
are tuned for a `CANVAS_SIZE`-pixel square and get multiplied by the
live scale factor each frame, so the emblem grows and shrinks with the
window instead of staying pinned to its original header size.

The wordmark is a genuine Canvas text item (not a separate widget)
because it needs to sit inside the same coordinate space as the diamonds
and rotate/recolor every frame. It can't be squished the way the diamond
polygons are — Canvas text glyphs don't stretch via the scale trick that
sells the diamonds' faux-3D spin, `.scale()` on a text item only moves
its anchor point, not its glyph shapes — so instead of faking a broken
squish, it does a genuine in-plane rotation using Tk 8.6+'s native
`angle` option on `create_text`, synced to the same `self._angle`, with
its fill color matching the diamonds' current (possibly back-shaded)
outline color.

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
    scale_for_canvas,
    shade_color,
)

WORDMARK_TEXT = "MizuBibi"

# All of these are tuned for a CANVAS_SIZE-pixel square canvas; actual
# on-screen sizes are these times the live self._scale (see _on_resize).
CANVAS_SIZE = 130
DIAMOND_WIDTH = 26
DIAMOND_HEIGHT = 40
PINWHEEL_RADIUS = 22
WORDMARK_OFFSET_Y = 60  # how far below the shared center the wordmark sits
WORDMARK_FONT_SIZE = 13

SPIN_DEGREES_PER_FRAME = 6
FRAME_MS = 40

OUTLINE_COLOR = "#ef4444"
OUTLINE_WIDTH = 2
BACK_SHADE_FACTOR = 0.5  # how much darker the outline gets when facing away

# How far behind the front plane the echo layer actually sits, in the
# same faux-3D depth units apply_spin_squish uses — not a screen-space
# pixel offset. See the module docstring for why that distinction matters.
ECHO_DEPTH = 22.0
ECHO_SHADE_FACTOR = 0.45
CONNECTOR_WIDTH = 1


@dataclass
class _Diamond:
    index: int
    polygon_id: int
    echo_id: int
    connector_ids: list[int]


class SpinningLogo(tk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=theme.BG)
        self._angle = 0.0

        # Placeholder layout until the first <Configure> event reports the
        # canvas's real size — _animate() re-derives every point from
        # these each frame, so this only matters for the very first draw.
        self._axis_x = CANVAS_SIZE / 2
        self._center_y = CANVAS_SIZE / 2
        self._scale = 1.0

        self.canvas = tk.Canvas(self, bg=theme.BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        echo_outline = shade_color(OUTLINE_COLOR, ECHO_SHADE_FACTOR)
        placeholder = [0.0, 0.0] * 4
        self._diamonds: list[_Diamond] = []
        for i in range(3):
            # Drawn in back-to-front order so the main polygon's outline
            # ends up on top: echo first, then the connecting struts,
            # then the main polygon (tkinter Canvas stacks items in the
            # order they're created). Real coordinates get filled in by
            # the first _animate() call below.
            echo_id = self.canvas.create_polygon(
                placeholder, fill="", outline=echo_outline, width=OUTLINE_WIDTH
            )
            connector_ids = [
                self.canvas.create_line(0, 0, 0, 0, fill=echo_outline, width=CONNECTOR_WIDTH)
                for _ in range(4)
            ]
            polygon_id = self.canvas.create_polygon(
                placeholder, fill="", outline=OUTLINE_COLOR, width=OUTLINE_WIDTH
            )
            self._diamonds.append(_Diamond(i, polygon_id, echo_id, connector_ids))

        self._wordmark_id = self.canvas.create_text(
            self._axis_x,
            self._center_y + WORDMARK_OFFSET_Y,
            text=WORDMARK_TEXT,
            fill=OUTLINE_COLOR,
            font=(theme.FONT_FAMILY, WORDMARK_FONT_SIZE, "bold"),
            angle=0,
        )

        self._animate()

    def _on_resize(self, event: object) -> None:
        self._axis_x = event.width / 2
        self._center_y = event.height / 2
        self._scale = scale_for_canvas(event.width, event.height, base_size=CANVAS_SIZE)

    def _animate(self) -> None:
        self._angle = (self._angle + SPIN_DEGREES_PER_FRAME) % 360
        facing = is_facing_viewer(self._angle)
        outline_color = OUTLINE_COLOR if facing else shade_color(OUTLINE_COLOR, BACK_SHADE_FACTOR)
        echo_outline_color = shade_color(outline_color, ECHO_SHADE_FACTOR)

        scale = self._scale
        diamond_width = DIAMOND_WIDTH * scale
        diamond_height = DIAMOND_HEIGHT * scale
        pinwheel_radius = PINWHEEL_RADIUS * scale
        echo_depth = ECHO_DEPTH * scale

        centers = pinwheel_diamond_centers(self._axis_x, self._center_y, pinwheel_radius)

        for diamond in self._diamonds:
            center = centers[diamond.index]
            rotation = pinwheel_diamond_rotation(diamond.index)
            base_points = rotate_points(
                diamond_points(center[0], center[1], diamond_width, diamond_height),
                center,
                rotation,
            )
            front_points = apply_spin_squish(base_points, self._axis_x, self._angle, depth=0.0)
            echo_points = apply_spin_squish(base_points, self._axis_x, self._angle, depth=echo_depth)

            self.canvas.coords(diamond.echo_id, _flatten(echo_points))
            self.canvas.itemconfig(diamond.echo_id, outline=echo_outline_color)

            for connector_id, (fx, fy), (ex, ey) in zip(diamond.connector_ids, front_points, echo_points):
                self.canvas.coords(connector_id, fx, fy, ex, ey)
                self.canvas.itemconfig(connector_id, fill=echo_outline_color)

            self.canvas.coords(diamond.polygon_id, _flatten(front_points))
            self.canvas.itemconfig(diamond.polygon_id, outline=outline_color)

        self.canvas.coords(self._wordmark_id, self._axis_x, self._center_y + WORDMARK_OFFSET_Y * scale)
        self.canvas.itemconfig(
            self._wordmark_id,
            fill=outline_color,
            angle=self._angle,
            font=(theme.FONT_FAMILY, max(1, round(WORDMARK_FONT_SIZE * scale)), "bold"),
        )

        self.after(FRAME_MS, self._animate)


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [coordinate for point in points for coordinate in point]
