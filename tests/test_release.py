"""The release check, on small fake releases. Nothing here builds anything or needs dist/."""
import re
import subprocess
import sys
from fnmatch import fnmatch

import pytest

import release_package
from release_package import (
    EXE,
    FORBIDDEN,
    NAME,
    REQUIRED,
    TOP_LEVEL,
    problems_with_contents,
    problems_with_names,
    write_zip,
    zip_contents,
)

ROOT = release_package.ROOT


def test_a_complete_release_passes():
    assert problems_with_names(sorted(REQUIRED)) == []


@pytest.mark.parametrize(
    "stray",
    [
        "promo.md",
        "config.json",
        "make_promo_images.py",
        "make_trailer.py",
        "trailer/Prelude No. 2 - Chris Zabriskie.mp3",
        "promo_source/shot_1_flipping.jpg",
        "old v2/main.py",
        "old wip/bg_tester.py",
        "docs/testing BGs/bg.jpg",
        "docs/testing UIs/overlay.png",
        "CLAUDE.md",
    ],
)
def test_a_private_file_at_the_top_fails(stray):
    problems = problems_with_names(sorted(REQUIRED | {stray}))
    assert any(stray in problem for problem in problems)


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_every_forbidden_name_fails_at_any_depth(name):
    stray = f"_internal/somewhere/{name}"
    assert any(stray in problem for problem in problems_with_names(sorted(REQUIRED | {stray})))


def test_forbidden_names_ignore_case():
    assert problems_with_names(sorted(REQUIRED | {"_internal/Config.JSON"}))


def test_an_unknown_top_level_file_fails_by_default():
    assert problems_with_names(sorted(REQUIRED | {"notes.txt"}))


@pytest.mark.parametrize("required", sorted(REQUIRED))
def test_a_missing_required_file_fails(required):
    assert any(required in problem for problem in problems_with_names(sorted(REQUIRED - {required})))


def test_every_required_file_sits_under_an_allowed_top_level_name():
    assert {path.split("/")[0] for path in REQUIRED} <= TOP_LEVEL


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "project"
    (root / "promo").mkdir(parents=True)
    (root / "promo" / "cover.jpg").write_bytes(b"cover")
    return root


def test_matching_promo_passes(source):
    assert problems_with_contents({"promo/cover.jpg": b"cover"}, source, ()) == []


@pytest.mark.parametrize(
    "contents", [{}, {"promo/cover.jpg": b"edited"}, {"promo/cover.jpg": b"cover", "promo/extra.jpg": b"x"}]
)
def test_promo_that_differs_from_the_project_fails(source, contents):
    assert problems_with_contents(contents, source, ())


def test_a_test_image_fails_even_under_another_name(source, tmp_path):
    material = tmp_path / "testing BGs"
    material.mkdir()
    (material / "bg.jpg").write_bytes(b"picture")
    contents = {"promo/cover.jpg": b"cover", "_internal/renamed.dat": b"picture"}
    assert any("bg.jpg" in problem for problem in problems_with_contents(contents, source, (material,)))


def test_the_zip_holds_one_root_folder_and_its_files_read_back(tmp_path):
    release = tmp_path / NAME
    (release / "promo").mkdir(parents=True)
    (release / "guide.md").write_bytes(b"guide")
    (release / "promo" / "cover.jpg").write_bytes(b"cover")
    destination = tmp_path / "out.zip"
    write_zip(release, destination)
    contents, problems = zip_contents(destination, NAME)
    assert problems == []
    assert contents == {"guide.md": b"guide", "promo/cover.jpg": b"cover"}


def test_a_zip_with_the_wrong_root_is_a_problem(tmp_path):
    release = tmp_path / "Wrong name"
    release.mkdir()
    (release / "guide.md").write_bytes(b"guide")
    destination = tmp_path / "out.zip"
    write_zip(release, destination)
    assert zip_contents(destination, NAME)[1]


def test_the_docs_name_the_exe_the_build_produces():
    for doc in ("guide.md", "readme.md"):
        assert EXE in (ROOT / doc).read_text(encoding="utf-8")


def test_the_build_recipe_uses_the_same_name():
    assert f'NAME = "{NAME}"' in (ROOT / "build_release.spec").read_text(encoding="utf-8")
    assert f"set NAME={NAME}" in (ROOT / "build_release.bat").read_text(encoding="utf-8")


def test_the_license_files_ship_from_the_project():
    folder = ROOT / "licenses"
    assert (folder / "THIRD-PARTY-NOTICES.md").is_file()
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in (folder / "LGPL-3.0.txt").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in (folder / "GPL-3.0.txt").read_text(encoding="utf-8")


LOAD_EVERY_FORMAT = """
import sys
from pathlib import Path
from PIL import Image
from core.compose import load_background, load_overlay
from core.sorter import IMAGE_EXTENSIONS

folder = Path(sys.argv[1])
for extension in IMAGE_EXTENSIONS:
    for mode in ("RGB", "RGBA"):
        if mode == "RGBA" and extension in (".jpg", ".jpeg", ".bmp"):
            continue
        path = folder / f"{mode}{extension}"
        Image.new(mode, (4, 4), "red").save(path)
        load_background(path)
        load_overlay(path)
print(" ".join(name for name in sys.modules if name.startswith("PIL._")))
"""


def test_the_build_strips_nothing_that_loading_a_supported_format_imports(tmp_path):
    """A stripped Pillow module does not fail the build: that format just reads as unreadable."""
    spec = (ROOT / "build_release.spec").read_text(encoding="utf-8")
    stripped = re.findall(r'"(pil/[^"]+)"', spec)
    assert stripped
    result = subprocess.run(
        [sys.executable, "-c", LOAD_EVERY_FORMAT, str(tmp_path)], capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    imported = result.stdout.split()
    assert "PIL._imaging" in imported
    for name in imported:
        path = name.replace(".", "/").lower() + ".cp313-win_amd64.pyd"
        assert not any(fnmatch(path, pattern) for pattern in stripped), name
