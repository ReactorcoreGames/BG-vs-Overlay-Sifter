"""Generate promo/: the screenshots of the real program, the itch.io thumbnail and the cover.

    .venv/Scripts/python.exe make_promo_images.py                Thumbnail and cover only
    .venv/Scripts/python.exe make_promo_images.py --screenshots  Retake the screenshots first

This script is in the project so that a one-word change to the copy never means rewriting it:
edit the constants under "The copy" and run it. Everything in promo/ rebuilds from assets/ and
the clean captures in promo_source/, so it works on a fresh clone, and stamps never stack up.

--screenshots drives the real window on the real platform, full-screen for a few seconds, and
needs docs/testing BGs and docs/testing UIs. R really moves files, so it works on a temporary
copy. The copy lives at a short path because the panel shows folder paths on screen, and a temp
folder inside a user profile would print the Windows account name into a public image.

Everything is JPG: the screenshots came out 33-80% smaller than as PNG, with the panel's text
still clean at quality 92 and no chroma subsampling.

Never write a specific price or amount into the copy.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from gui.theme import FLESH, FLESH_DEEP, PANEL, RIND, TEXT

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "promo"
SOURCE_DIR = ROOT / "promo_source"  # clean captures, left out of the release zip
ART = ROOT / "assets" / "icon_og.jpg"
ICON = ROOT / "assets" / "icon.ico"
ICON_BOX_IN_ART = (170, 170, 1348, 1348)  # measured: the part of the art the 256px icon shows
TEST_BGS = ROOT / "docs" / "testing BGs"
TEST_OVERLAYS = ROOT / "docs" / "testing UIs"
DEMO = Path("C:/Sifter demo")

OVERLAY_ONE = "Full Screen UI Overlay (1).png"
OVERLAY_TWO = "Full Screen UI Overlay (2).png"
OVERLAY_TITLE = "Center Title Floating UI Element.png"
TOAST_MILLISECONDS = 2800  # past the toast's own 2500, so one shot's toast cannot reach the next

JPG = {"quality": 92, "optimize": True, "subsampling": 0}

FONT_BLACK = "C:/Windows/Fonts/seguibl.ttf"  # Segoe UI Black
FONT_BOLD = "C:/Windows/Fonts/segoeuib.ttf"

SHOT_FLIP = "shot_1_flipping.jpg"
SHOT_PANEL = "shot_2_panel.jpg"
SHOT_MOVED = "shot_3_moved.jpg"
SHOT_TITLE = "shot_4_title.jpg"
SHOT_PORTRAIT = "shot_5_portrait.jpg"

# -- The copy. This is the part to edit. ----------------------------------------------------

THUMB_TITLE = ("BG vs", "OVERLAY", "SIFTER")
THUMB_TAGLINE = "Flip. Judge. Sort."

COVER_TITLE = ("BG vs OVERLAY", "SIFTER")
COVER_SUBTITLE = "Which backgrounds work behind your UI?"
COVER_KEYS = (
    ("A / D", "flip backgrounds"),
    ("W / S", "flip overlays"),
    ("R", "move it out"),
    ("Ctrl+Z", "take it back"),
)
COVER_FOOTER = "Made by Reactorcore  |  reactorcore.itch.io"

# Screenshot: (headline, detail, centre of the stamp). Placed over what the shot can spare.
STAMPS = {
    SHOT_FLIP: ("SEE YOUR UI OVER\nANY BACKGROUND", "Flip quickly through many BGs and Overlays by keyboard", (1195, 640)),
    SHOT_PANEL: ("EVERY SETTING IN ONE PANEL", "Tweak how you want the result to look globally and quickly", (880, 145)),
    SHOT_MOVED: ("PRESS R TO MOVE/REJECT/FAVORITE BGs", "Ctrl+Z brings them back if you change your mind", (610, 225)),
    SHOT_TITLE: ("PLACE THE LOOSE OVERLAY ELEMENT ANYWHERE", "9 anchor points plus a pixel offset", (960, 840)),
    SHOT_PORTRAIT: ("TEST ANY\nASPECT RATIO OR RESOLUTION", "Choose from easy presets or your own custom size", (525, 540)),
}


# -- screenshots ----------------------------------------------------------------------------

def take_screenshots() -> None:
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from gui import theme
    from gui.app import MainWindow, enable_dpi_awareness, set_taskbar_identity

    if DEMO.exists():
        raise SystemExit(f"{DEMO} already exists. Look at it and move it aside first.")
    backgrounds = DEMO / "Backgrounds"
    overlays = DEMO / "Overlays"
    shutil.copytree(TEST_BGS, backgrounds)
    shutil.copytree(TEST_OVERLAYS, overlays)
    source_count = len(list(TEST_BGS.iterdir()))

    config = DEMO / "config.json"
    config.write_text(json.dumps({
        "bg_folder": str(backgrounds),
        "overlay_folder": str(overlays),
    }), encoding="utf-8")

    enable_dpi_awareness()
    set_taskbar_identity()
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.STYLE)
    window = MainWindow(config)

    def wait(milliseconds: int) -> None:
        # Not QTest.qWait, which starves the render threads: a first frame that takes about
        # 0.5s in the real program took about 12s under it.
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    def settle(milliseconds: int = 250) -> None:
        """Until the frame under the cursor is the one on screen, then past any slide."""
        for _ in range(400):
            wait(25)
            if window._wanted is None:
                break
            if window.shown_background == window.sorter.current and window.frames.peek(window._wanted):
                break
        else:
            raise RuntimeError("The frame never arrived")
        wait(milliseconds)

    def go_to(background: str, overlay: str) -> None:
        for _ in range(len(window.sorter.paths)):
            if window.sorter.current.name == background:
                break
            QTest.keyClick(window, Qt.Key_D)
        for _ in range(len(window.overlays.paths) + 1):
            if window.overlays.current and window.overlays.current.name == overlay:
                break
            QTest.keyClick(window, Qt.Key_S)
        settle()

    def shoot(name: str) -> None:
        image = window.screen().grabWindow(window.winId())
        lossless = DEMO / "shot.png"
        image.save(str(lossless))
        with Image.open(lossless) as grabbed:
            grabbed.convert("RGB").save(SOURCE_DIR / name, **JPG)
        print(f"took {name}  {image.width()}x{image.height()}")

    try:
        # Frameless at the screen's size, not F11: fullscreen hides the filename label, and a
        # title bar would make the picture wider than 16:9.
        window.setWindowFlag(Qt.FramelessWindowHint)
        window.setWindowState(Qt.WindowNoState)
        window.setGeometry(window.screen().geometry())
        window.show()
        window.activateWindow()
        settle(600)

        go_to("bg lake (1).jpg", OVERLAY_ONE)
        shoot(SHOT_FLIP)

        go_to("bg forest (3).jpg", OVERLAY_TWO)
        QTest.keyClick(window, Qt.Key_Escape)
        settle(500)
        shoot(SHOT_PANEL)
        QTest.keyClick(window, Qt.Key_Escape)
        settle(500)

        go_to("bg city (2).jpg", OVERLAY_TWO)
        QTest.keyClick(window, Qt.Key_R)
        settle(100)
        shoot(SHOT_MOVED)
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
        settle(TOAST_MILLISECONDS)
        if len([p for p in backgrounds.iterdir() if p.is_file()]) != source_count:
            raise RuntimeError("The undo did not bring the moved file back")

        window.panel._set("canvas_mode", "preset")
        window.panel._set("aspect", "16:9")
        window.panel._set("resolution", 1080)
        go_to("bg mountains (1).jpg", OVERLAY_TITLE)
        shoot(SHOT_TITLE)

        window.panel._set("aspect", "9:16")
        window.panel._set("anchor", "top")
        window.panel._set("offset_y", 240)
        go_to("bg road (1).jpg", OVERLAY_TITLE)
        QTest.keyClick(window, Qt.Key_Escape)
        settle(500)
        shoot(SHOT_PORTRAIT)
    finally:
        window.close()
        app.processEvents()
        parked = shutil.move(str(DEMO), tempfile.mkdtemp(prefix="sifter_demo_"))
        print(f"demo copy parked in {parked}")

    if len(list(TEST_BGS.iterdir())) != source_count:
        raise RuntimeError("The real test material changed")


# -- drawing helpers ------------------------------------------------------------------------

def fit_font(path: str, text: str, max_width: int, start: int) -> ImageFont.FreeTypeFont:
    """Largest size at or below `start` that fits. Measured, because widths are never as assumed."""
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for size in range(start, 11, -1):
        font = ImageFont.truetype(path, size)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return ImageFont.truetype(path, 12)


def text_height(font: ImageFont.FreeTypeFont, text: str) -> int:
    box = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)
    return box[3] - box[1]


def shadowed_text(img, left, top, text, font, fill, blur=7, stroke=0) -> int:
    """Draws with the visible ink's top-left at (left, top), over a heavy shadow. Returns the ink's bottom."""
    draw = ImageDraw.Draw(img)
    box = draw.textbbox((0, 0), text, font=font)
    x, y = left - box[0], top - box[1]
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x + 2, y + 5), text, font=font, fill=(0, 0, 0, 255), stroke_width=stroke + 3)
    for _ in range(2):  # twice, so the shadow keeps a dense core as well as a wide edge
        img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(img).text((x, y), text, font=font, fill=fill, stroke_width=stroke, stroke_fill=(10, 18, 13, 255))
    return top + box[3] - box[1]


def fill_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = max(size[0] / image.width, size[1] / image.height)
    scaled = image.resize((round(image.width * scale) + 1, round(image.height * scale) + 1), Image.LANCZOS)
    left, top = (scaled.width - size[0]) // 2, (scaled.height - size[1]) // 2
    return scaled.crop((left, top, left + size[0], top + size[1]))


def mosaic_ground(size: tuple[int, int], tile_width: int) -> Image.Image:
    """Dense real detail, pushed back in the rind's green so the text in front can win."""
    tile_height = tile_width * 9 // 16
    # The boxes keep the test overlay's logo out: a store image must not read as that game's.
    sources = (
        (SHOT_MOVED, None),
        (SHOT_TITLE, (500, 602, 1350, 1080)),
        (SHOT_FLIP, None),
        (SHOT_PANEL, None),
        (SHOT_PORTRAIT, (656, 600, 1264, 942)),
    )
    tiles = [
        fill_crop(Image.open(SOURCE_DIR / name).convert("RGB").crop(box or (0, 0, 1920, 1080)), (tile_width, tile_height))
        for name, box in sources
    ]
    ground = Image.new("RGB", size, PANEL)
    count = 0
    for row in range(size[1] // tile_height + 1):
        shift = -(row % 2) * tile_width // 2
        for column in range(size[0] // tile_width + 2):
            ground.paste(tiles[count % len(tiles)], (shift + column * tile_width, row * tile_height))
            count += 1
    ground = ImageEnhance.Brightness(ground).enhance(0.55)
    tint = Image.new("RGB", size, PANEL)
    return Image.blend(ground, tint, 0.45).convert("RGBA")


def card(name: str, width: int, angle: float) -> Image.Image:
    """A screenshot as a tilted print, to read as flipping through a stack."""
    image = Image.open(SOURCE_DIR / name).convert("RGB")
    image = image.resize((width, width * image.height // image.width), Image.LANCZOS)
    edge = max(4, width // 90)
    framed = Image.new("RGBA", (image.width + edge * 2, image.height + edge * 2), TEXT)
    framed.paste(image, (edge, edge))
    return framed.rotate(angle, Image.BICUBIC, expand=True)


def paste_with_shadow(img: Image.Image, layer: Image.Image, position: tuple[int, int], blur=14) -> None:
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 215), (position[0] + 6, position[1] + 12), layer.getchannel("A"))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur)))
    img.alpha_composite(layer, position)


def watermelon(size: int) -> Image.Image:
    """The art cut out, using the icon's traced silhouette, as a sticker with a cream edge."""
    icon = Image.open(ICON)
    icon.size = (256, 256)
    icon.load()
    # Blurring then thresholding turns the upscaled mask's stair-steps back into a smooth curve.
    mask = icon.convert("RGBA").getchannel("A").resize((size, size), Image.LANCZOS)
    mask = mask.filter(ImageFilter.GaussianBlur(size / 300)).point(lambda value: 255 if value > 110 else 0)
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    art = Image.open(ART).convert("RGB").crop(ICON_BOX_IN_ART).resize((size, size), Image.LANCZOS)

    margin = max(6, size // 40)
    sticker = Image.new("RGBA", (size + margin * 2, size + margin * 2), (0, 0, 0, 0))
    edge = Image.new("L", sticker.size, 0)
    edge.paste(mask, (margin, margin))
    edge = edge.filter(ImageFilter.MaxFilter(margin * 2 - 1 if margin % 2 == 0 else margin * 2 + 1))
    edge = edge.filter(ImageFilter.GaussianBlur(1))
    sticker.paste(TEXT, (0, 0), edge)
    sticker.paste(art, (margin, margin), mask)
    return sticker


def key_cap(img, left, top, text, font, height) -> int:
    """A keyboard key, drawn. Returns its right edge."""
    draw = ImageDraw.Draw(img)
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0] + height // 2
    draw.rounded_rectangle((left, top, left + width, top + height), radius=height // 6,
                           fill=FLESH_DEEP, outline=TEXT, width=max(2, height // 20))
    draw.text((left + (width - (box[2] - box[0])) / 2 - box[0], top + (height - (box[3] - box[1])) / 2 - box[1]),
              text, font=font, fill=TEXT)
    return left + width


def stamp(headline: str, detail: str) -> Image.Image:
    """A tilted advert stamp that says plainly what the picture shows."""
    head_font = ImageFont.truetype(FONT_BLACK, 50)
    detail_font = ImageFont.truetype(FONT_BOLD, 28)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    head_box = measure.multiline_textbbox((0, 0), headline, font=head_font, align="center", spacing=6)
    detail_box = measure.textbbox((0, 0), detail, font=detail_font)
    head_w, head_h = head_box[2] - head_box[0], head_box[3] - head_box[1]
    detail_w, detail_h = detail_box[2] - detail_box[0], detail_box[3] - detail_box[1]
    pad, gap = 30, 16
    width = round(max(head_w, detail_w)) + pad * 2
    height = round(head_h + gap + detail_h) + pad * 2

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=16, fill=FLESH_DEEP, outline=TEXT, width=5)
    draw.rounded_rectangle((10, 10, width - 11, height - 11), radius=9, outline=TEXT, width=2)
    draw.multiline_text(((width - head_w) / 2 - head_box[0], pad - head_box[1]), headline, font=head_font,
                        fill=TEXT, align="center", spacing=6)
    draw.text(((width - detail_w) / 2 - detail_box[0], pad + head_h + gap - detail_box[1]), detail,
              font=detail_font, fill=TEXT)
    return image.rotate(3, Image.BICUBIC, expand=True)


def make_stamped_screenshots() -> list[Path]:
    written = []
    for name, (headline, detail, centre) in STAMPS.items():
        image = Image.open(SOURCE_DIR / name).convert("RGBA")
        badge = stamp(headline, detail)
        paste_with_shadow(image, badge, (centre[0] - badge.width // 2, centre[1] - badge.height // 2))
        image.convert("RGB").save(OUT_DIR / name, **JPG)
        written.append(OUT_DIR / name)
    return written


# -- the two store images -------------------------------------------------------------------

def make_thumbnail() -> Path:
    W, H = 630, 500
    img = mosaic_ground((W, H), 210)
    paste_with_shadow(img, card(SHOT_MOVED, 330, 7), (292, 10))
    paste_with_shadow(img, card(SHOT_PANEL, 330, -5), (268, 92))
    melon = watermelon(190)
    paste_with_shadow(img, melon.rotate(-8, Image.BICUBIC, expand=True), (W - 212, H - 230))

    margin = 26
    top = 24
    for line, colour, start, width in (
        (THUMB_TITLE[0], TEXT, 92, 340),
        (THUMB_TITLE[1], FLESH, 96, 400),
        (THUMB_TITLE[2], TEXT, 112, 400),
    ):
        font = fit_font(FONT_BLACK, line, width, start)
        top = shadowed_text(img, margin, top, line, font, colour, stroke=2) + 20

    tagline = fit_font(FONT_BLACK, THUMB_TAGLINE, 400, 46)
    shadowed_text(img, margin, H - margin - text_height(tagline, THUMB_TAGLINE), THUMB_TAGLINE, tagline, RIND, blur=5, stroke=2)

    out = OUT_DIR / "thumbnail_630x500.jpg"
    img.convert("RGB").save(out, **JPG)
    return out


def make_cover() -> Path:
    W, H = 1280, 720
    img = mosaic_ground((W, H), 320)
    paste_with_shadow(img, card(SHOT_MOVED, 560, 8), (770, 14))
    paste_with_shadow(img, card(SHOT_FLIP, 590, -3), (745, 205))
    melon = watermelon(280)
    paste_with_shadow(img, melon.rotate(-8, Image.BICUBIC, expand=True), (W - 330, H - 330), blur=18)

    margin = 44
    top = 34
    title_width = 720
    for line, colour, start in ((COVER_TITLE[0], TEXT, 92), (COVER_TITLE[1], FLESH, 160)):
        font = fit_font(FONT_BLACK, line, title_width, start)
        top = shadowed_text(img, margin, top, line, font, colour, blur=8, stroke=2) + 24

    subtitle = fit_font(FONT_BOLD, COVER_SUBTITLE, title_width - 20, 40)
    top = shadowed_text(img, margin, top + 2, COVER_SUBTITLE, subtitle, RIND, blur=5, stroke=1) + 32

    cap_font = ImageFont.truetype(FONT_BLACK, 34)
    meaning_font = ImageFont.truetype(FONT_BOLD, 40)
    cap_height = 60
    cap_width = max(ImageDraw.Draw(img).textlength(key, font=cap_font) for key, _ in COVER_KEYS) + cap_height // 2
    for key, meaning in COVER_KEYS:
        key_cap(img, margin, top, key, cap_font, cap_height)
        ink = text_height(meaning_font, meaning)
        shadowed_text(img, margin + round(cap_width) + 24, top + (cap_height - ink) // 2, meaning, meaning_font, TEXT, blur=5, stroke=1)
        top += cap_height + 14

    footer = ImageFont.truetype(FONT_BOLD, 26)
    shadowed_text(img, margin, H - 26 - text_height(footer, COVER_FOOTER), COVER_FOOTER, footer, TEXT, blur=4, stroke=1)

    out = OUT_DIR / "cover_1280x720.jpg"
    img.convert("RGB").save(out, **JPG)
    return out


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    SOURCE_DIR.mkdir(exist_ok=True)
    if "--screenshots" in sys.argv:
        take_screenshots()
    for path in (*make_stamped_screenshots(), make_thumbnail(), make_cover()):
        with Image.open(path) as written:
            print(f"wrote {path.name}  {written.width}x{written.height}  {path.stat().st_size // 1024} KB")
