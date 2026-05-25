"""Optional VLM track via local Ollama (qwen2.5vl:7b).

Used to (a) re-extract text for low-confidence pages, (b) produce richer Markdown
for the .md output. Returns text only — no bounding boxes — so this output
feeds the Markdown track and per-line text replacement (matched against
PaddleOCR's bbox order), not invisible-PDF layout directly.
"""
from __future__ import annotations

import base64
import io
import logging
from typing import Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5vl:7b"

PROMPT_MARKDOWN = (
    "이미지에서 모든 텍스트를 정확히 추출해 Markdown으로 변환해. "
    "표는 GitHub-flavored Markdown 표 문법을 사용하고, 제목/소제목은 적절한 # 레벨을 부여해. "
    "원본 문서의 줄바꿈과 단락 구분을 최대한 보존하되, 의미 없는 줄바꿈은 합쳐. "
    "OCR 노이즈성 글자만 있는 줄은 버려. 부연 설명/사과/요약 없이 결과 Markdown만 출력해."
)


def ollama_available() -> bool:
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.ok
    except Exception:
        return False


def image_to_b64(img: Image.Image, max_side: int = 1600) -> str:
    """Encode PIL image as base64 PNG; downscale to <= max_side on the long edge
    to keep VLM latency reasonable."""
    w, h = img.size
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def vlm_extract_markdown(img: Image.Image, timeout: int = 180) -> Optional[str]:
    """Run qwen2.5vl on `img`. Returns Markdown text, or None on failure."""
    try:
        payload = {
            "model": MODEL,
            "prompt": PROMPT_MARKDOWN,
            "images": [image_to_b64(img)],
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 8192},
        }
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        return (r.json().get("response") or "").strip()
    except Exception as e:
        logger.warning("VLM call failed: %s", e)
        return None
