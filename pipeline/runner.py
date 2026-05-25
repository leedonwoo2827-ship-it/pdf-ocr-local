"""End-to-end pipeline: scanned PDF -> searchable PDF + Markdown."""
from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .coord import TextLine
from .ocr_engine import ocr_page
from .pdf_writer import write_searchable_pdf
from .renderer import render_pdf, page_count

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    quality: bool = False         # False=Fast (DPI 200), True=Quality (DPI 300)
    emit_markdown: bool = True
    use_vlm: bool = False
    vlm_threshold: float = 0.7    # if avg page rec_score below -> call VLM
    overwrite: bool = False

    @property
    def dpi(self) -> int:
        return 300 if self.quality else 200


def derive_out_paths(src: Path) -> tuple[Path, Path]:
    """before--<stem>.pdf -> after--<stem>.pdf  +  same-stem .md"""
    name = src.stem
    if name.startswith("before--"):
        out_stem = "after--" + name[len("before--"):]
    else:
        out_stem = name + "_ocr"
    out_pdf = src.parent / f"{out_stem}.pdf"
    out_md = src.parent / f"{out_stem}.md"
    return out_pdf, out_md


def _lines_to_text(lines: List[TextLine]) -> str:
    # Order by approximate reading order: row band, then x
    if not lines:
        return ""
    # group by Y bands of ~0.5 * median line height
    sorted_lines = sorted(lines, key=lambda L: (round(L.y_pt / max(L.height_pt, 1.0)), L.x_pt))
    out: List[str] = []
    prev_band = None
    row: List[str] = []
    for L in sorted_lines:
        band = round(L.y_pt / max(L.height_pt, 1.0))
        if prev_band is None or band == prev_band:
            row.append(L.text)
        else:
            out.append(" ".join(row))
            row = [L.text]
        prev_band = band
    if row:
        out.append(" ".join(row))
    return "\n".join(out)


def run_pipeline(
    src_pdf: str | Path,
    config: PipelineConfig,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> tuple[Path, Optional[Path]]:
    """Process one PDF. Returns (out_pdf_path, out_md_path_or_None)."""
    src = Path(src_pdf).resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    out_pdf, out_md = derive_out_paths(src)
    if out_pdf.exists() and not config.overwrite:
        logger.info("Skip (exists): %s", out_pdf.name)
        return out_pdf, (out_md if (config.emit_markdown and out_md.exists()) else None)

    total = page_count(src)
    if progress_cb:
        progress_cb(0, total, f"Rendering & OCR @ DPI {config.dpi}")

    page_lines: Dict[int, List[TextLine]] = {}
    page_texts: Dict[int, str] = {}
    low_conf_pages: List[int] = []
    t0 = time.time()

    for rp in render_pdf(src, dpi=config.dpi):
        res = ocr_page(rp, quality=config.quality)
        page_lines[rp.index] = res.lines
        page_texts[rp.index] = _lines_to_text(res.lines)
        if res.avg_score < config.vlm_threshold:
            low_conf_pages.append(rp.index)
        if progress_cb:
            progress_cb(rp.index + 1, total, f"OCR p{rp.index + 1}/{total} (score={res.avg_score:.2f})")

    # Optional VLM enrichment for low-confidence pages
    vlm_md: Dict[int, str] = {}
    if config.use_vlm and low_conf_pages:
        from .vlm_engine import ollama_available, vlm_extract_markdown
        if not ollama_available():
            logger.warning("VLM requested but Ollama not reachable; skipping enrichment")
        else:
            # re-render at moderate DPI for VLM (already have images from first pass?
            # we discarded them — re-render only the low-conf pages)
            wanted = set(low_conf_pages)
            for rp in render_pdf(src, dpi=config.dpi):
                if rp.index not in wanted:
                    continue
                if progress_cb:
                    progress_cb(rp.index + 1, total, f"VLM enrich p{rp.index + 1}")
                md = vlm_extract_markdown(rp.image)
                if md:
                    vlm_md[rp.index] = md

    # Write searchable PDF (use PaddleOCR bboxes; VLM does not replace text-layer)
    write_searchable_pdf(src, out_pdf, page_lines)

    # Emit Markdown
    md_path: Optional[Path] = None
    if config.emit_markdown:
        md_parts: List[str] = []
        for i in range(total):
            md_parts.append(f"\n\n<!-- page {i + 1} -->\n")
            if i in vlm_md:
                md_parts.append(vlm_md[i])
            else:
                md_parts.append(page_texts.get(i, ""))
        out_md.write_text("".join(md_parts).strip() + "\n", encoding="utf-8")
        md_path = out_md

    dt = time.time() - t0
    if progress_cb:
        progress_cb(total, total, f"Done in {dt:.1f}s -> {out_pdf.name}")
    logger.info("Done: %s (pages=%d, %.1fs)", out_pdf.name, total, dt)
    return out_pdf, md_path


def run_folder(
    folder: str | Path,
    config: PipelineConfig,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> List[tuple[Path, Optional[Path]]]:
    folder = Path(folder).resolve()
    pdfs = sorted(folder.glob("before--*.pdf"))
    results: List[tuple[Path, Optional[Path]]] = []
    for i, p in enumerate(pdfs):
        if progress_cb:
            progress_cb(i, len(pdfs), f"[{i+1}/{len(pdfs)}] {p.name}")
        try:
            results.append(run_pipeline(p, config, progress_cb=None))
        except Exception as e:
            logger.exception("Failed: %s", p.name)
            results.append((p, None))
    if progress_cb:
        progress_cb(len(pdfs), len(pdfs), "Batch complete")
    return results


def _cli():
    ap = argparse.ArgumentParser(description="Local OCR: scan PDF -> searchable PDF + .md")
    ap.add_argument("path", help="PDF file or folder containing before--*.pdf")
    ap.add_argument("--quality", action="store_true", help="Quality mode (DPI 300, slower)")
    ap.add_argument("--no-md", action="store_true", help="Skip Markdown output")
    ap.add_argument("--vlm", action="store_true", help="Use Ollama VLM for low-confidence pages")
    ap.add_argument("--threshold", type=float, default=0.7, help="VLM trigger threshold")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = PipelineConfig(
        quality=args.quality,
        emit_markdown=not args.no_md,
        use_vlm=args.vlm,
        vlm_threshold=args.threshold,
        overwrite=args.overwrite,
    )

    def cb(done, total, msg):
        print(f"  [{done}/{total}] {msg}")

    p = Path(args.path)
    if p.is_dir():
        run_folder(p, cfg, progress_cb=cb)
    else:
        run_pipeline(p, cfg, progress_cb=cb)


if __name__ == "__main__":
    _cli()
