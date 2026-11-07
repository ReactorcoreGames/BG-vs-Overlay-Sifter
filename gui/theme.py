"""Watermelon chrome, with its colours taken from `assets/icon_og.jpg`. Only the panel side wears it.

`SURROUND` and `MESSAGE` stay neutral: they sit right against the image being judged, and a
tinted surround would change how it reads. `tests/test_theme.py` measures every pairing here.

Names one font family, which suppresses Qt's font substitution, and Segoe UI carries no
arrows, triangles or emoji: a decorative glyph on a control draws as nothing. Use words.
"""
from __future__ import annotations

SURROUND = "#0c0c0f"  # outside the canvas; neutral so it cannot tint the judgement
MESSAGE = "#a8a8b4"  # the empty-state text, which sits on the surround

PANEL = "#12271b"  # the rind's dark stripe
FIELD = "#0a120d"  # seed near-black, pulled toward the rind
RAISED = "#233b2c"  # the rind's mid stripe
RAISED_HOVER = "#2f4f3a"
BORDER = "#7fa257"  # the rind's bright stripe
HAIRLINE = "#5a7b43"
TEXT = "#f5f2cc"  # the cream of the inner rind
TEXT_DIM = "#c3d393"  # the rind's pale edge
RIND = "#a9cf6c"  # section headings
FLESH = "#f58775"  # the flesh's bright side: title, focus, hover, links
FLESH_DEEP = "#a8323e"  # the flesh's deep side: anything selected
BAD = "#ff9aa2"  # a folder that does not exist, as an edge
BAD_GROUND = "#4a1620"  # and as a ground, so it reads differently from focus

STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 10pt; color: {TEXT}; }}
QDialog, QMessageBox {{ background: {PANEL}; }}
QToolTip {{ background: {RAISED}; border: 1px solid {BORDER}; }}

#panel {{ background: {PANEL}; border-left: 1px solid {HAIRLINE}; }}
#panel QScrollArea, #panelBody {{ background: {PANEL}; border: none; }}
#title {{ color: {FLESH}; font-size: 13pt; font-weight: 600; }}
#section {{ color: {RIND}; font-weight: 600; }}
#dim {{ color: {TEXT_DIM}; }}

QLineEdit, QSpinBox, QComboBox {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 3px;
    padding: 3px 5px; min-height: 20px;
    selection-background-color: {FLESH_DEEP}; selection-color: {TEXT};
    placeholder-text-color: {TEXT_DIM};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {FLESH}; }}
QSpinBox:hover, QComboBox:hover {{ border-color: {FLESH}; }}
QLineEdit[bad="true"] {{ background: {BAD_GROUND}; border-color: {BAD}; }}
QComboBox QAbstractItemView {{
    background: {FIELD}; border: 1px solid {BORDER}; outline: none;
}}
QComboBox QAbstractItemView::item {{ padding: 3px 6px; border: none; }}
QComboBox QAbstractItemView::item:hover {{ background: {RAISED_HOVER}; color: {TEXT}; }}
QComboBox QAbstractItemView::item:selected {{ background: {FLESH_DEEP}; color: {TEXT}; }}

QPushButton {{
    background: {RAISED}; border: 1px solid {BORDER}; border-radius: 3px; padding: 3px 8px;
}}
QPushButton:hover {{ background: {RAISED_HOVER}; border-color: {FLESH}; }}
QPushButton:pressed {{ background: {FIELD}; border-color: {FLESH}; }}
QPushButton:checked {{ background: {FLESH_DEEP}; border-color: {TEXT}; }}

QScrollBar:vertical {{ background: {PANEL}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 24px; border-radius: 4px; }}
QScrollBar::handle:vertical:hover {{ background: {FLESH}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

#toast {{ background: {PANEL}; border: 1px solid {FLESH}; border-radius: 4px; padding: 6px 12px; }}
"""
