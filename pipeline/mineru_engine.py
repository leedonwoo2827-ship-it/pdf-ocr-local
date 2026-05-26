"""MinerU 3.x integration — layout-aware PDF → Markdown.

We shell out to the `mineru` CLI (installed via `pip install mineru`) instead
of using its Python API because the package's internal modules are reorganized
across releases. The CLI is the stable contract.

Output of `mineru -p file.pdf -o OUT -b pipeline -l korean` is:

    OUT/<pdf-stem>/auto/<pdf-stem>.md            <-- our target
    OUT/<pdf-stem>/auto/<pdf-stem>_content_list.json
    OUT/<pdf-stem>/auto/images/...

We copy/rename the .md into the original PDF's parent folder following the
project's `after--<stem>.md` convention and discard the rest by default.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _mineru_env() -> dict:
    """Environment for the MinerU subprocess.

    - HF_HUB_DISABLE_SYMLINKS_WARNING: silence cosmetic warnings on Windows.
    - HF_HUB_ENABLE_HF_TRANSFER=0: stable downloader.
    Caller may also export MINERU_MODEL_SOURCE=modelscope to bypass HF entirely
    if HF Hub symlink errors persist (Windows non-admin).
    """
    env = os.environ.copy()
    env.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    env.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def mineru_available() -> bool:
    return shutil.which("mineru") is not None


def run_mineru_markdown(
    src_pdf: str | Path,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    backend: str = "pipeline",
    lang: str = "korean",
    timeout: int = 1800,
) -> Tuple[Optional[str], str]:
    """Run MinerU CLI on `src_pdf`, return (markdown_text, stderr_log).

    `markdown_text` is None on failure.
    `backend`: 'pipeline' (fast, layout+OCR), 'vlm-auto-engine' (slower, VLM-based),
               'hybrid-auto-engine' (highest quality, heavier).
    """
    src = Path(src_pdf).resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    if not mineru_available():
        return None, "mineru CLI not found (pip install mineru)"

    with tempfile.TemporaryDirectory(prefix="mineru_out_") as out_dir:
        cmd = [
            "mineru",
            "-p", str(src),
            "-o", out_dir,
            "-m", "auto",
            "-b", backend,
            "-l", lang,
        ]
        if page_start is not None:
            cmd += ["-s", str(page_start)]
        if page_end is not None:
            cmd += ["-e", str(page_end)]

        logger.info("MinerU: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=_mineru_env(),
            )
        except subprocess.TimeoutExpired:
            return None, f"mineru timed out after {timeout}s"

        if proc.returncode != 0:
            return None, f"mineru exit {proc.returncode}\nSTDERR:\n{proc.stderr[-2000:]}"

        # MinerU writes to: <out>/<stem>/auto/<stem>.md
        md_candidates = list(Path(out_dir).rglob("*.md"))
        if not md_candidates:
            return None, f"no .md produced by mineru\nSTDOUT:\n{proc.stdout[-1000:]}"
        md_text = md_candidates[0].read_text(encoding="utf-8", errors="replace")
        return md_text, proc.stderr[-500:] if proc.stderr else ""
