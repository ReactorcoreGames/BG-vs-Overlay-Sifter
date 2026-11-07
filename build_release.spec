# PyInstaller recipe, run by build_release.bat. A one-folder, windowed build.
#
# UNUSED lists what PyInstaller collects but the program never touches. Pillow decodes every
# image, so Qt only needs its Windows platform, its style, and the .ico reader for the window
# icon. Filtering here means none of it ever reaches dist/. After changing this list, retest
# the frozen build by hand: a missing part fails at runtime, not at build time. PIL's
# _imagingmath looks unused but must stay: the GIF plugin imports ImageMath, and without it
# every GIF silently shows as unreadable.
from fnmatch import fnmatch
from pathlib import Path

NAME = "BG vs Overlay Sifter"
ROOT = Path(SPECPATH)

UNUSED = (
    "pyside6/opengl32sw.dll",  # software OpenGL; nothing here uses OpenGL
    "pyside6/qt6network.dll",
    "pyside6/qt6opengl.dll",
    "pyside6/qt6pdf.dll",
    "pyside6/qt6qml*.dll",
    "pyside6/qt6quick*.dll",
    "pyside6/qt6svg.dll",
    "pyside6/qt6virtualkeyboard.dll",
    "pyside6/qtnetwork.pyd",
    "pyside6/translations/*",  # the program is English and never loads a translator
    "pyside6/plugins/generic/*",
    "pyside6/plugins/iconengines/*",
    "pyside6/plugins/networkinformation/*",
    "pyside6/plugins/platforminputcontexts/*",
    "pyside6/plugins/tls/*",
    "pyside6/plugins/platforms/qdirect2d.dll",
    "pyside6/plugins/platforms/qminimal.dll",
    "pyside6/plugins/platforms/qoffscreen.dll",
    "pyside6/plugins/imageformats/q[!i]*.dll",  # everything except qico.dll and qicns.dll
    "pyside6/plugins/imageformats/qicns.dll",
    "pil/_avif*",  # AVIF is not in IMAGE_EXTENSIONS
    "pil/_imagingft*",  # fonts, used only by make_promo_images.py
    "pil/_imagingcms*",
    "pil/_imagingtk*",
    "_ssl.pyd",
    "_hashlib.pyd",
    "libcrypto-3*.dll",
    "libssl-3*.dll",
)


def used(entries):
    def keep(entry):
        name = entry[0].replace("\\", "/").lower()
        return not any(fnmatch(name, pattern) for pattern in UNUSED)

    return [entry for entry in entries if keep(entry)]


analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "assets" / "missing image error.jpg"), "assets"),
    ],
    excludes=["PySide6.QtNetwork", "ssl", "tkinter", "unittest", "pydoc"],
)
analysis.binaries = used(analysis.binaries)
analysis.datas = used(analysis.datas)

pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    icon=str(ROOT / "assets" / "icon.ico"),
    console=False,  # --windowed
    upx=False,  # UPX-packed Qt DLLs are a known cause of antivirus false positives
)
COLLECT(exe, analysis.binaries, analysis.datas, name=NAME, upx=False)
