"""The window, offscreen, against real test material copied to a temporary folder.

The offscreen platform has no fonts, so nothing here judges appearance. It proves that
keys do what they say and that the flip's guarantees hold.
"""
import shutil
import threading
import time
from pathlib import Path

import pytest
from PIL import Image
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

import core.compose
import gui.frames
from core.settings import Settings, load_settings, save_settings
from gui.app import MainWindow
from gui.panel import SidePanel

ROOT = Path(__file__).resolve().parent.parent
BGS = ROOT / "docs" / "testing BGs"
OVERLAYS = ROOT / "docs" / "testing UIs"
OVERLAY_NAMES = ("Full Screen UI Overlay (1).png", "Center Title Floating UI Element.png")


def need_test_material() -> None:
    """The test images are gitignored, so a fresh clone runs without them."""
    if not sorted(BGS.glob("*.jpg")) or not all((OVERLAYS / name).is_file() for name in OVERLAY_NAMES):
        pytest.skip("docs/testing BGs and docs/testing UIs are not here")


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def wait_until(app, condition, timeout=10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.005)
    return False


@pytest.fixture
def folders(tmp_path):
    need_test_material()
    bgs = tmp_path / "bgs"
    overlays = tmp_path / "overlays"
    bgs.mkdir()
    overlays.mkdir()
    for source in sorted(BGS.glob("*.jpg"))[:6]:
        shutil.copy(source, bgs)
    for name in OVERLAY_NAMES:
        shutil.copy(OVERLAYS / name, overlays)
    return bgs, overlays


@pytest.fixture
def window(app, tmp_path, folders):
    config = tmp_path / "config.json"
    save_settings(Settings(bg_folder=str(folders[0]), overlay_folder=str(folders[1])), config)
    win = MainWindow(config)
    win.resize(800, 500)
    win.show()
    app.processEvents()
    assert wait_until(app, lambda: win.shown_background is not None)
    yield win
    win.close()


def press(app, key, modifiers=Qt.NoModifier, repeat=False, target=None) -> None:
    target = target or QApplication.focusWidget() or QApplication.activeWindow()
    event = QKeyEvent(QEvent.KeyPress, key, modifiers, "", repeat)
    QApplication.sendEvent(target, event)


def settled(app, win) -> None:
    assert wait_until(app, lambda: win.shown_background == win.sorter.current)


def press_on(app, win, key, **kwargs) -> None:
    press(app, key, target=win, **kwargs)


def test_a_d_and_arrows_flip_and_wrap(app, window):
    first = window.sorter.current
    press_on(app, window, Qt.Key_D)
    second = window.sorter.current
    assert second != first
    press_on(app, window, Qt.Key_Left)
    assert window.sorter.current == first
    press_on(app, window, Qt.Key_A)
    assert window.sorter.current == window.sorter.paths[-1]
    press_on(app, window, Qt.Key_Right)
    assert window.sorter.current == first


def test_w_s_cycle_overlays_through_no_overlay(app, window):
    assert window.overlays.paths[0] is None
    start = window.overlays.index
    assert start == 1  # starts on the first real overlay, not on nothing
    press_on(app, window, Qt.Key_W)
    assert window.overlays.current is None
    press_on(app, window, Qt.Key_Down)
    assert window.overlays.index == start


def test_r_moves_the_shown_image_and_ctrl_z_returns_it(app, window, folders):
    bgs, _ = folders
    victim = window.shown_background
    order = list(window.sorter.paths)
    press_on(app, window, Qt.Key_R)
    assert not victim.exists()
    assert (bgs / "rejects" / victim.name).exists()
    settled(app, window)
    press_on(app, window, Qt.Key_Z, modifiers=Qt.ControlModifier)
    assert victim.exists()
    assert window.sorter.paths == order
    assert window.sorter.current == victim


def test_holding_r_moves_only_one_image(app, window, folders):
    bgs, _ = folders
    press_on(app, window, Qt.Key_R)
    settled(app, window)
    for _ in range(5):
        press_on(app, window, Qt.Key_R, repeat=True)
    assert len(list((bgs / "rejects").iterdir())) == 1


def test_r_only_ever_moves_what_is_on_screen(app, window, folders):
    """Pressing R twice before the next frame is up must not move an unseen image."""
    bgs, _ = folders
    window.frames.clear()
    press_on(app, window, Qt.Key_R)
    press_on(app, window, Qt.Key_R)
    press_on(app, window, Qt.Key_R)
    assert len(list((bgs / "rejects").iterdir())) == 1


def test_refuses_to_move_into_the_background_folder_itself(app, window, folders):
    bgs, _ = folders
    window.settings.reject_folder = str(bgs)
    before = sorted(p.name for p in bgs.iterdir())
    press_on(app, window, Qt.Key_R)
    assert sorted(p.name for p in bgs.iterdir()) == before


def test_tab_cycles_the_mode_rather_than_moving_focus(app, window):
    assert window.settings.fit_mode == "fill"
    seen = []
    for _ in range(5):
        press_on(app, window, Qt.Key_Tab)
        seen.append(window.settings.fit_mode)
    assert seen == ["fit", "stretch", "tile", "center", "fill"]
    assert window.panel._fit.currentData() == "fill"


def test_esc_toggles_the_panel_and_never_quits(app, window):
    assert not window.panel.is_open
    press_on(app, window, Qt.Key_Escape)
    assert window.panel.is_open
    press_on(app, window, Qt.Key_Escape)
    assert not window.panel.is_open
    assert window.isVisible()


def test_typing_in_a_panel_field_triggers_no_shortcuts(app, window, folders):
    window.panel.set_open(True)
    wait_until(app, lambda: window.panel.isVisible())
    edit = window.panel._overlay_edit
    edit.setFocus()
    assert wait_until(app, lambda: QApplication.focusWidget() is edit, timeout=1.0)
    current = window.sorter.current
    fit = window.settings.fit_mode
    for key in (Qt.Key_R, Qt.Key_D, Qt.Key_A):
        QApplication.sendEvent(edit, QKeyEvent(QEvent.KeyPress, key, Qt.NoModifier, "x"))
    assert window.sorter.current == current
    assert current.exists()
    assert window.settings.fit_mode == fit


def test_changing_a_setting_in_the_panel_renders_with_it(app, window):
    window.panel._set("canvas_mode", "custom")
    window.panel._set("custom_width", 320)
    window.panel._set("custom_height", 200)
    assert wait_until(app, lambda: window._canvas_size == (320, 200))
    assert window.panel._custom_row.isVisibleTo(window.panel)


def test_match_canvas_takes_the_overlay_size(app, window):
    assert wait_until(app, lambda: window._canvas_size in ((1920, 1020), (700, 140)))


def test_bad_folder_text_is_refused_and_not_saved(app, window):
    before = window.settings.overlay_folder
    window.panel._overlay_edit.setText("Z:/definitely/not/here")
    window.panel._commit_folder("overlay_folder", window.panel._overlay_edit)
    assert window.settings.overlay_folder == before


def test_unreadable_background_degrades_to_the_placeholder(app, tmp_path):
    bgs = tmp_path / "broken"
    bgs.mkdir()
    (bgs / "bad.jpg").write_text("not an image")
    config = tmp_path / "c.json"
    save_settings(Settings(bg_folder=str(bgs)), config)
    win = MainWindow(config)
    win.show()
    assert wait_until(app, lambda: win.shown_background is not None)
    assert "(unreadable)" in win.view._label
    win.close()


def test_first_run_opens_the_panel_and_asks_for_a_folder(app, tmp_path):
    win = MainWindow(tmp_path / "none.json")
    win.show()
    app.processEvents()
    assert win.panel.is_open
    assert "background folder" in win.view._message
    press_on(app, win, Qt.Key_D)
    press_on(app, win, Qt.Key_R)
    win.close()


def test_settings_and_position_survive_a_restart(app, tmp_path, folders):
    config = tmp_path / "config.json"
    save_settings(Settings(bg_folder=str(folders[0]), overlay_folder=str(folders[1])), config)
    win = MainWindow(config)
    win.show()
    press_on(app, win, Qt.Key_D)
    press_on(app, win, Qt.Key_D)
    press_on(app, win, Qt.Key_Tab)
    press_on(app, win, Qt.Key_W)
    current = win.sorter.current
    win.close()

    assert load_settings(config).fit_mode == "fit"
    again = MainWindow(config)
    assert again.sorter.current == current
    assert again.overlays.current is None
    again.close()


def test_flipping_never_decodes_or_renders_on_the_ui_thread(app, window, monkeypatch):
    threads = set()
    real_render = gui.frames.render_frame

    def spy(*args, **kwargs):
        threads.add(threading.current_thread())
        return real_render(*args, **kwargs)

    monkeypatch.setattr(gui.frames, "render_frame", spy)
    window.frames.clear()
    for _ in range(6):
        press_on(app, window, Qt.Key_D)
    assert wait_until(app, lambda: threads)
    settled(app, window)
    assert threading.main_thread() not in threads


def test_a_flip_costs_the_ui_thread_almost_nothing(app, window):
    for _ in range(3):
        press_on(app, window, Qt.Key_D)
        settled(app, window)
    started = time.perf_counter()
    for _ in range(30):
        press_on(app, window, Qt.Key_D)
    per_flip = (time.perf_counter() - started) / 30
    assert per_flip < 0.01, f"{per_flip * 1000:.1f}ms per flip"


def test_holding_a_key_keeps_the_picture_moving(app, window):
    """Even when the cursor outruns the workers, frames it passed through get shown."""
    window.frames.clear()
    shown = set()
    for _ in range(40):
        press_on(app, window, Qt.Key_D)
        app.processEvents()
        shown.add(window.view._label)
        time.sleep(0.02)
    assert len(shown) >= 3


def test_coming_back_to_the_window_picks_up_edits_on_disk(app, window, folders):
    bgs, _ = folders
    Image.new("RGB", (64, 64), (1, 2, 3)).save(bgs / "aaa new.png")
    window._reload_from_disk()
    assert any(p.name == "aaa new.png" for p in window.sorter.paths)


def test_no_refused_features_crept_in():
    """No export, no sessions, no layouts: v3's scope is the point of v3."""
    source = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "gui").glob("*.py"))
    for forbidden in ("export", "session", "layout_manager", "contact sheet", "favourite_"):
        assert forbidden not in source.lower(), forbidden


def click_canvas(window, button=Qt.LeftButton) -> None:
    QTest.mouseClick(window.view, button, Qt.NoModifier, QPoint(10, 10))


def test_clicking_the_canvas_opens_the_panel_with_an_image_showing(app, window):
    assert not window.panel.is_open
    click_canvas(window, Qt.RightButton)
    assert not window.panel.is_open
    click_canvas(window)
    assert window.panel.is_open


def test_clicking_the_canvas_never_closes_the_panel(app, window):
    window.panel.set_open(True)
    click_canvas(window)
    assert window.panel.is_open


def test_clicking_the_canvas_takes_focus_out_of_a_field(app, window):
    window.panel.set_open(True)
    wait_until(app, lambda: window.panel.isVisible())
    edit = window.panel._overlay_edit
    edit.setFocus()
    assert wait_until(app, lambda: QApplication.focusWidget() is edit, timeout=1.0)
    click_canvas(window)
    assert QApplication.focusWidget() is not edit
    current = window.sorter.current
    press_on(app, window, Qt.Key_D)
    assert window.sorter.current != current


def test_clicking_the_panel_does_not_reach_the_canvas(app, window):
    window.panel.set_open(True)
    wait_until(app, lambda: window.panel.isVisible())
    seen = []
    window.view.clicked.connect(lambda: seen.append(True))
    QTest.mouseClick(window.panel._canvas_readout, Qt.LeftButton)
    assert not seen


@pytest.mark.parametrize(
    "folder, expected",
    [("", "Choose a background folder"), ("Z:/not/here", "Folder not found"), ("EMPTY", "No images in")],
)
def test_every_empty_state_says_how_to_reach_settings(app, tmp_path, folder, expected):
    empty = tmp_path / "empty"
    empty.mkdir()
    config = tmp_path / "c.json"
    save_settings(Settings(bg_folder=str(empty) if folder == "EMPTY" else folder), config)
    win = MainWindow(config)
    win.show()
    assert expected in win.view._message
    assert "Press Esc" not in win.view._message  # the panel opened by itself, so it is already there
    press_on(app, win, Qt.Key_Escape)
    assert expected in win.view._message and "Press Esc or click" in win.view._message
    click_canvas(win)
    assert win.panel.is_open and "Press Esc" not in win.view._message
    win.close()


def test_moving_the_last_image_still_says_how_to_reach_settings(app, tmp_path):
    need_test_material()
    bgs = tmp_path / "one"
    bgs.mkdir()
    shutil.copy(sorted(BGS.glob("*.jpg"))[0], bgs)
    config = tmp_path / "c.json"
    save_settings(Settings(bg_folder=str(bgs)), config)
    win = MainWindow(config)
    win.show()
    assert wait_until(app, lambda: win.shown_background is not None)
    press_on(app, win, Qt.Key_R)
    assert "No images left" in win.view._message and "Press Esc or click" in win.view._message
    win.close()


@pytest.mark.parametrize("bad", ["!!!not base64", "abc", "\u00e9", "AAAA"])
def test_a_nonsense_window_geometry_costs_that_setting_not_the_launch(app, tmp_path, bad):
    config = tmp_path / "c.json"
    save_settings(Settings(window_geometry=bad), config)
    win = MainWindow(config)
    assert win.isMaximized() or win.windowState() & Qt.WindowMaximized
    win.close()


def test_only_coming_back_to_the_window_reloads_not_the_launch(app, window, monkeypatch):
    reloads = []
    monkeypatch.setattr(window, "_reload_from_disk", lambda: reloads.append(True))
    monkeypatch.setattr(window, "isActiveWindow", lambda: True)
    window._activated_before = False
    QApplication.sendEvent(window, QEvent(QEvent.ActivationChange))
    assert not reloads
    QApplication.sendEvent(window, QEvent(QEvent.ActivationChange))
    assert len(reloads) == 1


def test_every_panel_control_explains_itself(app, window):
    kinds = (QPushButton, QComboBox, QSpinBox, QLineEdit)
    # A spin box's inner field shows its parent's tooltip, because Qt passes the event up.
    controls = [
        c for c in window.panel.findChildren(QWidget)
        if isinstance(c, kinds) and not isinstance(c.parent(), QAbstractSpinBox)
    ]
    assert len(controls) > 20
    for control in controls:
        assert control.toolTip(), f"{type(control).__name__} {control.text() if hasattr(control, 'text') else ''}"


def test_tooltip_lines_stay_short_enough_to_read(app, window):
    """Plain-text tooltips do not wrap, so a long line would run as wide as it likes."""
    for widget in window.panel.findChildren(QWidget):
        for line in widget.toolTip().splitlines():
            assert len(line) <= 82, line
