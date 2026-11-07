"""Offline tests over core/: the maths, compositing, config, and the guard on scope."""
import ast
import json
from pathlib import Path

import pytest
from PIL import Image

from core.cache import LRUCache, prefetch_order
from core.compose import RenderSpec, compose_canvas, render_frame
from core.placement import ANCHORS, background_placement, fit_view, overlay_position, preset_size
from core.settings import Settings, load_settings, save_settings

ROOT = Path(__file__).resolve().parent.parent
RED, BLUE, GREEN = (255, 0, 0), (0, 0, 255), (0, 255, 0)


@pytest.mark.parametrize(
    "aspect, resolution, expected",
    [
        ("16:9", 1080, (1920, 1080)),
        ("9:16", 1080, (1080, 1920)),
        ("16:9", 480, (854, 480)),
        ("4:3", 360, (480, 360)),
        ("1:1", 720, (720, 720)),
        ("2:3", 540, (540, 810)),
    ],
)
def test_presets_name_the_short_edge(aspect, resolution, expected):
    assert preset_size(aspect, resolution) == expected


def test_fill_covers_and_fit_contains():
    assert background_placement((100, 100), (200, 100), "fill") == (0, -50, 200, 200)
    assert background_placement((100, 100), (200, 100), "fit") == (50, 0, 100, 100)


def test_stretch_ignores_aspect_and_centre_keeps_native_pixels():
    assert background_placement((100, 100), (300, 50), "stretch") == (0, 0, 300, 50)
    assert background_placement((100, 100), (300, 50), "center") == (100, -25, 100, 100)


def test_all_nine_anchors_land_where_they_say():
    expected = {
        "top-left": (0, 0), "top": (45, 0), "top-right": (90, 0),
        "left": (0, 45), "center": (45, 45), "right": (90, 45),
        "bottom-left": (0, 90), "bottom": (45, 90), "bottom-right": (90, 90),
    }
    assert set(expected) == set(ANCHORS)
    for anchor, position in expected.items():
        assert overlay_position((10, 10), (100, 100), anchor, (0, 0)) == position


def test_offset_nudges_from_the_anchor():
    assert overlay_position((10, 10), (100, 100), "bottom-right", (-5, 3)) == (85, 93)


def test_view_fits_both_up_and_down():
    assert fit_view((1920, 1080), (960, 960)) == (960, 540)
    assert fit_view((640, 360), (1280, 1280)) == (1280, 720)


def test_fill_colour_shows_where_the_background_does_not_reach():
    spec = RenderSpec(fit_mode="center", fill_colour="#0000ff", canvas=(10, 10))
    canvas = compose_canvas(Image.new("RGB", (2, 2), RED), None, spec)
    assert canvas.getpixel((0, 0)) == BLUE
    assert canvas.getpixel((5, 5)) == RED


def test_fill_colour_shows_through_a_transparent_background():
    spec = RenderSpec(fill_colour="#0000ff", canvas=(4, 4))
    canvas = compose_canvas(Image.new("RGBA", (4, 4), (255, 0, 0, 0)), None, spec)
    assert canvas.getpixel((1, 1)) == BLUE


def test_tile_repeats_on_both_axes_even_from_one_pixel():
    tile = Image.new("RGB", (2, 1), RED)
    tile.putpixel((1, 0), BLUE)
    canvas = compose_canvas(tile, None, RenderSpec(fit_mode="tile", canvas=(5, 3)))
    assert canvas.getpixel((0, 2)) == RED
    assert canvas.getpixel((3, 2)) == BLUE
    assert canvas.getpixel((4, 2)) == RED
    assert compose_canvas(Image.new("RGB", (1, 1), RED), None, RenderSpec(fit_mode="tile", canvas=(7, 5))).getpixel((6, 4)) == RED


def test_overlay_larger_than_canvas_crops_rather_than_scales_or_crashes():
    overlay = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    overlay.putpixel((50, 50), (*GREEN, 255))
    spec = RenderSpec(canvas=(10, 10), anchor="center")
    canvas = compose_canvas(Image.new("RGB", (10, 10), RED), overlay, spec)
    assert canvas.size == (10, 10)
    assert canvas.getpixel((5, 5)) == GREEN
    assert canvas.getpixel((4, 4)) == RED


def test_overlay_entirely_off_canvas_does_not_crash():
    overlay = Image.new("RGBA", (4, 4), (*GREEN, 255))
    spec = RenderSpec(canvas=(10, 10), anchor="top-left", offset=(-50, 500))
    assert compose_canvas(Image.new("RGB", (10, 10), RED), overlay, spec).getpixel((0, 0)) == RED


def test_match_canvas_follows_the_overlay_and_falls_back_to_the_background():
    background = Image.new("RGB", (30, 20), RED)
    overlay = Image.new("RGBA", (70, 50))
    assert compose_canvas(background, overlay, RenderSpec()).size == (70, 50)
    assert compose_canvas(background, None, RenderSpec()).size == (30, 20)


def test_nearest_stays_crisp_and_lanczos_blends():
    source = Image.new("RGB", (2, 1), (0, 0, 0))
    source.putpixel((1, 0), (255, 255, 255))
    nearest, _ = render_frame(source, None, RenderSpec(resample="nearest", view=(64, 32)))
    lanczos, _ = render_frame(source, None, RenderSpec(resample="lanczos", view=(64, 32)))
    assert set(nearest.tobytes()) == {0, 255}
    assert len(set(lanczos.tobytes())) > 2


def test_render_reports_the_canvas_it_came_from():
    frame, canvas = render_frame(Image.new("RGB", (100, 50), RED), None, RenderSpec(view=(50, 50)))
    assert canvas == (100, 50)
    assert frame.size == (50, 25)


def test_lru_evicts_oldest_by_weight_and_keeps_the_newest():
    cache = LRUCache(10, weigh=len)
    cache.put("a", "x" * 6)
    cache.put("b", "x" * 6)
    assert "a" not in cache and "b" in cache
    cache.put("huge", "x" * 50)
    assert "huge" in cache and len(cache) == 1


def test_prefetch_is_nearest_first_favours_travel_and_wraps():
    assert prefetch_order(5, 100, 1, ahead=3, behind=1) == [6, 4, 7, 8]
    assert prefetch_order(5, 100, -1, ahead=2, behind=1) == [4, 6, 3]
    assert prefetch_order(0, 3, 1) == [1, 2]
    assert prefetch_order(0, 1) == []


def test_settings_round_trip(tmp_path):
    path = tmp_path / "config.json"
    settings = Settings(bg_folder="C:/x", fit_mode="tile", offset_x=-5, resample="nearest")
    save_settings(settings, path)
    assert load_settings(path) == settings


@pytest.mark.parametrize("content", ["", "{not json", "[1, 2]", "null"])
def test_broken_config_falls_back_to_defaults(tmp_path, content):
    path = tmp_path / "config.json"
    path.write_text(content)
    assert load_settings(path) == Settings()


def test_nonsense_values_lose_only_themselves(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "fit_mode": "span",
        "fill_colour": "red",
        "custom_width": 0,
        "offset_x": True,
        "resolution": 1081,
        "anchor": "top",
    }))
    loaded = load_settings(path)
    assert loaded == Settings(anchor="top")


def test_reject_folder_defaults_inside_the_background_folder():
    assert Settings().reject_path() is None
    assert Settings(bg_folder="C:/bgs").reject_path() == Path("C:/bgs/rejects")
    assert Settings(bg_folder="C:/bgs", reject_folder="D:/keep").reject_path() == Path("D:/keep")


def test_canvas_size_per_mode():
    assert Settings().canvas_size() is None
    assert Settings(canvas_mode="preset", aspect="4:3", resolution=720).canvas_size() == (960, 720)
    assert Settings(canvas_mode="custom", custom_width=7, custom_height=9).canvas_size() == (7, 9)


def test_core_imports_no_qt():
    for path in (ROOT / "core").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not any(n.startswith(("PySide", "PyQt")) for n in names), path
