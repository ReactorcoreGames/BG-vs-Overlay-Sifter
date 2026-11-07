"""Where things go, as plain numbers. Integer pixels, origin top-left."""
from __future__ import annotations

from typing import NamedTuple

# In Tab-cycle order. Windows' "Span" is deliberately absent: it stretches one image
# across several monitors, so on a single canvas it is identical to Fill and would make
# Tab look broken on that step.
FIT_MODES = ("fill", "fit", "stretch", "tile", "center")
FIT_LABELS = {
    "fill": "Fill",
    "fit": "Fit",
    "stretch": "Stretch",
    "tile": "Tile",
    "center": "Centre",
}

# In reading order, so the panel can lay them out as a 3x3 grid directly.
ANCHOR_FRACTIONS = {
    "top-left": (0.0, 0.0),
    "top": (0.5, 0.0),
    "top-right": (1.0, 0.0),
    "left": (0.0, 0.5),
    "center": (0.5, 0.5),
    "right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0),
    "bottom": (0.5, 1.0),
    "bottom-right": (1.0, 1.0),
}
ANCHORS = tuple(ANCHOR_FRACTIONS)

ASPECTS = {
    "16:9": (16, 9),
    "9:16": (9, 16),
    "4:3": (4, 3),
    "1:1": (1, 1),
    "3:2": (3, 2),
    "2:3": (2, 3),
}
RESOLUTIONS = (360, 480, 540, 720, 1080)
MAX_CANVAS = 16384


class Placement(NamedTuple):
    x: int
    y: int
    width: int
    height: int


def preset_size(aspect: str, resolution: int) -> tuple[int, int]:
    """A preset's pixels. "1080p" names the short edge, so 9:16 at 1080p is 1080x1920.

    The long edge rounds to even, which gives the conventional 854x480 rather than 853.
    """
    a, b = ASPECTS[aspect]
    long_edge = 2 * round(resolution * max(a, b) / min(a, b) / 2)
    return (long_edge, resolution) if a >= b else (resolution, long_edge)


def background_placement(
    background: tuple[int, int], canvas: tuple[int, int], fit_mode: str
) -> Placement:
    """How the background lands on the canvas. Overflow simply crops at the canvas edge.

    For `tile` this is the tile's own size at the origin; the caller repeats it.
    """
    bg_w, bg_h = background
    canvas_w, canvas_h = canvas

    if fit_mode == "stretch":
        return Placement(0, 0, canvas_w, canvas_h)
    if fit_mode == "tile":
        return Placement(0, 0, bg_w, bg_h)
    if fit_mode == "center":
        return Placement(round((canvas_w - bg_w) / 2), round((canvas_h - bg_h) / 2), bg_w, bg_h)

    pick = max if fit_mode == "fill" else min
    scale = pick(canvas_w / bg_w, canvas_h / bg_h)
    width = max(1, round(bg_w * scale))
    height = max(1, round(bg_h * scale))
    return Placement(round((canvas_w - width) / 2), round((canvas_h - height) / 2), width, height)


def overlay_position(
    overlay: tuple[int, int],
    canvas: tuple[int, int],
    anchor: str,
    offset: tuple[int, int],
) -> tuple[int, int]:
    """The anchor names the same point on canvas and overlay, then the offset nudges.

    Top-left with offset (20, 20) puts the overlay's corner 20px in from the canvas's,
    whatever the canvas size. The result may be negative: overlays never scale, so one
    larger than the canvas crops at the edges.
    """
    fx, fy = ANCHOR_FRACTIONS[anchor]
    return (
        round((canvas[0] - overlay[0]) * fx) + offset[0],
        round((canvas[1] - overlay[1]) * fy) + offset[1],
    )


def fit_view(canvas: tuple[int, int], view: tuple[int, int]) -> tuple[int, int]:
    """The canvas's size on screen: always fits the window, scaling up or down."""
    scale = min(view[0] / canvas[0], view[1] / canvas[1])
    return (max(1, round(canvas[0] * scale)), max(1, round(canvas[1] * scale)))
