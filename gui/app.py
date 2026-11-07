"""The window: keys in, frames out.

`SetProcessDpiAwareness` is carried over from the prototype; without it everything is
blurry on Windows. Quit is Alt+F4 and nothing else: Esc shows and hides the panel.
"""
from __future__ import annotations

import base64
import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMainWindow

from core.cache import prefetch_order
from core.compose import RenderSpec
from core.placement import FIT_LABELS, FIT_MODES
from core.settings import NO_OVERLAY, Settings, load_settings, save_settings
from core.sorter import OverlayCursor, Sorter

from . import theme
from .frames import Frame, FrameKey, FrameRenderer
from .keys import handle_key
from .panel import SidePanel
from .view import CanvasView, Toast

TITLE = "BG vs Overlay Sifter"
SAVE_DELAY_MILLISECONDS = 500
RESIZE_DELAY_MILLISECONDS = 80


def resource_root() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "config.json"
    return resource_root() / "config.json"


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def set_taskbar_identity() -> None:
    """Without this, running from source groups under python.exe and shows its icon."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Reactorcore.BGvsOverlaySifter")
    except Exception:
        pass


class MainWindow(QMainWindow):
    def __init__(self, config: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle(TITLE)
        self.setMinimumSize(640, 400)
        self.config = config or config_path()
        self.settings: Settings = load_settings(self.config)

        self.sorter = Sorter()
        self.overlays = OverlayCursor()
        self._activated_before = False

        self._wanted: FrameKey | None = None
        self._trail: list[FrameKey] = []
        self.shown_background: Path | None = None
        self._canvas_size: tuple[int, int] | None = None

        self.view = CanvasView(self)
        self.setCentralWidget(self.view)
        self.panel = SidePanel(self.settings, self.view)
        self.toast = Toast(self.view)

        self.frames = FrameRenderer(resource_root() / "assets" / "missing image error.jpg")
        self.frames.ready.connect(self._on_frame_ready)

        self._save_timer = QTimer(self, singleShot=True, interval=SAVE_DELAY_MILLISECONDS)
        self._save_timer.timeout.connect(self._save_now)
        self._resize_timer = QTimer(self, singleShot=True, interval=RESIZE_DELAY_MILLISECONDS)
        self._resize_timer.timeout.connect(self.refresh)

        self.view.resized.connect(self._on_view_resized)
        self.view.clicked.connect(self._on_canvas_clicked)
        self.panel.settings_changed.connect(self._on_settings_changed)
        self.panel.folders_changed.connect(self._on_folders_changed)
        self.panel.message.connect(self.toast.say)
        self.panel.close_requested.connect(self.toggle_panel)

        self._load_folders(self.settings.last_bg, self.settings.last_overlay)
        self._restore_geometry()
        QApplication.instance().installEventFilter(self)

        if self.sorter.current is None:
            self.panel.set_open(True)  # nothing to look at yet: go straight to setup
        self.refresh()

    # -- keys -------------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.KeyPress and handle_key(self, event):
            return True
        return super().eventFilter(obj, event)

    # -- actions ----------------------------------------------------------------------

    def flip_background(self, delta: int) -> None:
        self.sorter.step(delta)
        self.refresh(delta)
        self._schedule_save()

    def flip_overlay(self, delta: int) -> None:
        self.overlays.step(delta)
        self.refresh()
        self._schedule_save()

    def reject(self) -> None:
        """Moves the image on screen, which during a fast flip can trail the cursor.

        What you see is what moves. If what you see has just been moved and its successor
        is not up yet, this does nothing rather than move an image nobody has looked at.
        """
        target = self.shown_background
        if target is None or target not in self.sorter.paths:
            return
        folder = self.settings.reject_path()
        if folder is None:
            return
        if folder.resolve() == target.parent.resolve():
            self.toast.say("The target folder is the background folder. Choose another.")
            self.panel.set_open(True)
            self._update_cursor()
            return
        try:
            move = self.sorter.move_out(target, folder)
        except OSError as error:
            self.toast.say(f"Could not move {target.name}: {error}")
            return
        self.toast.say(f"Moved {move.source.name} to {folder.name}.  Ctrl+Z to undo")
        self.refresh()
        self._schedule_save()

    def undo(self) -> None:
        try:
            move = self.sorter.undo()
        except OSError as error:
            self.toast.say(f"Could not undo: {error}")
            return
        if move is None:
            self.toast.say("Nothing to undo")
            return
        self.toast.say(f"Restored {move.source.name}")
        self.refresh()
        self._schedule_save()

    def cycle_fit(self, delta: int) -> None:
        position = FIT_MODES.index(self.settings.fit_mode)
        self.settings.fit_mode = FIT_MODES[(position + delta) % len(FIT_MODES)]
        self.panel.sync()
        self.toast.say(FIT_LABELS[self.settings.fit_mode])
        self.refresh()
        self._schedule_save()

    def toggle_panel(self) -> None:
        self.panel.toggle()
        self._update_cursor()
        if self.sorter.current is None:
            self.refresh()  # the empty state's hint depends on whether the panel is open

    def _on_canvas_clicked(self) -> None:
        """Only ever opens: clicking away from a field is normal while adjusting settings."""
        focus = QApplication.focusWidget()
        if focus is not None:
            focus.clearFocus()
        if not self.panel.is_open:
            self.toggle_panel()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~Qt.WindowFullScreen)
        else:
            self._remember_geometry()
            self.setWindowState(self.windowState() | Qt.WindowFullScreen)
        self.view.set_label_visible(not self.isFullScreen())
        self._update_cursor()

    def _update_cursor(self) -> None:
        """No arrow over the image in fullscreen, where it would land in a screenshot."""
        hide = self.isFullScreen() and not self.panel.is_open
        self.view.setCursor(Qt.BlankCursor if hide else Qt.ArrowCursor)

    # -- frames -----------------------------------------------------------------------

    def _spec(self) -> RenderSpec:
        s = self.settings
        return RenderSpec(
            fit_mode=s.fit_mode,
            fill_colour=s.fill_colour,
            canvas=s.canvas_size(),
            anchor=s.anchor,
            offset=(s.offset_x, s.offset_y),
            resample=s.resample,
            view=self.view.pixel_size(),
        )

    def refresh(self, direction: int = 1) -> None:
        """Ask for the frame under the cursor plus its neighbours. Never renders here."""
        background = self.sorter.current
        if background is None:
            self._wanted = None
            self._trail.clear()
            self.shown_background = None
            self.view.show_message(self._empty_message())
            self._update_title("")
            self.panel.show_canvas_size(None)
            return

        spec = self._spec()
        overlay = self.overlays.current
        key = FrameKey(background, overlay, spec)
        self._wanted = key

        frame = self.frames.peek(key)
        if frame is not None:
            self._show(frame)
            self._trail.clear()
        else:
            self._trail.append(key)

        paths = self.sorter.paths
        wanted = [key]
        wanted += [
            FrameKey(paths[i], overlay, spec)
            for i in prefetch_order(self.sorter.index, len(paths), direction)
        ]
        wanted += [
            FrameKey(background, self.overlays.paths[i], spec)
            for i in prefetch_order(self.overlays.index, len(self.overlays.paths), 1, ahead=1, behind=1)
        ]
        self.frames.request(wanted)

    def _on_frame_ready(self, frame: Frame) -> None:
        """Show the frame if it is wanted, or one the cursor already passed through.

        While a key is held the cursor can outrun the workers, so the exact frame wanted
        may never arrive before the cursor moves on. Showing the ones it passed through
        keeps the picture moving forward. Prefetched neighbours never show this way.
        """
        if frame.key == self._wanted:
            self._show(frame)
            self._trail.clear()
        elif frame.key in self._trail:
            self._show(frame)
            del self._trail[: self._trail.index(frame.key) + 1]

    def _show(self, frame: Frame) -> None:
        key = frame.key
        self.shown_background = key.background
        self._canvas_size = frame.canvas_size

        parts = [key.background.name + (" (unreadable)" if frame.background_failed else "")]
        overlay = key.overlay.name if key.overlay else "No overlay"
        parts.append(overlay + (" (unreadable)" if frame.overlay_failed else ""))
        if key.background in self.sorter.paths:
            position = self.sorter.paths.index(key.background) + 1
            parts.append(f"{position}/{len(self.sorter.paths)}")
        label = "  |  ".join(parts)

        frame.image.setDevicePixelRatio(self.view.devicePixelRatioF())
        self.view.show_frame(frame.image, label)
        self._update_title(label)
        self.panel.show_canvas_size(frame.canvas_size)

    def _update_title(self, label: str) -> None:
        hint = "Esc for settings"
        self.setWindowTitle(f"{label}  -  {hint}" if label else f"{TITLE}  -  {hint}")

    def _empty_message(self) -> str:
        """Says what to do without relying on the title bar, which fullscreen does not have."""
        if not self.settings.bg_folder:
            message = "Choose a background folder to begin"
        elif not Path(self.settings.bg_folder).is_dir():
            message = f"Folder not found:\n{self.settings.bg_folder}"
        elif self.sorter.undo_stack:
            message = "No images left in the background folder.\nCtrl+Z brings the latest one back."
        else:
            message = f"No images in:\n{self.settings.bg_folder}"
        return message if self.panel.is_open else f"{message}\nPress Esc or click to open settings"

    # -- folders ----------------------------------------------------------------------

    def _load_folders(self, start_bg: str = "", start_overlay: str = "") -> None:
        self.sorter.set_folder(self.settings.bg_folder or None, start_bg)
        self.overlays.load(self.settings.overlay_folder, start_overlay)

    def _reload_from_disk(self) -> None:
        """Coming back to the window: pick up added files, and edits to existing ones."""
        self.sorter.rescan()
        self.overlays.rescan(self.settings.overlay_folder)
        self.frames.clear()
        self.refresh()

    def _on_folders_changed(self) -> None:
        self._load_folders()
        self.refresh()
        self._schedule_save()

    def _on_settings_changed(self) -> None:
        self.refresh()
        self._schedule_save()

    # -- window -----------------------------------------------------------------------

    def _on_view_resized(self) -> None:
        self.panel.place()
        self.toast.place()
        self._resize_timer.start()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and self.isActiveWindow():
            # The launch's own activation is not a return: the folders were only just read,
            # and clearing would throw away the frames already rendering.
            if self._activated_before:
                self._reload_from_disk()
            self._activated_before = True

    def _restore_geometry(self) -> None:
        try:
            saved = base64.b64decode(self.settings.window_geometry)
        except ValueError:  # a hand-edit can cost this setting, but never the launch
            saved = b""
        if not saved or not self.restoreGeometry(QByteArray(saved)):
            self.resize(1280, 720)
            self.setWindowState(Qt.WindowMaximized)

    def _remember_geometry(self) -> None:
        if not self.isFullScreen():
            self.settings.window_geometry = base64.b64encode(
                bytes(self.saveGeometry())
            ).decode("ascii")

    def _schedule_save(self) -> None:
        """Debounced, because flipping must not write to disk on every keypress."""
        self._save_timer.start()

    def _save_now(self) -> None:
        current = self.sorter.current
        self.settings.last_bg = current.name if current else ""
        overlay = self.overlays.current
        self.settings.last_overlay = overlay.name if overlay else NO_OVERLAY
        try:
            save_settings(self.settings, self.config)
        except OSError as error:
            self.toast.say(f"Could not save settings: {error}")

    def closeEvent(self, event) -> None:
        self._remember_geometry()
        self._save_timer.stop()
        self._save_now()
        QApplication.instance().removeEventFilter(self)
        self.frames.shutdown()
        super().closeEvent(event)


def main() -> int:
    enable_dpi_awareness()
    set_taskbar_identity()
    app = QApplication(sys.argv)
    app.setApplicationName(TITLE)
    app.setStyleSheet(theme.STYLE)
    app.setWindowIcon(QIcon(str(resource_root() / "assets" / "icon.ico")))
    window = MainWindow()
    window.show()
    return app.exec()
