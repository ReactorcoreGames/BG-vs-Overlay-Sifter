"""Second half of build_release.bat: assemble the release folder, check it, zip it, check the zip.

The check exists because the project folder holds files that must never reach the public zip:
the internal marketing doc, the owner's settings, and test material. It is an allowlist at the
top level plus a blocklist at every depth, so a new stray file fails the build by default.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import os
import shutil
import sys
import zipfile
from pathlib import Path

NAME = "BG vs Overlay Sifter"
EXE = f"{NAME}.exe"

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
RELEASE = DIST / NAME
ZIP = DIST / f"{NAME}.zip"
TEST_MATERIAL = (ROOT / "docs" / "testing BGs", ROOT / "docs" / "testing UIs")

TOP_LEVEL = {EXE, "_internal", "guide.md", "readme.md", "LICENSE", "promo", "licenses"}
REQUIRED = {
    EXE,
    "guide.md",
    "readme.md",
    "LICENSE",
    "_internal/assets/icon.ico",
    "_internal/assets/missing image error.jpg",
    "_internal/PySide6/plugins/platforms/qwindows.dll",
    "_internal/PySide6/plugins/imageformats/qico.dll",
    "promo/cover_1280x720.jpg",
    "promo/thumbnail_630x500.jpg",
    "licenses/THIRD-PARTY-NOTICES.md",
    "licenses/LGPL-3.0.txt",
    "licenses/GPL-3.0.txt",
    "licenses/Python-LICENSE.txt",
    "licenses/Pillow-LICENSE.txt",
}
# Lowercase. Any path component with one of these names fails, at any depth.
FORBIDDEN = {
    "promo.md",
    "promo_source",
    "make_promo_images.py",
    "make_trailer.py",
    "trailer",
    "config.json",
    "config.tmp",
    "old v2",
    "old wip",
    "docs",
    "testing bgs",
    "testing uis",
    "tests",
    "icon_og.jpg",
    "claude.md",
    "todo-checklist.md",
    "build_release.bat",
    "build_release.spec",
    "release_package.py",
    "licenseref-qt-commercial.txt",  # not the license this program uses Qt under
}


def assemble(release: Path = RELEASE) -> None:
    for name in ("guide.md", "readme.md", "LICENSE"):
        shutil.copy2(ROOT / name, release / name)
    shutil.copytree(ROOT / "promo", release / "promo", dirs_exist_ok=True)
    shutil.copytree(ROOT / "licenses", release / "licenses", dirs_exist_ok=True)

    notices = release / "licenses" / "THIRD-PARTY-NOTICES.md"
    text = notices.read_text(encoding="utf-8").replace("{PYSIDE6}", importlib.metadata.version("PySide6"))
    text = text.replace("{PILLOW}", importlib.metadata.version("Pillow")).replace("{PYTHON}", sys.version.split()[0])
    notices.write_text(text, encoding="utf-8")

    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", release / "licenses" / "Python-LICENSE.txt")
    pillow = importlib.metadata.distribution("Pillow")
    license_file = next(f for f in pillow.files if f.name == "LICENSE")
    shutil.copy2(pillow.locate_file(license_file), release / "licenses" / "Pillow-LICENSE.txt")


def problems_with_names(paths: list[str]) -> list[str]:
    """`paths` are files, relative to the release root, with forward slashes."""
    problems = []
    for path in paths:
        parts = path.split("/")
        if parts[0] not in TOP_LEVEL:
            problems.append(f"does not belong at the top level: {path}")
        forbidden = [part for part in parts if part.lower() in FORBIDDEN]
        if forbidden:
            problems.append(f"must not ship: {path}")
    for required in sorted(REQUIRED - set(paths)):
        problems.append(f"missing: {required}")
    return problems


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def problems_with_contents(contents: dict[str, bytes], source_root: Path = ROOT, test_material=TEST_MATERIAL) -> list[str]:
    """`promo/` must match the project's exactly, and no test image may ship under any name."""
    problems = []
    expected = {f"promo/{p.name}": p.read_bytes() for p in (source_root / "promo").iterdir() if p.is_file()}
    shipped = {path: data for path, data in contents.items() if path.startswith("promo/")}
    if {path: _digest(data) for path, data in shipped.items()} != {path: _digest(data) for path, data in expected.items()}:
        problems.append("promo/ differs from the project's promo/ folder")

    banned = {_digest(p.read_bytes()): p.name for folder in test_material if folder.is_dir() for p in folder.iterdir() if p.is_file()}
    for path, data in contents.items():
        if _digest(data) in banned:
            problems.append(f"test material shipped: {path} is {banned[_digest(data)]}")
    return problems


def folder_contents(release: Path) -> dict[str, bytes]:
    return {p.relative_to(release).as_posix(): p.read_bytes() for p in release.rglob("*") if p.is_file()}


def write_zip(release: Path, destination: Path) -> None:
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(release.rglob("*")):
            if path.is_file():
                archive.write(path, Path(release.name) / path.relative_to(release))


def zip_contents(destination: Path, root_name: str) -> tuple[dict[str, bytes], list[str]]:
    """The zip's files relative to its one root folder, plus any problem with its shape."""
    problems, contents = [], {}
    with zipfile.ZipFile(destination) as archive:
        corrupt = archive.testzip()
        if corrupt:
            problems.append(f"corrupt in the zip: {corrupt}")
        for name in archive.namelist():
            root, _, rest = name.partition("/")
            if root != root_name:
                problems.append(f"outside the zip's root folder: {name}")
            elif rest and not name.endswith("/"):
                contents[rest] = archive.read(name)
    return contents, problems


def fail(stage: str, problems: list[str]) -> None:
    print(f"\n*** RELEASE CHECK FAILED ({stage}). DO NOT UPLOAD. ***")
    for problem in problems:
        print(f"  {problem}")
    print()
    sys.exit(1)


def main() -> None:
    assemble()

    contents = folder_contents(RELEASE)
    problems = problems_with_names(sorted(contents)) + problems_with_contents(contents)
    if problems:
        fail("release folder", problems)

    # The zip only takes its final name after passing, so a failed check cannot leave one that looks finished.
    unchecked = ZIP.with_suffix(".unchecked")
    write_zip(RELEASE, unchecked)
    contents, problems = zip_contents(unchecked, NAME)
    problems += problems_with_names(sorted(contents)) + problems_with_contents(contents)
    if problems:
        fail("zip", problems)
    os.replace(unchecked, ZIP)

    print(f"Release check passed: {len(contents)} files.")
    print(f"{ZIP}  ({ZIP.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
