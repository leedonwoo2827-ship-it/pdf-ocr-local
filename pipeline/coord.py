"""Pixel-space OCR polygons -> PDF point coordinates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class TextLine:
    text: str
    score: float
    # PDF coordinates (points). Origin: bottom-left for PyMuPDF page space below
    # but we return values appropriate for fitz.Page.insert_text where the y
    # passed is the BASELINE position. fitz uses top-left origin internally for
    # insert_text — see pdf_writer.py for how this is used.
    x_pt: float
    y_pt: float           # top of text box in fitz coordinates (top-left origin)
    width_pt: float
    height_pt: float

    @property
    def fontsize(self) -> float:
        # fontsize roughly equals the text box height in points; clamp to sane range
        return max(4.0, min(72.0, self.height_pt * 0.9))

    @property
    def baseline_y_pt(self) -> float:
        # Place baseline near the bottom of the bbox, with small leading
        return self.y_pt + self.height_pt * 0.85


def polygon_to_line(
    polygon: Sequence[Sequence[float]],
    text: str,
    score: float,
    image_w_px: int,
    image_h_px: int,
    page_w_pt: float,
    page_h_pt: float,
) -> TextLine:
    """Convert a 4-point polygon (image px) into a TextLine in PDF points.

    PyMuPDF's page coordinate space for insert_text uses the *current* page
    rectangle. By default that is top-left origin (in PDF user units = points).
    """
    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    sx = page_w_pt / image_w_px
    sy = page_h_pt / image_h_px

    x_pt = x_min * sx
    y_pt = y_min * sy
    w_pt = (x_max - x_min) * sx
    h_pt = (y_max - y_min) * sy

    return TextLine(
        text=text,
        score=score,
        x_pt=x_pt,
        y_pt=y_pt,
        width_pt=w_pt,
        height_pt=h_pt,
    )
