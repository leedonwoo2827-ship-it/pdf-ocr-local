"""Split a mineru markdown into per-problem .md files for RAG.

Heuristic: every line starting with `## <number>` opens a new problem.
Everything before the first such line goes to Q000_intro.md.
Non-numbered ## headings (e.g. "## 데이터모델링관점") are kept inside the
preceding problem because they're usually section captions that belong
to that problem's body (a table title, a 해설 marker, etc.).

Output filename = Q<seq3>_orig<num2>.md, e.g. Q003_orig02.md
  - seq3 is the order the problem appeared in the source markdown
  - num2 is the original "##" number from the textbook

So the user gets files in reading order (Q001, Q002, ...) but each
filename still carries the textbook's own problem number for easy
cross-checking against the original PDF.

Usage:
    python scripts/split_by_problem.py assets/after--S36C-1i26051408350.md
    python scripts/split_by_problem.py path/to/foo.md -o some/where
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Optional, Tuple

PROBLEM_HEAD = re.compile(r"^##\s+(\d+)(?:\b|[^\d])")


def split_chunks(md_text: str) -> Tuple[str, List[Tuple[int, str]]]:
    """Return (intro_text, [(orig_num, body), ...]) preserving source order."""
    lines = md_text.splitlines()
    intro: List[str] = []
    chunks: List[Tuple[int, List[str]]] = []
    cur_num: Optional[int] = None
    cur_lines: List[str] = []

    for line in lines:
        m = PROBLEM_HEAD.match(line)
        if m:
            if cur_num is None:
                intro = cur_lines
            else:
                chunks.append((cur_num, cur_lines))
            cur_num = int(m.group(1))
            cur_lines = [line]
        else:
            cur_lines.append(line)

    if cur_num is None:
        intro = cur_lines
    elif cur_lines:
        chunks.append((cur_num, cur_lines))

    intro_text = "\n".join(intro).strip()
    bodies = [(n, "\n".join(ls).strip()) for n, ls in chunks]
    return intro_text, bodies


def write_problems(intro_text: str, bodies: List[Tuple[int, str]], out_dir: Path) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Wipe old Q*.md so a re-run does not leave orphans from a longer source
    for old in out_dir.glob("Q*.md"):
        try:
            old.unlink()
        except Exception:
            pass

    written: List[Path] = []
    if intro_text:
        p = out_dir / "Q000_intro.md"
        p.write_text(intro_text + "\n", encoding="utf-8")
        written.append(p)

    for seq, (orig_num, body) in enumerate(bodies, 1):
        name = f"Q{seq:03d}_orig{orig_num:02d}.md"
        p = out_dir / name
        # Append an empty answer slot so the user can fill it in by hand
        # after cross-checking the original PDF. Automated answer-key
        # mapping is intentionally NOT done here.
        if "## 정답" not in body:
            body = body.rstrip() + "\n\n## 정답\n\n_(여기에 정답 — 원본 정답표 보고 손으로 채우세요)_\n"
        p.write_text(body + "\n", encoding="utf-8")
        written.append(p)

    return written


def main():
    ap = argparse.ArgumentParser(description="Split a mineru/paddle markdown into per-problem .md files.")
    ap.add_argument("src_md", help="Path to the combined .md (e.g. assets/after--<stem>.md)")
    ap.add_argument("-o", "--out-dir", default=None,
                    help="Output folder (default: <src>_problems/ next to the source)")
    args = ap.parse_args()

    src = Path(args.src_md).resolve()
    if not src.exists():
        raise SystemExit(f"not found: {src}")

    out_dir = Path(args.out_dir).resolve() if args.out_dir else src.with_name(src.stem + "_problems")
    text = src.read_text(encoding="utf-8", errors="replace")
    intro_text, bodies = split_chunks(text)
    written = write_problems(intro_text, bodies, out_dir)

    print(f"Source        : {src}")
    print(f"Output folder : {out_dir}")
    print(f"Intro chunk   : {'yes' if intro_text else 'no'}")
    print(f"Problems      : {len(bodies)}  (first 10 orig numbers: {[n for n,_ in bodies[:10]]})")
    print(f"Files written : {len(written)}")
    if bodies:
        # Quick sanity: detect duplicate orig numbers, which usually means
        # the textbook restarted numbering for a new chapter/round.
        from collections import Counter
        c = Counter(n for n, _ in bodies)
        dups = {n: k for n, k in c.items() if k > 1}
        if dups:
            print(f"Note          : duplicate orig numbers seen -> {dict(list(dups.items())[:10])}")
            print("                (likely multiple rounds; filenames Qseq are still unique)")


if __name__ == "__main__":
    main()
