"""The file moves: the one part of the program that can lose someone's work."""
from pathlib import Path

import pytest

from core.settings import NO_OVERLAY
from core.sorter import OverlayCursor, Sorter, scan_images, unique_destination


@pytest.fixture
def folder(tmp_path):
    bgs = tmp_path / "bgs"
    bgs.mkdir()
    for name in ("a.jpg", "b.jpg", "c.jpg", "d.jpg"):
        (bgs / name).write_text(name)
    return bgs


def sorter_on(folder, start="") -> Sorter:
    sorter = Sorter()
    sorter.set_folder(folder, start)
    return sorter


def names(sorter) -> list[str]:
    return [p.name for p in sorter.paths]


def test_scan_is_flat_and_never_sees_the_rejects_inside(folder):
    (folder / "rejects").mkdir()
    (folder / "rejects" / "old.jpg").write_text("x")
    (folder / "notes.txt").write_text("x")
    assert [p.name for p in scan_images(folder)] == ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]


def test_scan_sorts_numbers_naturally(tmp_path):
    for name in ("bg (10).jpg", "bg (2).jpg", "BG (1).JPG"):
        (tmp_path / name).write_text("x")
    assert [p.name for p in scan_images(tmp_path)] == ["BG (1).JPG", "bg (2).jpg", "bg (10).jpg"]


def test_scan_of_missing_folder_is_empty(tmp_path):
    assert scan_images(tmp_path / "nope") == []


def test_collisions_count_up(tmp_path):
    assert unique_destination(tmp_path, "foo.jpg").name == "foo.jpg"
    (tmp_path / "foo.jpg").write_text("x")
    assert unique_destination(tmp_path, "foo.jpg").name == "foo (2).jpg"
    (tmp_path / "foo (2).jpg").write_text("x")
    assert unique_destination(tmp_path, "foo.jpg").name == "foo (3).jpg"


def test_moving_never_overwrites_an_earlier_reject(folder, tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "a.jpg").write_text("earlier reject")
    sorter = sorter_on(folder)
    sorter.move_out(sorter.paths[0], target)
    assert (target / "a.jpg").read_text() == "earlier reject"
    assert (target / "a (2).jpg").read_text() == "a.jpg"


def test_moving_lands_on_the_next_image_and_creates_the_target(folder, tmp_path):
    sorter = sorter_on(folder, "b.jpg")
    sorter.move_out(sorter.current, tmp_path / "new" / "target")
    assert sorter.current.name == "c.jpg"
    assert (tmp_path / "new" / "target" / "b.jpg").exists()
    assert not (folder / "b.jpg").exists()


def test_moving_the_last_image_wraps_to_the_first(folder, tmp_path):
    sorter = sorter_on(folder, "d.jpg")
    sorter.move_out(sorter.current, tmp_path / "t")
    assert sorter.current.name == "a.jpg"


def test_moving_an_image_before_the_cursor_keeps_the_cursor_on_its_image(folder, tmp_path):
    sorter = sorter_on(folder, "c.jpg")
    sorter.move_out(folder / "a.jpg", tmp_path / "t")
    assert sorter.current.name == "c.jpg"


def test_moving_everything_leaves_no_current(folder, tmp_path):
    sorter = sorter_on(folder)
    while sorter.current:
        sorter.move_out(sorter.current, tmp_path / "t")
    assert sorter.paths == [] and sorter.index == 0


def test_undo_restores_old_positions_in_reverse_order(folder, tmp_path):
    sorter = sorter_on(folder, "b.jpg")
    sorter.move_out(sorter.current, tmp_path / "t")  # b
    sorter.move_out(sorter.current, tmp_path / "t")  # c
    sorter.step(-1)
    sorter.move_out(sorter.current, tmp_path / "t")  # a
    assert names(sorter) == ["d.jpg"]

    sorter.undo()
    assert names(sorter) == ["a.jpg", "d.jpg"] and sorter.current.name == "a.jpg"
    sorter.undo()
    assert names(sorter) == ["a.jpg", "c.jpg", "d.jpg"] and sorter.current.name == "c.jpg"
    sorter.undo()
    assert names(sorter) == ["a.jpg", "b.jpg", "c.jpg", "d.jpg"] and sorter.current.name == "b.jpg"
    assert sorter.undo() is None
    assert (folder / "b.jpg").read_text() == "b.jpg"


def test_undo_never_overwrites_a_new_file_with_the_old_name(folder, tmp_path):
    sorter = sorter_on(folder)
    sorter.move_out(sorter.current, tmp_path / "t")
    (folder / "a.jpg").write_text("new file")
    sorter.undo()
    assert (folder / "a.jpg").read_text() == "new file"
    assert (folder / "a (2).jpg").read_text() == "a.jpg"


def test_undo_of_a_vanished_file_reports_and_does_not_block_older_undos(folder, tmp_path):
    sorter = sorter_on(folder)
    sorter.move_out(sorter.current, tmp_path / "t")  # a
    moved = sorter.move_out(sorter.current, tmp_path / "t")  # b
    moved.destination.unlink()
    with pytest.raises(FileNotFoundError):
        sorter.undo()
    sorter.undo()
    assert (folder / "a.jpg").exists()


def test_undo_after_switching_folders_restores_the_file_without_polluting_the_list(folder, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "z.jpg").write_text("z")
    sorter = sorter_on(folder)
    sorter.move_out(sorter.current, tmp_path / "t")
    sorter.set_folder(other)
    sorter.undo()
    assert (folder / "a.jpg").exists()
    assert names(sorter) == ["z.jpg"]


def test_rescan_stays_on_the_current_image_when_files_appear(folder):
    sorter = sorter_on(folder, "c.jpg")
    (folder / "0 first.jpg").write_text("x")
    sorter.rescan()
    assert sorter.current.name == "c.jpg"
    assert sorter.index == 3


def test_rescan_survives_the_current_image_vanishing(folder):
    sorter = sorter_on(folder, "d.jpg")
    (folder / "d.jpg").unlink()
    sorter.rescan()
    assert sorter.current.name == "c.jpg"


def test_start_name_that_no_longer_exists_starts_at_the_beginning(folder):
    assert sorter_on(folder, "gone.jpg").index == 0


def _overlay_folder(tmp_path, names):
    folder = tmp_path / "overlays"
    folder.mkdir(exist_ok=True)
    for name in names:
        (folder / name).write_bytes(b"x")
    return folder


def test_overlays_lead_with_no_overlay_and_start_on_the_first_real_one(tmp_path):
    cursor = OverlayCursor()
    assert cursor.current is None
    cursor.load(str(_overlay_folder(tmp_path, ["a.png", "b.png"])))
    assert cursor.paths[0] is None
    assert cursor.current.name == "a.png"
    cursor.step(-1)
    assert cursor.current is None
    cursor.step(-1)
    assert cursor.current.name == "b.png"


def test_overlays_with_no_folder_are_only_no_overlay_and_never_scan_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "stray.png").write_bytes(b"x")
    monkeypatch.chdir(tmp_path)
    cursor = OverlayCursor()
    cursor.load("")
    assert cursor.paths == [None]
    cursor.step(1)
    assert cursor.current is None


def test_overlays_restart_where_they_were(tmp_path):
    folder = str(_overlay_folder(tmp_path, ["a.png", "b.png"]))
    cursor = OverlayCursor()
    cursor.load(folder, "b.png")
    assert cursor.current.name == "b.png"
    cursor.load(folder, NO_OVERLAY)
    assert cursor.current is None
    cursor.load(folder, "gone.png")
    assert cursor.current.name == "a.png"


def test_overlay_rescan_stays_put_and_copes_with_removal(tmp_path):
    folder = _overlay_folder(tmp_path, ["b.png", "c.png"])
    cursor = OverlayCursor()
    cursor.load(str(folder), "c.png")
    (folder / "a.png").write_bytes(b"x")
    cursor.rescan(str(folder))
    assert cursor.current.name == "c.png"
    (folder / "c.png").unlink()
    cursor.rescan(str(folder))
    assert cursor.current.name == "b.png"
