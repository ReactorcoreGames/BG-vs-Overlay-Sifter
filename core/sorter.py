"""The background list, moving files out of it, and undoing that. The actual deliverable.

Two rules here are the difference between a sorter and a way to lose files:

**The scan is flat.** The rejects folder usually lives inside the background folder, so a
recursive walk would cycle the rejects straight back into the rotation.

**Nothing is ever overwritten.** Collisions count up Explorer-style (`foo (2).jpg`), in
both directions: moving out and undoing back.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .settings import NO_OVERLAY

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif")


def natural_key(path: Path) -> list:
    """Sort `bg (2).jpg` before `bg (10).jpg`, as Explorer does."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", path.name.lower())]


def scan_images(folder: Path | str) -> list[Path]:
    """The folder's images, naturally sorted. Flat, never recursive."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
        key=natural_key,
    )


def unique_destination(folder: Path, filename: str) -> Path:
    """`foo.jpg`, then `foo (2).jpg`, `foo (3).jpg`... **Never overwrite.**"""
    candidate = folder / filename
    stem, suffix = Path(filename).stem, Path(filename).suffix
    counter = 2
    while candidate.exists():
        candidate = folder / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


class OverlayCursor:
    """The overlay cycle. A "no overlay" step leads it, and is all there is with no folder."""

    def __init__(self) -> None:
        self.paths: list[Path | None] = [None]
        self.index = 0

    @property
    def current(self) -> Path | None:
        return self.paths[self.index]

    def _scan(self, folder: str) -> None:
        self.paths = [None, *(scan_images(folder) if folder else [])]

    def load(self, folder: str, start_name: str = "") -> None:
        """Start on `start_name` if it is there, otherwise on the first real overlay."""
        self._scan(folder)
        names = [p.name if p else NO_OVERLAY for p in self.paths]
        self.index = names.index(start_name) if start_name in names else min(1, len(self.paths) - 1)

    def rescan(self, folder: str) -> None:
        """Pick up outside changes, staying on the current overlay if it is still there."""
        current = self.current
        self._scan(folder)
        if current in self.paths:
            self.index = self.paths.index(current)
        else:
            self.index = min(self.index, len(self.paths) - 1)

    def step(self, delta: int) -> None:
        self.index = (self.index + delta) % len(self.paths)


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path
    index: int


class Sorter:
    """A cursor over one folder's images, with undo for the current run only."""

    def __init__(self) -> None:
        self.folder: Path | None = None
        self.paths: list[Path] = []
        self.index = 0
        self.undo_stack: list[Move] = []

    @property
    def current(self) -> Path | None:
        return self.paths[self.index] if self.paths else None

    def set_folder(self, folder: Path | str | None, start_name: str = "") -> None:
        """Switch folders. The undo stack survives: its paths are absolute and stay valid."""
        self.folder = Path(folder) if folder else None
        self.paths = scan_images(self.folder) if self.folder else []
        self.index = next((i for i, p in enumerate(self.paths) if p.name == start_name), 0)

    def rescan(self) -> None:
        """Pick up outside changes, staying on the current image if it is still there."""
        if self.folder is None:
            return
        current = self.current
        self.paths = scan_images(self.folder)
        if current in self.paths:
            self.index = self.paths.index(current)
        else:
            self.index = min(self.index, max(0, len(self.paths) - 1))

    def step(self, delta: int) -> None:
        if self.paths:
            self.index = (self.index + delta) % len(self.paths)

    def move_out(self, path: Path, target_folder: Path) -> Move:
        """Move one image to the target. The cursor stays put, landing on the next image."""
        index = self.paths.index(path)
        target_folder.mkdir(parents=True, exist_ok=True)
        destination = unique_destination(target_folder, path.name)
        shutil.move(str(path), str(destination))

        move = Move(path, destination, index)
        self.undo_stack.append(move)
        del self.paths[index]
        if index < self.index:
            self.index -= 1
        if self.index >= len(self.paths):
            self.index = 0
        return move

    def undo(self) -> Move | None:
        """Put the latest move back at its old list position, and go to it.

        Raises `OSError` if it cannot. A file that has vanished is dropped from the stack
        so it cannot block older undos; a failed move stays, because it may be retried.
        """
        if not self.undo_stack:
            return None
        move = self.undo_stack[-1]
        if not move.destination.exists():
            self.undo_stack.pop()
            raise FileNotFoundError(f"{move.destination.name} is no longer in the target folder")

        move.source.parent.mkdir(parents=True, exist_ok=True)
        restored = unique_destination(move.source.parent, move.source.name)
        shutil.move(str(move.destination), str(restored))
        self.undo_stack.pop()

        if restored.parent == self.folder:
            self.index = min(move.index, len(self.paths))
            self.paths.insert(self.index, restored)
        return move
