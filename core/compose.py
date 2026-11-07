"""Background plus overlay in, finished frame out.

There is one render path, as in the prototype: composite at canvas resolution, then
resample to the window. The two steps use the same resampling filter, so Nearest stays
crisp all the way to the screen.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .placement import background_placement, fit_view, overlay_position

RESAMPLING = {"lanczos": Image.LANCZOS, "nearest": Image.NEAREST}


@dataclass(frozen=True)
class RenderSpec:
    """Everything a frame depends on besides its two images. Hashable: part of the cache key."""

    fit_mode: str = "fill"
    fill_colour: str = "#000000"
    canvas: tuple[int, int] | None = None  # None means match the overlay
    anchor: str = "center"
    offset: tuple[int, int] = (0, 0)
    resample: str = "lanczos"
    view: tuple[int, int] = (1280, 720)


def load_background(path: Path) -> Image.Image:
    """RGB, or RGBA if the file has transparency for the fill colour to show through."""
    with Image.open(path) as handle:
        return handle.convert("RGBA" if handle.has_transparency_data else "RGB")


def load_overlay(path: Path) -> Image.Image:
    with Image.open(path) as handle:
        return handle.convert("RGBA")


def resolve_canvas(
    spec: RenderSpec, background: Image.Image, overlay: Image.Image | None
) -> tuple[int, int]:
    """The chosen canvas; or the overlay's size, as the prototype did; or with no overlay, the BG's."""
    if spec.canvas is not None:
        return spec.canvas
    return overlay.size if overlay is not None else background.size


def _paste(canvas: Image.Image, image: Image.Image, position: tuple[int, int]) -> None:
    """Blend onto the opaque canvas. `paste` clips negative and overflowing positions itself."""
    canvas.paste(image, position, image if image.mode == "RGBA" else None)


def _tiled(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Repeat by doubling, so a 1x1 tile costs a few pastes rather than two million."""
    layer = Image.new(image.mode, size)
    layer.paste(image, (0, 0))
    width, height = image.size
    while width < size[0]:
        layer.paste(layer.crop((0, 0, width, height)), (width, 0))
        width *= 2
    while height < size[1]:
        layer.paste(layer.crop((0, 0, size[0], height)), (0, height))
        height *= 2
    return layer


def compose_canvas(
    background: Image.Image, overlay: Image.Image | None, spec: RenderSpec
) -> Image.Image:
    """The composite at full canvas resolution, always opaque RGB."""
    size = resolve_canvas(spec, background, overlay)
    canvas = Image.new("RGB", size, spec.fill_colour)

    if spec.fit_mode == "tile":
        _paste(canvas, _tiled(background, size), (0, 0))
    else:
        x, y, width, height = background_placement(background.size, size, spec.fit_mode)
        scaled = background
        if (width, height) != background.size:
            scaled = background.resize((width, height), RESAMPLING[spec.resample])
        _paste(canvas, scaled, (x, y))

    if overlay is not None:
        _paste(canvas, overlay, overlay_position(overlay.size, size, spec.anchor, spec.offset))
    return canvas


def render_frame(
    background: Image.Image, overlay: Image.Image | None, spec: RenderSpec
) -> tuple[Image.Image, tuple[int, int]]:
    """The composite resampled to the window. Returns it with the canvas size it came from."""
    canvas = compose_canvas(background, overlay, spec)
    target = fit_view(canvas.size, spec.view)
    if target == canvas.size:
        return canvas, canvas.size
    return canvas.resize(target, RESAMPLING[spec.resample]), canvas.size
