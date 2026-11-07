"""Worker threads that turn (background, overlay, settings) into ready-to-paint frames.

**Nothing decodes on the UI thread during a flip.** The flip is the product and a stutter
kills it. The UI thread only ever `peek`s finished frames; everything slower happens here.

Pending work is replaced wholesale on every `request`, so holding a key never builds up a
backlog of frames nobody is waiting for any more.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

from core.cache import LRUCache
from core.compose import RenderSpec, load_background, load_overlay, render_frame

FRAME_BUDGET_BYTES = 512 * 1024 * 1024
DECODED_IMAGES = 8
WORKERS = 3


@dataclass(frozen=True)
class FrameKey:
    background: Path
    overlay: Path | None
    spec: RenderSpec


@dataclass(frozen=True)
class Frame:
    key: FrameKey
    image: QImage
    canvas_size: tuple[int, int]
    background_failed: bool = False
    overlay_failed: bool = False


def to_qimage(image: Image.Image) -> QImage:
    """Opaque 32-bit, the format the raster painter blits without converting."""
    data = image.convert("RGBA").tobytes("raw", "BGRA")
    return QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGB32).copy()


class FrameRenderer(QObject):
    ready = Signal(object)

    def __init__(self, placeholder: Path, workers: int = WORKERS) -> None:
        super().__init__()
        self._placeholder = placeholder
        self._frames = LRUCache(FRAME_BUDGET_BYTES, weigh=lambda f: f.image.sizeInBytes())
        self._decoded = LRUCache(DECODED_IMAGES)
        self._pending: list[FrameKey] = []
        self._in_flight: set[FrameKey] = set()
        self._generation = 0
        self._stopping = False
        self._wake = threading.Condition()
        self._threads = [
            threading.Thread(target=self._work, daemon=True) for _ in range(workers)
        ]
        for thread in self._threads:
            thread.start()

    def peek(self, key: FrameKey) -> Frame | None:
        """The frame only if it is already finished. **Never renders.**"""
        return self._frames.get(key)

    def request(self, keys: list[FrameKey]) -> None:
        """Replace the pending work with these keys, most wanted first."""
        with self._wake:
            self._pending = [
                k for k in keys if k not in self._frames and k not in self._in_flight
            ]
            self._wake.notify_all()

    def clear(self) -> None:
        """Forget everything rendered, so files edited on disk get re-read."""
        with self._wake:
            self._generation += 1
            self._pending = []
            self._in_flight.clear()
        self._frames.clear()
        self._decoded.clear()

    def shutdown(self) -> None:
        with self._wake:
            self._stopping = True
            self._wake.notify_all()
        for thread in self._threads:
            thread.join(timeout=2)

    def _work(self) -> None:
        while True:
            with self._wake:
                while not self._pending and not self._stopping:
                    self._wake.wait()
                if self._stopping:
                    return
                key = self._pending.pop(0)
                self._in_flight.add(key)
                generation = self._generation

            frame = self._render(key)

            with self._wake:
                if generation != self._generation or self._stopping:
                    continue  # cleared while rendering: this frame may be stale
                self._frames.put(key, frame)
                self._in_flight.discard(key)
            try:
                self.ready.emit(frame)
            except RuntimeError:
                return  # the window is already gone

    def _decode(self, path: Path, loader) -> Image.Image:
        image = self._decoded.get(path)
        if image is None:
            image = loader(path)
            self._decoded.put(path, image)
        return image

    def _render(self, key: FrameKey) -> Frame:
        """Bad files degrade rather than crash: a placeholder BG, or simply no overlay."""
        background_failed = overlay_failed = False
        try:
            background = self._decode(key.background, load_background)
        except Exception:
            background_failed = True
            background = self._decode(self._placeholder, load_background)

        overlay = None
        if key.overlay is not None:
            try:
                overlay = self._decode(key.overlay, load_overlay)
            except Exception:
                overlay_failed = True

        image, canvas_size = render_frame(background, overlay, key.spec)
        return Frame(key, to_qimage(image), canvas_size, background_failed, overlay_failed)
