"""Fill in the `keywords:` slot in each Q*.md's YAML front-matter
using a local LLM (Ollama qwen2.5:7b).

Idempotent: skips files whose keywords array is already non-empty.

Usage:
    python scripts/add_keywords.py assets/after--<stem>_problems/
    python scripts/add_keywords.py <folder> --model qwen2.5:7b --max 5

Requires Ollama running locally:
    ollama serve         # if not already running
    ollama pull qwen2.5:7b
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

PROMPT_TEMPLATE = (
    "다음 한국어 SQLD 시험 문제에서 검색용 키워드 5~8개를 뽑아.\n"
    "오직 JSON 배열만 출력하고 다른 설명·인사·접미사·코드펜스는 절대 출력하지 마.\n"
    "키워드는 명사형 한 단어 또는 짧은 구. 영어 SQL 키워드는 영문 그대로(예: JOIN, GROUP BY).\n"
    "출력 예: [\"분산 데이터베이스\", \"Query\", \"가용성\", \"보안통제\"]\n\n"
    "문제 본문:\n"
    "{body}\n\n"
    "JSON 배열:"
)


def extract_keywords(body: str, model: str, timeout: int = 120) -> List[str]:
    prompt = PROMPT_TEMPLATE.format(body=body[:2500])
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_ctx": 4096},
            },
            timeout=timeout,
        )
        r.raise_for_status()
        resp = (r.json().get("response") or "").strip()
    except Exception as e:
        print(f"  WARN: ollama call failed: {e}")
        return []

    # accept either a JSON array or a comma list
    m = re.search(r"\[.*?\]", resp, re.DOTALL)
    if m:
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                return [str(k).strip().strip('"\'') for k in arr if str(k).strip()][:10]
        except Exception:
            pass

    # last-ditch: split on commas
    cleaned = resp.replace("[", "").replace("]", "").replace("\"", "").replace("'", "")
    parts = [p.strip() for p in re.split(r"[,\n]", cleaned) if p.strip()]
    return parts[:10]


_FRONT_RE = re.compile(r"^---\n(.+?)\n---\n", re.DOTALL)


def patch_front_matter(md_path: Path, model: str) -> str:
    text = md_path.read_text(encoding="utf-8")
    m = _FRONT_RE.match(text)
    if not m:
        return "no-frontmatter"
    fm = m.group(1)
    body = text[m.end():]

    # skip if keywords already populated
    kw_match = re.search(r"^keywords:\s*(.+)$", fm, re.MULTILINE)
    if kw_match and kw_match.group(1).strip() not in ("[]", "null", ""):
        return "skip-already-set"

    kws = extract_keywords(body, model=model)
    if not kws:
        return "skip-empty-llm"

    kw_str = "[" + ", ".join(json.dumps(k, ensure_ascii=False) for k in kws) + "]"
    if kw_match:
        new_fm = _re_replace_kw(fm, kw_str)
    else:
        new_fm = fm.rstrip() + f"\nkeywords: {kw_str}"

    md_path.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
    return f"ok: {kws}"


def _re_replace_kw(fm: str, kw_str: str) -> str:
    return re.sub(r"^keywords:\s*.+$", f"keywords: {kw_str}", fm, flags=re.MULTILINE)


def main():
    ap = argparse.ArgumentParser(description="Fill keywords in Q*.md front-matter via Ollama.")
    ap.add_argument("folder", help="Folder with Q*.md files (e.g. assets/after--<stem>_problems/)")
    ap.add_argument("--model", default="qwen2.5:7b", help="Ollama model tag (default: qwen2.5:7b)")
    ap.add_argument("--max", type=int, default=None,
                    help="Cap how many files to process (default: all). Useful for a smoke test.")
    args = ap.parse_args()

    # Reachability check
    try:
        ping = requests.get("http://localhost:11434/api/tags", timeout=3)
        ping.raise_for_status()
        tags = [m["name"] for m in ping.json().get("models", [])]
        if args.model not in tags and args.model.split(":")[0] not in [t.split(":")[0] for t in tags]:
            print(f"[WARN] model '{args.model}' not in `ollama list`. Available: {tags}")
    except Exception as e:
        raise SystemExit(f"[ERROR] cannot reach Ollama: {e}\n  start it with `ollama serve` and `ollama pull {args.model}`")

    folder = Path(args.folder).resolve()
    files = sorted(folder.glob("Q*.md"))
    if args.max:
        files = files[: args.max]
    print(f"Processing {len(files)} file(s) under {folder}")
    for i, f in enumerate(files, 1):
        status = patch_front_matter(f, args.model)
        print(f"[{i}/{len(files)}] {f.name}: {status}")
    print("Done.")


if __name__ == "__main__":
    main()
