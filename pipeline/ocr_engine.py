"""PaddleOCR wrapper (Fast / Quality modes)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

import numpy as np

from .coord import TextLine, polygon_to_line
from .renderer import RenderedPage

logger = logging.getLogger(__name__)

_OCR_SINGLETON = {}  # mode -> PaddleOCR


@dataclass
class PageOCR:
    page_index: int
    lines: List[TextLine]
    avg_score: float


def _build_ocr(quality: bool):
    """Lazy-init a PaddleOCR pipeline. Reuse one per mode to avoid model reload."""
    from paddleocr import PaddleOCR  # local import: heavy
    key = "quality" if quality else "fast"
    if key in _OCR_SINGLETON:
        return _OCR_SINGLETON[key]

    kwargs = dict(
        lang="korean",
        ocr_version="PP-OCRv5",
        use_textline_orientation=True,
        device="gpu:0",
    )
    if quality:
        kwargs["use_doc_unwarping"] = True
        kwargs["use_doc_orientation_classify"] = True
    else:
        kwargs["use_doc_unwarping"] = False
        kwargs["use_doc_orientation_classify"] = False

    logger.info("Loading PaddleOCR (%s mode)...", key)
    ocr = PaddleOCR(**kwargs)
    _OCR_SINGLETON[key] = ocr
    return ocr


def ocr_page(page: RenderedPage, quality: bool = False) -> PageOCR:
    """Run OCR on one rendered page; return TextLines in PDF point coords."""
    ocr = _build_ocr(quality)
    img = page.numpy  # HxWx3 RGB ndarray
    raw = ocr.predict(img)  # list of dict (1 item per image)
    lines: List[TextLine] = []
    scores: List[float] = []
    for entry in raw:
        polys = entry.get("rec_polys") or entry.get("dt_polys") or []
        texts = entry.get("rec_texts") or []
        recs = entry.get("rec_scores") or [1.0] * len(texts)
        for poly, txt, sc in zip(polys, texts, recs):
            if not txt:
                continue
            poly_list = np.asarray(poly).reshape(-1, 2).tolist()
            line = polygon_to_line(
                polygon=poly_list,
                text=str(txt),
                score=float(sc),
                image_w_px=page.width_px,
                image_h_px=page.height_px,
                page_w_pt=page.width_pt,
                page_h_pt=page.height_pt,
            )
            lines.append(line)
            scores.append(float(sc))
    avg = float(sum(scores) / len(scores)) if scores else 0.0
    return PageOCR(page_index=page.index, lines=lines, avg_score=avg)
