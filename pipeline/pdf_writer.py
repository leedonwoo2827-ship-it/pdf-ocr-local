"""Build a searchable PDF by overlaying an invisible text layer on the original."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF

from .coord import TextLine

logger = logging.getLogger(__name__)

FONT_NAME = "nanum"
FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "NanumGothic.ttf"


def write_searchable_pdf(
    src_pdf: str | Path,
    out_pdf: str | Path,
    page_lines: Dict[int, List[TextLine]],
) -> None:
    """Open `src_pdf`, overlay invisible text per page, save to `out_pdf`.

    `page_lines[i]` = list of TextLine for page index `i` (0-based).
    Uses render_mode=3 (invisible) so the original page imagery is unchanged
    but text becomes selectable / searchable.
    """
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"Korean font missing: {FONT_PATH}")

    doc = fitz.open(str(src_pdf))
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            lines = page_lines.get(page_idx) or []
            if not lines:
                continue
            # Register font on this page (idempotent within a page)
            page.insert_font(fontname=FONT_NAME, fontfile=str(FONT_PATH))

            page_rotation = page.rotation or 0

            for line in lines:
                text = line.text
                if not text.strip():
                    continue
                # fitz.Page uses top-left origin in user space matching PDF
                # rotation; insert_text expects the baseline point.
                point = fitz.Point(line.x_pt, line.baseline_y_pt)
                try:
                    page.insert_text(
                        point=point,
                        text=text,
                        fontname=FONT_NAME,
                        fontsize=line.fontsize,
                        render_mode=3,  # invisible text
                        rotate=0,        # bbox already in page coords
                    )
                except Exception as e:
                    logger.warning("insert_text failed on p%d: %s (text=%r)", page_idx + 1, e, text[:30])

        out_path = Path(out_pdf)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
