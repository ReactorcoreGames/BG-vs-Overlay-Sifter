"""The sidepanel: three folders and the global settings, sliding in over the image.

It slides *over* the image rather than pushing it, so opening it never re-renders or
shifts what is being judged. It reads and writes `Settings` directly and only signals
that something changed; the window decides what that means.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.placement import ANCHORS, ASPECTS, FIT_LABELS, FIT_MODES, MAX_CANVAS, RESOLUTIONS
from core.settings import DEFAULT_REJECT_NAME, Settings

from . import theme

PANEL_WIDTH = 340
SLIDE_MILLISECONDS = 140
SECTION_GAP = 3

ANCHOR_LABELS = {
    "top-left": "Top left", "top": "Top", "top-right": "Top right",
    "left": "Left", "center": "Centre", "right": "Right",
    "bottom-left": "Bottom left", "bottom": "Bottom", "bottom-right": "Bottom right",
}
CANVAS_LABELS = {"match": "Match overlay", "preset": "Preset", "custom": "Custom"}
RESAMPLE_LABELS = {"lanczos": "Lanczos (smooth)", "nearest": "Nearest (crisp)"}
KEYS = (
    ("A / D  or  Left / Right", "Previous / next BG"),
    ("W / S  or  Up / Down", "Previous / next overlay"),
    ("R", "Move BG to target folder"),
    ("Ctrl+Z", "Undo the latest move"),
    ("Tab", "Cycle BG mode"),
    ("F11", "Fullscreen"),
    ("Esc", "Show / hide this panel"),
    ("Click the image", "Show this panel"),
)
# Plain-text tooltips do not wrap, so the lines are broken by hand. A test holds them to a width.
TIPS = {
    "bg_folder": (
        "The folder of background images to flip through.\n"
        "Type or paste a path and press Enter, or use Browse.\n"
        "Images in its subfolders are not included."
    ),
    "overlay_folder": (
        "Optional. The finished overlay images to show on top.\n"
        "W / S steps through them, with a no-overlay step included.\n"
        "Type or paste a path and press Enter, or use Browse."
    ),
    "reject_folder": (
        "Where R moves the background on screen.\n"
        "Left empty, it is a rejects folder inside the backgrounds folder.\n"
        "Created when first needed. Nothing is ever overwritten."
    ),
    "browse": "Choose this folder from a window.",
    "open": "Open this folder in Explorer.",
    "open_reject": "Open this folder in Explorer, creating it if needed.",
    "fit_mode": (
        "How the background covers the canvas. Tab cycles through these.\n"
        "Fill: covers it all, cropping what overflows.\n"
        "Fit: shows the whole image, with the fill colour in any gaps.\n"
        "Stretch: covers it all, distorting the image's shape.\n"
        "Tile: repeats at full size from the top left.\n"
        "Centre: full size in the middle, cropped or with gaps."
    ),
    "fill_colour": (
        "Shows in any gaps the background leaves, as Fit and Centre can,\n"
        "and through any transparent parts of it. Click to choose."
    ),
    "canvas_mode": (
        "The size of the picture, before it is fitted to the window.\n"
        "Match overlay: the size of the overlay showing,\n"
        "or of the background when no overlay is showing.\n"
        "Preset: choose a shape and a size.\n"
        "Custom: type a width and height."
    ),
    "canvas_readout": "The size of the canvas right now, in pixels.",
    "aspect": "The canvas's shape, as width to height.",
    "resolution": "The canvas's short edge in pixels, so 9:16 at 1080p is 1080 x 1920.",
    "custom_width": "The canvas's width in pixels. Type a number and press Enter, or use the arrows.",
    "custom_height": "The canvas's height in pixels. Type a number and press Enter, or use the arrows.",
    "placement": (
        "Where the overlay sits on the canvas.\n"
        "Overlays are never resized, and crop at the canvas's edge."
    ),
    "offset_x": (
        "Nudges the overlay sideways from its placement, in pixels.\n"
        "Positive moves it right, negative moves it left."
    ),
    "offset_y": (
        "Nudges the overlay up or down from its placement, in pixels.\n"
        "Positive moves it down, negative moves it up."
    ),
    "resample": (
        "How images are resized.\n"
        "Lanczos: smooth, for paintings and photos.\n"
        "Nearest: keeps hard pixel edges, for pixel art."
    ),
    "close": "Hide this panel. Esc does the same, and clicking the image brings it back.",
}


class _IgnoreWheel(QObject):
    """Scrolling the panel must not change whichever combo passes under the cursor."""

    def eventFilter(self, obj, event) -> bool:
        return event.type() == QEvent.Wheel and not obj.hasFocus()


def swatch_ink(fill: str) -> str:
    """Black or white, whichever measures better, so the hex stays readable on any fill."""
    r, g, b = (
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        for c in QColor(fill).getRgbF()[:3]
    )
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "#000000" if (luminance + 0.05) / 0.05 >= 1.05 / (luminance + 0.05) else "#ffffff"


def _label(text: str, name: str = "", tip: str = "") -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setToolTip(tip)
    return label


class SidePanel(QFrame):
    settings_changed = Signal()
    folders_changed = Signal()
    message = Signal(str)
    close_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("panel")
        self.setFixedWidth(PANEL_WIDTH)
        self.is_open = False
        self._wheel_guard = _IgnoreWheel(self)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(SLIDE_MILLISECONDS)
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        self._slide.finished.connect(self._slide_finished)

        body = QWidget()
        body.setObjectName("panelBody")
        self._column = QVBoxLayout(body)
        self._column.setContentsMargins(16, 8, 16, 8)
        self._column.setSpacing(4)
        self._build()

        scroll = QScrollArea(self)
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self.sync()
        self.hide()

    # -- building ---------------------------------------------------------------------

    def _build(self) -> None:
        add = self._column.addWidget

        header = QHBoxLayout()
        header.addWidget(_label("BG vs Overlay Sifter", "title"), 1)
        close = self._button("Close", TIPS["close"])
        close.clicked.connect(self.close_requested)
        header.addWidget(close)
        self._column.addLayout(header)

        self._section("Folders")
        self._bg_edit = self._folder_row("Backgrounds", "bg_folder")
        self._overlay_edit = self._folder_row("Overlays", "overlay_folder")
        self._reject_edit = self._folder_row("Move rejects or favourites to", "reject_folder")

        self._section("Background")
        fill = QHBoxLayout()
        self._fit = self._combo({m: FIT_LABELS[m] for m in FIT_MODES}, "fit_mode")
        fill.addWidget(self._fit, 1)
        fill.addWidget(_label("Fill colour", tip=TIPS["fill_colour"]))
        self._colour = self._button("", TIPS["fill_colour"])
        self._colour.clicked.connect(self._pick_colour)
        fill.addWidget(self._colour)
        self._column.addLayout(fill)

        self._section("Canvas")
        canvas = QHBoxLayout()
        self._canvas_mode = self._combo(CANVAS_LABELS, "canvas_mode")
        canvas.addWidget(self._canvas_mode, 1)
        self._canvas_readout = _label("", "dim", TIPS["canvas_readout"])
        canvas.addWidget(self._canvas_readout)
        self._column.addLayout(canvas)

        self._preset_row = QWidget()
        preset = QHBoxLayout(self._preset_row)
        preset.setContentsMargins(0, 0, 0, 0)
        self._aspect = self._combo({a: a for a in ASPECTS}, "aspect")
        self._resolution = self._combo({r: f"{r}p" for r in RESOLUTIONS}, "resolution")
        preset.addWidget(self._aspect)
        preset.addWidget(self._resolution)
        add(self._preset_row)

        self._custom_row = QWidget()
        custom = QHBoxLayout(self._custom_row)
        custom.setContentsMargins(0, 0, 0, 0)
        self._custom_w = self._spin("custom_width", 1, MAX_CANVAS)
        self._custom_h = self._spin("custom_height", 1, MAX_CANVAS)
        custom.addWidget(_label("W", tip=TIPS["custom_width"]))
        custom.addWidget(self._custom_w, 1)
        custom.addWidget(_label("H", tip=TIPS["custom_height"]))
        custom.addWidget(self._custom_h, 1)
        add(self._custom_row)

        self._section("Overlay placement", TIPS["placement"])
        grid = QGridLayout()
        grid.setSpacing(3)
        self._anchor_buttons = {}
        for position, anchor in enumerate(ANCHORS):
            name = ANCHOR_LABELS[anchor]
            button = self._button(name, f"Line the overlay up with the {name.lower()} of the canvas.")
            button.setCheckable(True)
            button.clicked.connect(lambda _=False, a=anchor: self._set("anchor", a))
            grid.addWidget(button, position // 3, position % 3)
            self._anchor_buttons[anchor] = button
        self._column.addLayout(grid)

        offsets = QHBoxLayout()
        self._offset_x = self._spin("offset_x", -MAX_CANVAS, MAX_CANVAS)
        self._offset_y = self._spin("offset_y", -MAX_CANVAS, MAX_CANVAS)
        offsets.addWidget(_label("X", tip=TIPS["offset_x"]))
        offsets.addWidget(self._offset_x, 1)
        offsets.addWidget(_label("Y", tip=TIPS["offset_y"]))
        offsets.addWidget(self._offset_y, 1)
        self._column.addLayout(offsets)

        self._column.addSpacing(SECTION_GAP)
        resampling = QHBoxLayout()
        resampling.addWidget(_label("Resampling", "section", TIPS["resample"]))
        self._resample = self._combo(RESAMPLE_LABELS, "resample")
        resampling.addWidget(self._resample, 1)
        self._column.addLayout(resampling)

        self._section("Keys")
        keys = QGridLayout()
        keys.setVerticalSpacing(2)
        for row, (key, meaning) in enumerate(KEYS):
            keys.addWidget(_label(key), row, 0)
            keys.addWidget(_label(meaning, "dim"), row, 1)
        self._column.addLayout(keys)

        self._column.addStretch(1)
        footer = _label(
            'Made by Reactorcore: <a href="https://linktr.ee/reactorcore" '
            f'style="color: {theme.FLESH};">linktr.ee/reactorcore</a>',
        )
        footer.setOpenExternalLinks(True)
        footer.setFocusPolicy(Qt.NoFocus)
        add(footer)

    def _section(self, title: str, tip: str = "") -> None:
        self._column.addSpacing(SECTION_GAP)
        self._column.addWidget(_label(title, "section", tip))

    def _button(self, text: str, tip: str) -> QPushButton:
        # NoFocus: a button holding focus would turn Space and arrows into its own keys.
        button = QPushButton(text)
        button.setFocusPolicy(Qt.NoFocus)
        button.setToolTip(tip)
        return button

    def _combo(self, options: dict, attribute: str) -> QComboBox:
        combo = QComboBox()
        combo.setToolTip(TIPS[attribute])
        for value, text in options.items():
            combo.addItem(text, value)
        combo.setFocusPolicy(Qt.ClickFocus)
        combo.installEventFilter(self._wheel_guard)
        combo.activated.connect(lambda _: self._set(attribute, combo.currentData()))
        combo.activated.connect(lambda _: combo.clearFocus())
        return combo

    def _spin(self, attribute: str, low: int, high: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setToolTip(TIPS[attribute])
        spin.setRange(low, high)
        spin.setKeyboardTracking(False)  # render on commit, not on every digit typed
        spin.setFocusPolicy(Qt.ClickFocus)
        spin.installEventFilter(self._wheel_guard)
        spin.valueChanged.connect(lambda value: self._set(attribute, value))
        spin.lineEdit().returnPressed.connect(spin.clearFocus)
        return spin

    def _folder_row(self, title: str, attribute: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setToolTip(TIPS[attribute])
        edit.setFocusPolicy(Qt.ClickFocus)
        edit.editingFinished.connect(lambda: self._commit_folder(attribute, edit))
        edit.returnPressed.connect(edit.clearFocus)

        row = QHBoxLayout()
        row.addWidget(_label(title, "dim", TIPS[attribute]), 1)
        browse = self._button("Browse...", TIPS["browse"])
        browse.clicked.connect(lambda: self._browse(attribute, edit))
        row.addWidget(browse)
        opener = self._button("Open", TIPS["open_reject" if attribute == "reject_folder" else "open"])
        opener.clicked.connect(lambda: self._open_folder(attribute))
        row.addWidget(opener)
        self._column.addLayout(row)
        self._column.addWidget(edit)
        return edit

    # -- reacting ---------------------------------------------------------------------

    def _set(self, attribute: str, value: object) -> None:
        if getattr(self.settings, attribute) == value:
            return
        setattr(self.settings, attribute, value)
        self.sync()
        self.settings_changed.emit()

    def _commit_folder(self, attribute: str, edit: QLineEdit) -> None:
        text = edit.text().strip()
        path = os.path.normpath(text) if text else ""
        # The target folder may not exist yet: the first move creates it.
        bad = bool(path) and attribute != "reject_folder" and not os.path.isdir(path)
        edit.setProperty("bad", bad)
        edit.style().polish(edit)
        if bad:
            self.message.emit(f"Folder not found: {path}")
            return
        if getattr(self.settings, attribute) != path:
            setattr(self.settings, attribute, path)
            self.sync()
            self.folders_changed.emit()

    def _browse(self, attribute: str, edit: QLineEdit) -> None:
        start = edit.text() or self.settings.bg_folder
        chosen = QFileDialog.getExistingDirectory(self, "Choose folder", start)
        if chosen:
            edit.setText(os.path.normpath(chosen))
            self._commit_folder(attribute, edit)

    def _open_folder(self, attribute: str) -> None:
        if attribute == "reject_folder":
            path = self.settings.reject_path()
            if path is None:
                self.message.emit("Choose a background folder first")
                return
            path.mkdir(parents=True, exist_ok=True)
        else:
            path = Path(getattr(self.settings, attribute))
            if not getattr(self.settings, attribute) or not path.is_dir():
                self.message.emit("Choose this folder first")
                return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _pick_colour(self) -> None:
        # Qt's own dialog, because the native one cannot wear the theme.
        colour = QColorDialog.getColor(
            QColor(self.settings.fill_colour), self, "Fill colour", QColorDialog.DontUseNativeDialog
        )
        if colour.isValid():
            self._set("fill_colour", colour.name())

    # -- state ------------------------------------------------------------------------

    def sync(self) -> None:
        """Show what `Settings` holds. Blocks signals, so it can never echo back as a change."""
        s = self.settings
        for edit, text in (
            (self._bg_edit, s.bg_folder),
            (self._overlay_edit, s.overlay_folder),
            (self._reject_edit, s.reject_folder),
        ):
            if not edit.hasFocus():
                edit.setText(text)
        default = str(Path(s.bg_folder) / DEFAULT_REJECT_NAME) if s.bg_folder else DEFAULT_REJECT_NAME
        self._reject_edit.setPlaceholderText(default)

        for combo, value in (
            (self._fit, s.fit_mode),
            (self._canvas_mode, s.canvas_mode),
            (self._aspect, s.aspect),
            (self._resolution, s.resolution),
            (self._resample, s.resample),
        ):
            combo.blockSignals(True)
            combo.setCurrentIndex(combo.findData(value))
            combo.blockSignals(False)

        for spin, value in (
            (self._custom_w, s.custom_width),
            (self._custom_h, s.custom_height),
            (self._offset_x, s.offset_x),
            (self._offset_y, s.offset_y),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

        for anchor, button in self._anchor_buttons.items():
            button.setChecked(anchor == s.anchor)

        self._colour.setText(s.fill_colour)
        self._colour.setStyleSheet(f"background: {s.fill_colour}; color: {swatch_ink(s.fill_colour)};")
        self._preset_row.setVisible(s.canvas_mode == "preset")
        self._custom_row.setVisible(s.canvas_mode == "custom")

    def show_canvas_size(self, size: tuple[int, int] | None) -> None:
        self._canvas_readout.setText(f"Canvas is {size[0]} x {size[1]}" if size else "")
        self._canvas_readout.setVisible(size is not None)  # empty, it would still take a layout slot

    def mousePressEvent(self, event) -> None:
        event.accept()  # a click on the panel must not fall through to the canvas behind it

    # -- sliding ----------------------------------------------------------------------

    def _edge_positions(self) -> tuple[QPoint, QPoint]:
        width = self.parentWidget().width()
        return QPoint(width - PANEL_WIDTH, 0), QPoint(width, 0)

    def toggle(self) -> None:
        self.set_open(not self.is_open)

    def set_open(self, is_open: bool) -> None:
        if is_open == self.is_open:
            return
        self.is_open = is_open
        opened, closed = self._edge_positions()
        self.setFixedHeight(self.parentWidget().height())
        if is_open:
            self.move(closed)
            self.show()
            self.raise_()
        elif self.focusWidget() is not None:
            self.focusWidget().clearFocus()
        self._slide.stop()
        self._slide.setStartValue(self.pos())
        self._slide.setEndValue(opened if is_open else closed)
        self._slide.start()

    def _slide_finished(self) -> None:
        if not self.is_open:
            self.hide()

    def place(self) -> None:
        """Keep to the window's right edge when it resizes."""
        self.setFixedHeight(self.parentWidget().height())
        opened, closed = self._edge_positions()
        self._slide.stop()
        self.move(opened if self.is_open else closed)
        self.setVisible(self.is_open)
