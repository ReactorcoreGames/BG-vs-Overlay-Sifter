"""`config.json`: every setting is global and this is the only file the program saves.

A missing, malformed or partly nonsense file falls back to defaults key by key, so a
hand-edit can cost one setting but never the launch.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .compose import RESAMPLING
from .placement import ANCHORS, ASPECTS, FIT_MODES, MAX_CANVAS, RESOLUTIONS, preset_size

CANVAS_MODES = ("match", "preset", "custom")
DEFAULT_REJECT_NAME = "rejects"
NO_OVERLAY = "<none>"  # `<` cannot appear in a Windows filename, so no file can collide

_CHOICES = {
    "fit_mode": FIT_MODES,
    "canvas_mode": CANVAS_MODES,
    "aspect": tuple(ASPECTS),
    "resolution": RESOLUTIONS,
    "anchor": ANCHORS,
    "resample": tuple(RESAMPLING),
}
_RANGES = {
    "custom_width": (1, MAX_CANVAS),
    "custom_height": (1, MAX_CANVAS),
    "offset_x": (-MAX_CANVAS, MAX_CANVAS),
    "offset_y": (-MAX_CANVAS, MAX_CANVAS),
}


@dataclass
class Settings:
    bg_folder: str = ""
    overlay_folder: str = ""
    reject_folder: str = ""  # empty means `<bg_folder>/rejects`
    fit_mode: str = "fill"
    fill_colour: str = "#000000"
    canvas_mode: str = "match"
    aspect: str = "16:9"
    resolution: int = 1080
    custom_width: int = 1920
    custom_height: int = 1080
    anchor: str = "center"
    offset_x: int = 0
    offset_y: int = 0
    resample: str = "lanczos"
    last_bg: str = ""
    last_overlay: str = ""
    window_geometry: str = ""

    def reject_path(self) -> Path | None:
        if self.reject_folder:
            return Path(self.reject_folder)
        return Path(self.bg_folder) / DEFAULT_REJECT_NAME if self.bg_folder else None

    def canvas_size(self) -> tuple[int, int] | None:
        """The chosen canvas in pixels. `None` means match the overlay."""
        if self.canvas_mode == "preset":
            return preset_size(self.aspect, self.resolution)
        if self.canvas_mode == "custom":
            return (self.custom_width, self.custom_height)
        return None


def _valid(name: str, value: object, default: object) -> bool:
    if type(value) is not type(default):
        return False
    if name in _CHOICES:
        return value in _CHOICES[name]
    if name in _RANGES:
        low, high = _RANGES[name]
        return low <= value <= high
    if name == "fill_colour":
        return re.fullmatch(r"#[0-9a-fA-F]{6}", value) is not None
    return True


def load_settings(path: Path) -> Settings:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()

    settings = Settings()
    for field in fields(Settings):
        value = data.get(field.name)
        if value is not None and _valid(field.name, value, field.default):
            setattr(settings, field.name, value)
    return settings


def save_settings(settings: Settings, path: Path) -> None:
    """Write-then-replace, so a crash mid-save cannot leave half a config behind."""
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    os.replace(temporary, path)
