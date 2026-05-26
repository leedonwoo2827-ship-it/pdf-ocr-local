"""MinerU 3.x integration — layout-aware PDF → Markdown.

We shell out to the `mineru` CLI (installed via `pip install mineru`) instead
of using its Python API because the package's internal modules are reorganized
across releases. The CLI is the stable contract.

Output of `mineru -p file.pdf -o OUT -b pipeline -l korean` is:

    OUT/<pdf-stem>/auto/<pdf-stem>.md            <-- markdown
    OUT/<pdf-stem>/auto/<pdf-stem>_content_list.json   <-- per-element page_idx
    OUT/<pdf-stem>/auto/images/...
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _mineru_env() -> dict:
    env = os.environ.copy()
    env.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    env.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def mineru_available() -> bool:
    return shutil.which("mineru") is not None


def _split_pages_from_content_list(content_list_path: Path) -> Dict[int, str]:
    """Reconstruct per-page markdown using mineru's _content_list.json.

    Each element looks roughly like:
        {"type": "title|text|table|equation|image", "text": "...",
         "text_level": 1, "page_idx": 0}

    Returns {page_idx_0based: markdown_text}.
    """
    pages: Dict[int, List[str]] = {}
    try:
        items = json.loads(content_list_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        logger.warning("Could not parse %s: %s", content_list_path, e)
        return {}

    for it in items:
        if not isinstance(it, dict):
            continue
        page_idx = it.get("page_idx", 0)
        kind = it.get("type", "text")
        chunk = ""
        if kind == "title":
            level = max(1, min(6, int(it.get("text_level") or 1)))
            chunk = ("#" * level) + " " + (it.get("text") or "").strip()
        elif kind in ("text", "equation"):
            chunk = (it.get("text") or "").strip()
        elif kind == "table":
            chunk = (it.get("table_body") or it.get("text") or "").strip()
        elif kind == "image":
            cap = (it.get("img_caption") or [""])
            chunk = "\n".join(c for c in cap if c) or "[image]"
        else:
            chunk = (it.get("text") or "").strip()
        if chunk:
            pages.setdefault(int(page_idx), []).append(chunk)

    return {p: "\n\n".join(blocks) for p, blocks in pages.items()}


def _terminate_subprocess(proc: subprocess.Popen) -> None:
    """Kill mineru and any child workers it spawned.

    On Windows we use CTRL_BREAK_EVENT (which mineru's worker pool actually
    listens to) and then taskkill /T as a fallback. On POSIX we send SIGTERM
    to the whole process group.
    """
    try:
        if sys.platform == "win32":
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                pass
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True, timeout=10,
                )
            except Exception:
                pass
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    except Exception as e:
        logger.warning("Failed to terminate mineru: %s", e)


def run_mineru_markdown(
    src_pdf: str | Path,
    page_start: Optional[int] = None,
    page_end: Optional[int] = None,
    backend: str = "pipeline",
    lang: str = "korean",
    timeout: int = 1800,
) -> Tuple[Optional[str], Optional[Dict[int, str]], str]:
    """Run MinerU CLI on `src_pdf`, return (markdown_text, pages_by_idx, log).

    - markdown_text: combined Markdown, or None on failure.
    - pages_by_idx: {page_idx_0based: markdown}, or None if content_list
      could not be parsed.
    - log: short status string.

    stdout/stderr of mineru are inherited so the user sees its native
    progress bars in the cmd window. Timeouts kill the entire mineru
    process tree, not just the launcher.
    """
    src = Path(src_pdf).resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    if not mineru_available():
        return None, None, "mineru CLI not found (pip install mineru)"

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

        logger.info("MinerU starting: %s", " ".join(cmd))
        print(f"\n>>> MinerU starting (timeout={timeout}s, backend={backend}, lang={lang})", flush=True)

        creationflags = 0
        preexec_fn = None
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            preexec_fn = os.setsid  # type: ignore[assignment]

        try:
            proc = subprocess.Popen(
                cmd,
                env=_mineru_env(),
                stdout=None,
                stderr=None,
                creationflags=creationflags,
                preexec_fn=preexec_fn,
            )
        except FileNotFoundError as e:
            return None, None, f"mineru CLI not launchable: {e}"

        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"\n>>> MinerU timed out after {timeout}s, killing process tree ...", flush=True)
            _terminate_subprocess(proc)
            return None, None, f"mineru timed out after {timeout}s"

        if rc != 0:
            print(f">>> MinerU exit {rc}", flush=True)
            return None, None, f"mineru exit {rc}"

        md_candidates = list(Path(out_dir).rglob("*.md"))
        if not md_candidates:
            return None, None, "no .md produced by mineru"
        md_path = md_candidates[0]
        md_text = md_path.read_text(encoding="utf-8", errors="replace")

        # Try to load the matching _content_list.json for per-page split.
        content_list_path = md_path.with_name(md_path.stem + "_content_list.json")
        pages_by_idx: Optional[Dict[int, str]] = None
        if content_list_path.exists():
            pages_by_idx = _split_pages_from_content_list(content_list_path) or None

        print(f">>> MinerU done: {len(md_text)} chars" +
              (f", {len(pages_by_idx)} pages parsed" if pages_by_idx else ""),
              flush=True)
        return md_text, pages_by_idx, ""
