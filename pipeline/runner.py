"""End-to-end pipeline: scanned PDF -> searchable PDF + Markdown."""
from __future__ import annotations

import argparse
import logging
import re
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
    markdown_engine: str = "paddle"   # "paddle" | "mineru"
    mineru_backend: str = "pipeline"  # "pipeline" | "vlm-auto-engine" | "hybrid-auto-engine"
    use_vlm: bool = False             # per-page VLM enrichment of paddle output
    vlm_threshold: float = 0.7
    overwrite: bool = False
    split_pages: bool = True          # also emit assets/after--<stem>_pages/page-NNN.md

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


def _pages_dir_for(out_pdf: Path) -> Path:
    """assets/after--xxx.pdf  ->  assets/after--xxx_pages/"""
    return out_pdf.parent / f"{out_pdf.stem}_pages"


_PAGE_MARKER_RE = re.compile(r"<!--\s*page\s+(\d+)\s*-->", re.IGNORECASE)


def split_paddle_md_by_marker(md_text: str) -> Dict[int, str]:
    """Split paddle markdown by <!-- page N --> markers.

    Returns {page_number_1based: chunk_text}. Pages with empty chunks are
    still returned (as "") so downstream code can write N files.
    """
    pages: Dict[int, str] = {}
    matches = list(_PAGE_MARKER_RE.finditer(md_text))
    for i, m in enumerate(matches):
        pno = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        pages[pno] = md_text[start:end].strip()
    return pages


def write_page_files(pages: Dict[int, str], pages_dir: Path) -> List[Path]:
    """Write page-NNN.md files; returns list of created paths."""
    pages_dir.mkdir(parents=True, exist_ok=True)
    # Clean any stale page files from a previous run so a shorter PDF
    # doesn't leave orphans behind.
    for old in pages_dir.glob("page-*.md"):
        try:
            old.unlink()
        except Exception:
            pass
    written: List[Path] = []
    for pno in sorted(pages.keys()):
        p = pages_dir / f"page-{pno:03d}.md"
        p.write_text((pages[pno] or "").strip() + "\n", encoding="utf-8")
        written.append(p)
    return written


def _lines_to_text(lines: List[TextLine]) -> str:
    if not lines:
        return ""
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
        if progress_cb:
            progress_cb(1, 1, f"Skipped: {out_pdf.name} already exists (enable overwrite to rerun)")
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
            wanted = set(low_conf_pages)
            for rp in render_pdf(src, dpi=config.dpi):
                if rp.index not in wanted:
                    continue
                if progress_cb:
                    progress_cb(rp.index + 1, total, f"VLM enrich p{rp.index + 1}")
                md = vlm_extract_markdown(rp.image)
                if md:
                    vlm_md[rp.index] = md

    # Searchable PDF
    write_searchable_pdf(src, out_pdf, page_lines)

    # Markdown — engine is selectable
    md_path: Optional[Path] = None
    if config.emit_markdown:
        engine = (config.markdown_engine or "paddle").lower()
        md_text: str = ""
        # page_md_by_1based: {1..N: markdown} for the per-page split
        page_md_by_1based: Dict[int, str] = {}

        if engine == "mineru":
            # Mineru runtime scales with page count on this hardware (RTX 4070
            # 8GB): roughly ~30s/page including table OCR. Use a dynamic
            # timeout with a comfortable margin so 80-100 page books finish.
            mineru_timeout = max(1800, total * 60)
            if progress_cb:
                progress_cb(total, total, f"MinerU layout-aware Markdown (timeout {mineru_timeout//60}min) ...")
            from .mineru_engine import run_mineru_markdown, mineru_available
            if not mineru_available():
                logger.warning("MinerU CLI not found; falling back to paddle markdown")
                engine = "paddle"
            else:
                md_text_m, pages_by_idx, mlog = run_mineru_markdown(
                    src, backend=config.mineru_backend, timeout=mineru_timeout,
                )
                if md_text_m is None:
                    logger.warning("MinerU failed (%s); falling back to paddle", mlog)
                    engine = "paddle"
                else:
                    md_text = md_text_m
                    if pages_by_idx:
                        page_md_by_1based = {i + 1: t for i, t in pages_by_idx.items()}

        if engine == "paddle" or not md_text:
            md_parts: List[str] = []
            for i in range(total):
                md_parts.append(f"\n\n<!-- page {i + 1} -->\n")
                chunk = vlm_md[i] if i in vlm_md else page_texts.get(i, "")
                md_parts.append(chunk)
                page_md_by_1based[i + 1] = chunk
            md_text = "".join(md_parts)

        out_md.write_text(md_text.strip() + "\n", encoding="utf-8")
        md_path = out_md

        # Per-page split for RAG
        if config.split_pages and page_md_by_1based:
            pages_dir = _pages_dir_for(out_pdf)
            written = write_page_files(page_md_by_1based, pages_dir)
            # Also bundle as a single .zip so the Gradio UI can offer it as a
            # one-click download (the UI doesn't natively expose 84 files).
            zip_path = pages_dir.with_suffix(".zip")
            try:
                import zipfile
                with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for pf in written:
                        zf.write(pf, arcname=pf.name)
            except Exception as e:
                logger.warning("Could not build %s: %s", zip_path, e)
            if progress_cb:
                progress_cb(total, total,
                            f"Split into {len(written)} per-page .md -> {pages_dir.name}/  (also: {zip_path.name})")
            logger.info("Per-page split: %d files in %s (+ %s)", len(written), pages_dir, zip_path.name)

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
    ap.add_argument("--md-engine", choices=["paddle", "mineru"], default="paddle",
                    help="Markdown engine: paddle (raw OCR text) | mineru (layout-aware)")
    ap.add_argument("--mineru-backend", choices=["pipeline", "vlm-auto-engine", "hybrid-auto-engine"],
                    default="pipeline", help="MinerU backend if --md-engine=mineru")
    ap.add_argument("--vlm", action="store_true", help="Use Ollama VLM for low-confidence pages (paddle md only)")
    ap.add_argument("--threshold", type=float, default=0.7, help="VLM trigger threshold")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--no-split-pages", action="store_true",
                    help="Skip per-page .md split (assets/after--<stem>_pages/page-NNN.md)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = PipelineConfig(
        quality=args.quality,
        emit_markdown=not args.no_md,
        markdown_engine=args.md_engine,
        mineru_backend=args.mineru_backend,
        use_vlm=args.vlm,
        vlm_threshold=args.threshold,
        overwrite=args.overwrite,
        split_pages=not args.no_split_pages,
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
