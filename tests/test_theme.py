"""Every pairing the theme actually draws clears its contrast threshold, measured to WCAG 2.1.

Text needs 4.5:1 on its own ground, and the edge of a control 3:1 against what it sits on.
A pair is only meaningful against the surface it is really drawn over, so each is named.
"""
from __future__ import annotations

import pytest

from gui import theme
from gui.panel import swatch_ink

TEXT_THRESHOLD = 4.5
EDGE_THRESHOLD = 3.0


def contrast_ratio(a: str, b: str) -> float:
    def luminance(colour: str) -> float:
        channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


TEXT_PAIRS = [
    ("TEXT", "PANEL"),  # labels, the key list, the footer
    ("TEXT", "FIELD"),  # typed text, combo values and popups
    ("TEXT", "RAISED"),  # buttons, tooltips
    ("TEXT", "RAISED_HOVER"),  # a hovered button
    ("TEXT", "FLESH_DEEP"),  # a selected button, popup row or text selection
    ("TEXT", "BAD_GROUND"),  # a folder that does not exist
    ("TEXT_DIM", "PANEL"),  # folder titles, the key meanings
    ("TEXT_DIM", "FIELD"),  # placeholder text
    ("RIND", "PANEL"),  # section headings
    ("FLESH", "PANEL"),  # the title and the footer link
    ("MESSAGE", "SURROUND"),  # the empty state
]
EDGE_PAIRS = [
    ("BORDER", "PANEL"),  # a field or button against the panel
    ("BORDER", "RAISED"),  # a button's edge against its own face
    ("BORDER", "FIELD"),  # a field's edge against its own face
    ("FLESH", "PANEL"),  # focus and hover
    ("FLESH", "FIELD"),
    ("FLESH", "RAISED_HOVER"),
    ("TEXT", "FLESH_DEEP"),  # the edge of a selected button
    ("BAD", "PANEL"),  # a folder that does not exist
    ("BAD", "BAD_GROUND"),
]


def test_the_measurement_agrees_with_known_values():
    assert contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert contrast_ratio("#5a8fd6", "#5a8fd6") == pytest.approx(1.0, abs=0.001)


@pytest.mark.parametrize("ink, ground", TEXT_PAIRS)
def test_text_clears_its_threshold(ink, ground):
    ratio = contrast_ratio(getattr(theme, ink), getattr(theme, ground))
    assert ratio >= TEXT_THRESHOLD, f"{ink} on {ground} is {ratio:.2f}:1"


@pytest.mark.parametrize("edge, ground", EDGE_PAIRS)
def test_control_edges_clear_their_threshold(edge, ground):
    ratio = contrast_ratio(getattr(theme, edge), getattr(theme, ground))
    assert ratio >= EDGE_THRESHOLD, f"{edge} on {ground} is {ratio:.2f}:1"


def test_the_surround_stays_neutral():
    """It sits against the image being judged, so no channel may stand out."""
    channels = [int(theme.SURROUND[i:i + 2], 16) for i in (1, 3, 5)]
    assert max(channels) - min(channels) <= 4
    assert max(channels) <= 0x18


@pytest.mark.parametrize(
    "fill", ["#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff", "#808080", "#767676", "#f58775"]
)
def test_the_fill_swatch_label_reads_on_any_colour(fill):
    assert contrast_ratio(swatch_ink(fill), fill) >= TEXT_THRESHOLD
