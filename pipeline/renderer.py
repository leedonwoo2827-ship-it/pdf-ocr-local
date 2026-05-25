"""PDF -> PIL Image rendering via pypdfium2."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np
import pypdfium2 as pdfium
from PIL import Image


@dataclass
class RenderedPage:
    index: int
    image: Image.Image
    width_px: int
    height_px: int
    width_pt: float
    height_pt: float
    dpi: int

    @property
    def numpy(self) -> np.ndarray:
        return np.asarray(self.image.convert("RGB"))


def render_pdf(pdf_path: str | Path, dpi: int = 200) -> Iterator[RenderedPage]:
    """Yield RenderedPage for each page of `pdf_path` at `dpi`.

    pypdfium2 uses scale where 1.0 == 72 DPI; so scale = dpi/72.
    """
    scale = dpi / 72.0
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        for i in range(len(doc)):
            page = doc[i]
            w_pt, h_pt = page.get_size()
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil()
            yield RenderedPage(
                index=i,
                image=pil,
                width_px=pil.width,
                height_px=pil.height,
                width_pt=float(w_pt),
                height_pt=float(h_pt),
                dpi=dpi,
            )
    finally:
        doc.close()


def page_count(pdf_path: str | Path) -> int:
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(doc)
    finally:
        doc.close()
