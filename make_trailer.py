"""Generate the YouTube trailer: the real program, cut to the music.

    .venv/Scripts/python.exe make_trailer.py            Assemble the video from trailer/frames
    .venv/Scripts/python.exe make_trailer.py --capture  Retake the frames first

Flipping in this program is a hard cut, so a real capture of each state, cut on a note, is what
it really looks like. --capture presses the real keys in the real window, on the real platform,
and covers the screen for about a minute without taking keyboard focus. Like the promo shots, it
needs docs/testing BGs and docs/testing UIs and works on a temporary copy, because R moves files.

The music is CC BY 4.0, so the credit on the end card and in promo.md's YouTube description must
stay. Never write a specific price or amount into the copy.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageChops, ImageDraw, ImageFont

from gui.theme import BORDER, FLESH, FLESH_DEEP, HAIRLINE, PANEL, RAISED, RIND, TEXT, TEXT_DIM
from make_promo_images import (
    DEMO,
    FONT_BLACK,
    FONT_BOLD,
    OVERLAY_ONE,
    TEST_BGS,
    TEST_OVERLAYS,
    fit_font,
    watermelon,
)

ROOT = Path(__file__).resolve().parent
TRAILER_DIR = ROOT / "trailer"
FRAMES_DIR = TRAILER_DIR / "frames"  # the captures, gitignored
MUSIC = TRAILER_DIR / "Prelude No. 2 - Chris Zabriskie.mp3"
OUTPUT = TRAILER_DIR / "BG vs Overlay Sifter - trailer.mp4"

WIDTH, HEIGHT = 1920, 1080
FPS = 60

# Measured from the music: when each bar's first note sounds, in seconds. The piece drifts a
# little, so a fixed tempo slides off the notes by up to 0.2s. Cuts are written in bars.
BARS = (0.58, 2.90, 5.22, 7.54, 9.86, 12.16, 14.44, 16.68, 18.96, 21.24, 23.50, 25.76, 28.04, 30.28)

INTRO_FADE_SECONDS = 0.35
END_CARD_BAR = 11.0
END_CROSSFADE_SECONDS = 0.3
DURATION_SECONDS = 30.5
PICTURE_FADE_SECONDS = 0.8
MUSIC_FADE_SECONDS = 3.0
MUSIC_GAIN = "6dB"  # peaks at -8.3 dB as supplied, and YouTube only ever turns things down
KEY_LIT_SECONDS = 0.22

# The footage sits above a strip, so a caption never covers what is being judged.
FOOTAGE_BOX = (128, 16, 1664, 936)
STRIP_TOP = 952
KEY_HEIGHT = 72

# These carry a readable signature in a corner, which would be a distraction in a trailer.
SIGNED_BACKGROUNDS = {"bg factory (1).jpg", "bg harbor (1).jpg", "bg plains (3).jpg", "bg sea (3).jpg"}

# -- The copy. This is the part to edit. ----------------------------------------------------

INTRO = (("Which backgrounds work", TEXT), ("behind your UI?", FLESH))
TITLE = (("BG vs OVERLAY", TEXT), ("SIFTER", FLESH))
TAGLINE = "Flip. Judge. Sort."
MADE_BY = "For Windows  |  by Reactorcore  |  reactorcore.itch.io"
CREDITS = "Music: Prelude No. 2 by Chris Zabriskie (CC BY 4.0)   |   Shown with overlays from Commander Wars"

# (first bar, caption, the keys shown beside it)
SCENES = (
    (1.0, "Flip through your backgrounds", ("A", "D")),
    (3.0, "Try every overlay on top", ("W", "S")),
    (5.0, "Move the bad ones out. Undo any time.", ("R", "Ctrl+Z")),
    (7.0, "Any canvas. Any placement. One panel.", ("Esc",)),
    (9.0, "Five background modes", ("Tab",)),
    (10.25, "Hold a key and fly through the folder", ("A", "D")),
)


class Shot(NamedTuple):
    bar: float
    key: str | None = None  # pressed for this shot, and lit in the video
    settings: dict | None = None  # changed through the panel, as a click there would
    first: tuple[str, ...] = ()  # pressed unseen, to get ready for this shot


HOME = {"aspect": "16:9", "anchor": "center", "offset_y": 0, "fit_mode": "fill"}

SHOTS = (
    Shot(1.0),
    Shot(1.5, "D"),
    Shot(2.0, "D"),
    Shot(2.25, "D"),
    Shot(2.5, "D"),
    Shot(2.75, "D"),
    Shot(3.0, "S"),
    Shot(3.5, "S"),
    Shot(4.0, "S"),
    Shot(4.5, "S"),
    Shot(5.0, "D"),
    Shot(5.5, "R"),
    Shot(6.0, "R"),
    Shot(6.5, "Ctrl+Z"),
    Shot(7.0, "Esc"),
    Shot(7.5, "W"),
    Shot(8.0, settings={"aspect": "1:1"}),
    Shot(8.5, settings={"aspect": "9:16", "anchor": "top", "offset_y": 240}),
    Shot(9.0, "Esc"),
    Shot(9.25, "Tab"),
    Shot(9.5, "Tab"),
    Shot(9.75, "Tab"),
    Shot(10.0, "Tab"),
    Shot(10.25, "D", settings=HOME, first=("S",)),
    Shot(10.375, "D"),
    Shot(10.5, "D"),
    Shot(10.625, "D"),
    Shot(10.75, "D"),
    Shot(10.875, "D"),
)


def bar_time(bar: float) -> float:
    index = int(bar)
    return BARS[index] + (bar - index) * (BARS[index + 1] - BARS[index])


# -- capture --------------------------------------------------------------------------------

def shuffled_names(folder: Path) -> list[tuple[Path, str]]:
    """Each background with a numbered name that deals the subjects out in turn.

    Sorted as they are, a flip would show four lakes in a row. This changes only the order
    the real program meets them in, so every shot is still one real key press from the last.
    The signed ones go last, past anything the trailer reaches.
    """
    groups: dict[str, list[Path]] = {}
    paths = sorted(folder.iterdir())
    for path in paths:
        if path.name in SIGNED_BACKGROUNDS:
            continue
        subject = re.sub(r"\s*\(\d+\)$", "", path.stem)
        groups.setdefault(subject, []).append(path)
    subjects = sorted(groups, key=lambda subject: subject != "bg lake")  # open on the lake
    dealt = []
    while any(groups.values()):
        dealt.extend(groups[subject].pop(0) for subject in subjects if groups[subject])
    dealt.extend(path for path in paths if path.name in SIGNED_BACKGROUNDS)
    return [(path, f"{number:02} {path.name}") for number, path in enumerate(dealt, 1)]


def capture() -> None:
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from gui import theme
    from gui.app import MainWindow, enable_dpi_awareness, set_taskbar_identity

    keys = {
        "A": (Qt.Key_A, Qt.NoModifier),
        "D": (Qt.Key_D, Qt.NoModifier),
        "W": (Qt.Key_W, Qt.NoModifier),
        "S": (Qt.Key_S, Qt.NoModifier),
        "R": (Qt.Key_R, Qt.NoModifier),
        "Tab": (Qt.Key_Tab, Qt.NoModifier),
        "Esc": (Qt.Key_Escape, Qt.NoModifier),
        "Ctrl+Z": (Qt.Key_Z, Qt.ControlModifier),
    }

    if DEMO.exists():
        raise SystemExit(f"{DEMO} already exists. Look at it and move it aside first.")
    if FRAMES_DIR.exists():
        shutil.move(str(FRAMES_DIR), tempfile.mkdtemp(prefix="sifter_old_frames_"))
    FRAMES_DIR.mkdir(parents=True)

    backgrounds = DEMO / "Backgrounds"
    overlays = DEMO / "Overlays"
    backgrounds.mkdir(parents=True)
    source_count = len(list(TEST_BGS.iterdir()))
    for path, name in shuffled_names(TEST_BGS):
        shutil.copy2(path, backgrounds / name)
    shutil.copytree(TEST_OVERLAYS, overlays)

    config = DEMO / "config.json"
    config.write_text(json.dumps({
        "bg_folder": str(backgrounds),
        "overlay_folder": str(overlays),
        "canvas_mode": "preset",
        "aspect": "16:9",
        "resolution": 1080,
        "last_overlay": OVERLAY_ONE,
    }), encoding="utf-8")

    enable_dpi_awareness()
    set_taskbar_identity()
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLE)
    window = MainWindow(config)

    def wait(milliseconds: int) -> None:
        # Not QTest.qWait, which starves the render threads.
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    def settle(milliseconds: int = 200) -> None:
        for _ in range(400):
            wait(25)
            if window._wanted is None:
                break
            if window.shown_background == window.sorter.current and window.frames.peek(window._wanted):
                break
        else:
            raise RuntimeError("The frame never arrived")
        wait(milliseconds)

    def grab(path: Path) -> None:
        image = window.screen().grabWindow(window.winId())
        if not image.save(str(path)):
            raise RuntimeError(f"Could not save {path}")
        if (image.width(), image.height()) != (WIDTH, HEIGHT):
            print(f"note: captured at {image.width()}x{image.height()}")

    def press(name: str) -> None:
        key, modifiers = keys[name]
        QTest.keyClick(window, key, modifiers)

    try:
        # On top, so nothing else lands in a grab, and never active, so typing cannot reach it.
        window.setWindowFlag(Qt.FramelessWindowHint)
        window.setWindowFlag(Qt.WindowStaysOnTopHint)
        window.setAttribute(Qt.WA_ShowWithoutActivating)
        window.setWindowState(Qt.WindowNoState)
        window.setGeometry(window.screen().geometry())
        window.show()
        settle(600)

        slide = window.panel._slide
        for index, shot in enumerate(SHOTS):
            for name in shot.first:
                press(name)
            for attribute, value in (shot.settings or {}).items():
                if attribute == "fit_mode":
                    window.settings.fit_mode = value
                    window.panel.sync()
                    window.refresh()
                else:
                    window.panel._set(attribute, value)
            window.toast.hide()  # a toast belongs to the shot that raised it
            stem = FRAMES_DIR / f"{index:02}"
            if shot.key == "Esc":
                # Stepped by hand, so the slide gets every frame however long a grab takes.
                press("Esc")
                slide.pause()
                for step in range(0, slide.duration(), 1000 // FPS):
                    slide.setCurrentTime(step)
                    wait(40)
                    grab(stem.with_name(f"{index:02}_{step:03}.png"))
                slide.resume()
                settle(400)
                grab(stem.with_name(f"{index:02}_999.png"))
            else:
                if shot.key:
                    press(shot.key)
                settle()
                grab(stem.with_name(f"{index:02}_000.png"))
            print(f"{shot.bar:6.3f} {shot.key or '-':7} {window.view._label}")
    finally:
        window.close()
        app.processEvents()
        parked = shutil.move(str(DEMO), tempfile.mkdtemp(prefix="sifter_demo_"))
        print(f"demo copy parked in {parked}")

    if len(list(TEST_BGS.iterdir())) != source_count:
        raise RuntimeError("The real test material changed")


# -- drawing --------------------------------------------------------------------------------

def ink_width(text: str, font: ImageFont.FreeTypeFont) -> int:
    box = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def centred(draw: ImageDraw.ImageDraw, centre_x: int, top: int, text: str, font, fill) -> int:
    """Draws with the ink's top at `top`. Returns the ink's bottom."""
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((centre_x - (box[2] - box[0]) / 2 - box[0], top - box[1]), text, font=font, fill=fill)
    return top + box[3] - box[1]


def intro_card() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PANEL)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_BLACK, 112)
    top = 400
    for line, colour in INTRO:
        top = centred(draw, WIDTH // 2, top, line, font, colour) + 44
    return image


def end_card() -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), PANEL)
    melon = watermelon(400)
    left = 200
    image.alpha_composite(melon, (left, 275))

    draw = ImageDraw.Draw(image)
    centre = left + melon.width + (WIDTH - left - melon.width - 90) // 2
    available = WIDTH - left - melon.width - 150
    top = 307
    for (line, colour), start in zip(TITLE, (100, 190)):
        top = centred(draw, centre, top, line, fit_font(FONT_BLACK, line, available, start), colour) + 34
    top = centred(draw, centre, top + 4, TAGLINE, ImageFont.truetype(FONT_BOLD, 56), RIND) + 44
    centred(draw, centre, top, MADE_BY, fit_font(FONT_BOLD, MADE_BY, available, 34), TEXT)
    centred(draw, WIDTH // 2, 1004, CREDITS, ImageFont.truetype(FONT_BOLD, 25), TEXT_DIM)
    return image.convert("RGB")


def draw_keys(image: Image.Image, labels: tuple[str, ...], lit: str | None) -> int:
    """The scene's keys at the strip's right end. The one just pressed lights up. Returns their left edge."""
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_BLACK, 34)
    top = STRIP_TOP + (HEIGHT - STRIP_TOP - KEY_HEIGHT) // 2
    right = FOOTAGE_BOX[0] + FOOTAGE_BOX[2]
    for label in reversed(labels):
        width = max(KEY_HEIGHT, ink_width(label, font) + 44)
        pressed = label == lit
        draw.rounded_rectangle(
            (right - width, top, right, top + KEY_HEIGHT), radius=12,
            fill=FLESH_DEEP if pressed else RAISED,
            outline=TEXT if pressed else HAIRLINE, width=3,
        )
        box = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (right - width + (width - (box[2] - box[0])) / 2 - box[0], top + (KEY_HEIGHT - (box[3] - box[1])) / 2 - box[1]),
            label, font=font, fill=TEXT if pressed else TEXT_DIM,
        )
        right -= width + 14
    return right


def footage_frame(capture_path: Path, caption: str, labels: tuple[str, ...], lit: str | None) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PANEL)
    left, top, width, height = FOOTAGE_BOX
    picture = Image.open(capture_path).convert("RGB").resize((width, height), Image.LANCZOS)
    image.paste(picture, (left, top))
    ImageDraw.Draw(image).rectangle((left - 2, top - 2, left + width + 1, top + height + 1), outline=BORDER, width=2)
    keys_left = draw_keys(image, labels, lit)
    font = fit_font(FONT_BLACK, caption, keys_left - left - 40, 52)
    draw = ImageDraw.Draw(image)
    box = draw.textbbox((0, 0), caption, font=font)
    draw.text((left - box[0], STRIP_TOP + (HEIGHT - STRIP_TOP - (box[3] - box[1])) / 2 - box[1]), caption, font=font, fill=TEXT)
    return image


# -- assembly -------------------------------------------------------------------------------

def scene_at(bar_seconds: float) -> tuple[str, tuple[str, ...]]:
    caption, labels = SCENES[0][1:]
    for bar, scene_caption, scene_labels in SCENES:
        if bar_seconds >= bar_time(bar):
            caption, labels = scene_caption, scene_labels
    return caption, labels


def timeline() -> list[tuple[int, list[Path], str | None]]:
    """For each shot: the video frame it starts on, its captures in order, and its key."""
    entries = []
    for index, shot in enumerate(SHOTS):
        captures = sorted(FRAMES_DIR.glob(f"{index:02}_*.png"))
        if not captures:
            raise SystemExit(f"{FRAMES_DIR} has no capture for shot {index}. Run with --capture.")
        entries.append((round(bar_time(shot.bar) * FPS), captures, shot.key))
    return entries


def build_video() -> None:
    entries = timeline()
    intro = intro_card()
    end = end_card()
    black = Image.new("RGB", (WIDTH, HEIGHT), "black")
    total = round(DURATION_SECONDS * FPS)
    first_footage = entries[0][0]
    end_start = round(bar_time(END_CARD_BAR) * FPS)
    crossfade = round(END_CROSSFADE_SECONDS * FPS)
    fade_start = total - round(PICTURE_FADE_SECONDS * FPS)
    music_fade_start = DURATION_SECONDS - MUSIC_FADE_SECONDS

    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-i", str(MUSIC),
        "-map", "0:v", "-map", "1:a", "-t", str(DURATION_SECONDS),
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-af", f"volume={MUSIC_GAIN},afade=t=out:st={music_fade_start}:d={MUSIC_FADE_SECONDS}",
        "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
        "-movflags", "+faststart", str(OUTPUT),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)

    last_state = None
    last_bytes = b""
    try:
        for frame in range(total):
            state, picture = None, None
            if frame < first_footage:
                start = round(BARS[0] * FPS)
                progress = (frame - start) / (INTRO_FADE_SECONDS * FPS)
                level = min(max(progress, 0.0), 1.0)
                state = ("intro", level)
                if state != last_state:
                    picture = Image.blend(black, intro, level)
            elif frame >= end_start + crossfade:
                level = max(0.0, (total - frame) / (total - fade_start)) if frame >= fade_start else 1.0
                state = ("end", level)
                if state != last_state:
                    picture = Image.blend(black, end, min(level, 1.0))
            else:
                current = [entry for entry in entries if entry[0] <= frame][-1]
                start, captures, key = current
                capture_path = captures[min(frame - start, len(captures) - 1)]
                caption, labels = scene_at(frame / FPS + 1e-6)
                lit = key if frame - start < KEY_LIT_SECONDS * FPS else None
                blend = (frame - end_start + 1) / crossfade if frame >= end_start else 0.0
                state = ("footage", capture_path, caption, lit, blend)
                if state != last_state:
                    picture = footage_frame(capture_path, caption, labels, lit)
                    if blend:
                        picture = Image.blend(picture, end, blend)
            if picture is not None:
                last_bytes = picture.tobytes()
                last_state = state
            encoder.stdin.write(last_bytes)
    finally:
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    print(f"wrote {OUTPUT.name}  {OUTPUT.stat().st_size // (1024 * 1024)} MB")


if __name__ == "__main__":
    if "--capture" in sys.argv:
        capture()
    build_video()
