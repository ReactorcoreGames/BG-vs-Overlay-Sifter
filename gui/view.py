"""The canvas on screen, the prototype's shadowed label, and the brief toast."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QLabel, QWidget

from . import theme

LABEL_MARGIN = 8
TOAST_MILLISECONDS = 2500


class CanvasView(QWidget):
    """Paints whichever frame it was last handed. Does no work beyond painting it."""

    resized = Signal()
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self._image = QImage()
        self._label = ""
        self._message = ""
        self.label_visible = True
        self._font = QFont("Segoe UI", 10)

    def pixel_size(self) -> tuple[int, int]:
        """The view in physical pixels, so frames stay sharp under display scaling."""
        ratio = self.devicePixelRatioF()
        return (max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio)))

    def show_frame(self, image: QImage, label: str) -> None:
        self._image = image
        self._label = label
        self._message = ""
        self.update()

    def show_message(self, message: str) -> None:
        self._image = QImage()
        self._label = ""
        self._message = message
        self.update()

    def set_label_visible(self, visible: bool) -> None:
        self.label_visible = visible
        self.update()

    def resizeEvent(self, event) -> None:
        self.resized.emit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def _target_rect(self) -> QRectF:
        """Pixel-exact when the frame was rendered for this size; scaled during a resize."""
        ratio = self.devicePixelRatioF()
        view_w, view_h = self.pixel_size()
        scale = min(view_w / self._image.width(), view_h / self._image.height())
        if abs(scale - 1.0) < 0.002:
            scale = 1.0
        width = round(self._image.width() * scale)
        height = round(self._image.height() * scale)
        return QRectF(
            ((view_w - width) // 2) / ratio,
            ((view_h - height) // 2) / ratio,
            width / ratio,
            height / ratio,
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.SURROUND))
        painter.setFont(self._font)

        if self._message:
            painter.setPen(QColor(theme.MESSAGE))
            painter.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self._message)
            return
        if self._image.isNull():
            return

        target = self._target_rect()
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(target, self._image)

        if self._label and self.label_visible:
            # The prototype's black-shadow trick: reads on any background, costs nothing.
            position = QPointF(target.left() + LABEL_MARGIN, target.bottom() - LABEL_MARGIN)
            painter.setPen(QColor("black"))
            painter.drawText(position + QPointF(1, 1), self._label)
            painter.setPen(QColor("white"))
            painter.drawText(position, self._label)


class Toast(QLabel):
    """One line of feedback that fades out by itself and never takes focus."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.hide()
        self._timer = QTimer(self, singleShot=True, interval=TOAST_MILLISECONDS)
        self._timer.timeout.connect(self.hide)

    def say(self, text: str) -> None:
        self.setText(text)
        self.adjustSize()
        self.place()
        self.show()
        self.raise_()
        self._timer.start()

    def place(self) -> None:
        parent = self.parentWidget()
        self.move((parent.width() - self.width()) // 2, parent.height() - self.height() - 40)
