"""The global keys. Quit is Alt+F4 and nothing else: Esc shows and hides the panel."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QLineEdit


def handle_key(window, event) -> bool:
    """Global keys, caught before Qt's focus handling can claim Tab or the arrows."""
    if QApplication.activeModalWidget() or QApplication.activePopupWidget():
        return False

    key = event.key()
    modifiers = event.modifiers() & ~Qt.KeypadModifier
    repeat = event.isAutoRepeat()
    focus = QApplication.focusWidget()
    typing = isinstance(focus, (QLineEdit, QAbstractSpinBox))

    if modifiers == Qt.NoModifier and key == Qt.Key_Escape:
        if typing:
            focus.clearFocus()
        elif not repeat:
            window.toggle_panel()
        return True
    if modifiers == Qt.NoModifier and key == Qt.Key_F11:
        if not repeat:
            window.toggle_fullscreen()
        return True

    # Typing in a panel field never triggers shortcuts: an "r" in a path moves no file.
    if typing:
        return False

    if modifiers == Qt.ControlModifier and key == Qt.Key_Z:
        if not repeat:
            window.undo()
        return True
    if key == Qt.Key_Backtab:
        if not repeat:
            window.cycle_fit(-1)
        return True
    if modifiers != Qt.NoModifier:
        return False

    if key in (Qt.Key_A, Qt.Key_Left):
        window.flip_background(-1)
    elif key in (Qt.Key_D, Qt.Key_Right):
        window.flip_background(1)
    elif key in (Qt.Key_W, Qt.Key_Up):
        window.flip_overlay(-1)
    elif key in (Qt.Key_S, Qt.Key_Down):
        window.flip_overlay(1)
    elif key == Qt.Key_R:
        # Never on auto-repeat: holding the key must not dump a run of images.
        if not repeat:
            window.reject()
    elif key == Qt.Key_Tab:
        if not repeat:
            window.cycle_fit(1)
    else:
        return False
    return True
