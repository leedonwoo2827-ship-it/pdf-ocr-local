"""Split a mineru/paddle markdown into per-problem .md files for RAG.

Heuristic: every line starting with `## <number>` opens a new problem.

Output filename = Q<seq3>_orig<num2>.md, e.g. Q003_orig02.md
  - seq3 is the order the problem appeared in the source markdown
  - num2 is the original "##" number from the textbook

Each output file gets:
  1. YAML front-matter (round / subject / subject_no / problem_no /
     answer / keywords) with the values we can determine automatically;
     unknowns stay null and the user fills them in.
  2. Body rewritten in the user's heading convention:
        #   <과목번호>과목 <과목명>
        ##  <문제번호> <발문>
        ### <보기 ①/②/③/④>
        ####정답  +  empty answer slot
  3. Original mineru content (tables, 해설 text, etc.) preserved
     between the heading transforms.

Usage:
    python scripts/split_by_problem.py assets/after--<stem>.md
    python scripts/split_by_problem.py path/to/foo.md -o some/where --plain
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Optional, Tuple

# ------------------------------------------------------------------------
# Domain knowledge: SQLD subject (과목) mapping.
# Add more entries if the textbook uses other chapter headings.
# Match is normalized: spaces are stripped before comparison so OCR
# whitespace differences (e.g. "SQL 기본 및 활용" vs "SQL기본및활용") still hit.
# ------------------------------------------------------------------------
SUBJECT_MAP: List[Tuple[str, int, str]] = [
    ("데이터 모델링의 이해", 1, "데이터 모델링의 이해"),
    ("데이터 모델과 SQL",   1, "데이터 모델과 SQL"),
    ("데이터 모델과 성능",  1, "데이터 모델과 성능"),
    ("데이터모델링관점",    1, "데이터 모델링의 이해"),  # alias seen in mineru
    ("SQL 기본 및 활용",    2, "SQL 기본 및 활용"),
    ("SQL 기본",            2, "SQL 기본"),
    ("SQL 활용",            2, "SQL 활용"),
    ("SQL 최적화 기본 원리", 2, "SQL 최적화 기본 원리"),
]

PROBLEM_HEAD = re.compile(r"^##\s+(\d+)(?:\b|[^\d])")
CHAPTER_HEAD = re.compile(r"^##\s+(.+?)\s*$")
CHOICE_LINE = re.compile(r"^\s*([①②③④⑤])\s*(.*)$")


def detect_subject(chapter_text: str) -> Tuple[Optional[int], Optional[str]]:
    norm = chapter_text.replace(" ", "")
    for key, sno, sname in SUBJECT_MAP:
        if key.replace(" ", "") in norm:
            return sno, sname
    return None, None


def split_chunks(md_text: str) -> Tuple[str, List[Tuple[int, str, Optional[Tuple[int, str]]]]]:
    """Return (intro_text, [(orig_num, body, (subject_no, subject_name)|None), ...])

    Tracks the most recently matched SUBJECT_MAP chapter so each problem
    inherits the correct subject without us having to second-guess later.
    """
    lines = md_text.splitlines()
    intro_lines: List[str] = []
    chunks: List[Tuple[int, List[str], Optional[Tuple[int, str]]]] = []
    current_subject: Optional[Tuple[int, str]] = None
    cur_num: Optional[int] = None
    cur_lines: List[str] = []

    for line in lines:
        m_p = PROBLEM_HEAD.match(line)
        m_c = CHAPTER_HEAD.match(line) if not m_p else None

        if m_p:
            if cur_num is None:
                intro_lines = cur_lines
            else:
                chunks.append((cur_num, cur_lines, current_subject))
            cur_num = int(m_p.group(1))
            cur_lines = [line]
            continue

        if m_c:
            sno, sname = detect_subject(m_c.group(1))
            if sno is not None:
                current_subject = (sno, sname)
            # keep the chapter line in whichever bucket we're filling so
            # info isn't lost
            cur_lines.append(line)
            continue

        cur_lines.append(line)

    if cur_num is None:
        intro_lines = cur_lines
    elif cur_lines:
        chunks.append((cur_num, cur_lines, current_subject))

    intro = "\n".join(intro_lines).strip()
    bodies = [(n, "\n".join(ls).strip(), subj) for n, ls, subj in chunks]
    return intro, bodies


def rewrite_body_user_style(
    body: str,
    orig_num: int,
    subject: Optional[Tuple[int, str]],
) -> str:
    """Apply the user's heading convention to one problem body."""
    out_lines: List[str] = []
    saw_problem_head = False
    for line in body.splitlines():
        stripped = line.strip()
        # The first ## NN line: keep as h2 (발문). Already h2 in source.
        m_p = PROBLEM_HEAD.match(line)
        if m_p and not saw_problem_head:
            out_lines.append(line)
            saw_problem_head = True
            continue
        # Chapter headings inside a problem (e.g. "## 데이터모델링관점") are
        # demoted - they're usually table captions, not real chapters.
        m_c = CHAPTER_HEAD.match(line) if not m_p else None
        if m_c and saw_problem_head:
            # if it's a known subject, drop (we'll already have it as the #
            # heading at the top); otherwise demote to plain bold so the
            # text isn't lost.
            sno, _ = detect_subject(m_c.group(1))
            if sno is not None:
                continue
            out_lines.append(f"**{m_c.group(1).strip()}**")
            continue
        # Choice lines: ①②③④ -> ### ① ...
        m_ch = CHOICE_LINE.match(stripped)
        if m_ch:
            mark = m_ch.group(1)
            rest = m_ch.group(2).strip()
            out_lines.append(f"### {mark} {rest}".rstrip())
            continue
        out_lines.append(line)
    body_str = "\n".join(out_lines).strip()

    # Subject heading on top (h1) - the user's convention.
    if subject is not None:
        sno, sname = subject
        body_str = f"# {sno}과목 {sname}\n\n" + body_str
    return body_str


def build_front_matter(
    orig_num: int,
    subject: Optional[Tuple[int, str]],
) -> str:
    sno = subject[0] if subject else None
    sname = subject[1] if subject else None
    return (
        "---\n"
        f"round: null\n"
        f"subject: {sname or 'null'}\n"
        f"subject_no: {sno if sno is not None else 'null'}\n"
        f"problem_no: {orig_num}\n"
        f"answer: null\n"
        f"keywords: []\n"
        "---\n\n"
    )


ANSWER_BLOCK = (
    "\n\n#### 정답\n\n① ② ③ ④\n\n_(정답이 아닌 것을 지우세요)_\n"
)


def write_problems(
    intro_text: str,
    bodies: List[Tuple[int, str, Optional[Tuple[int, str]]]],
    out_dir: Path,
    plain: bool = False,
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
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

    for seq, (orig_num, body, subject) in enumerate(bodies, 1):
        name = f"Q{seq:03d}_orig{orig_num:02d}.md"
        p = out_dir / name
        if plain:
            content = body.rstrip() + ANSWER_BLOCK
        else:
            content = (
                build_front_matter(orig_num, subject)
                + rewrite_body_user_style(body, orig_num, subject).rstrip()
                + ANSWER_BLOCK
            )
        p.write_text(content, encoding="utf-8")
        written.append(p)
    return written


def main():
    ap = argparse.ArgumentParser(description="Split a mineru/paddle markdown into per-problem .md files.")
    ap.add_argument("src_md", help="Path to the combined .md (e.g. assets/after--<stem>.md)")
    ap.add_argument("-o", "--out-dir", default=None,
                    help="Output folder (default: <src>_problems/ next to the source)")
    ap.add_argument("--plain", action="store_true",
                    help="Skip front-matter and heading rewrites (just split on ## NN)")
    args = ap.parse_args()

    src = Path(args.src_md).resolve()
    if not src.exists():
        raise SystemExit(f"not found: {src}")

    out_dir = Path(args.out_dir).resolve() if args.out_dir else src.with_name(src.stem + "_problems")
    text = src.read_text(encoding="utf-8", errors="replace")
    intro_text, bodies = split_chunks(text)
    written = write_problems(intro_text, bodies, out_dir, plain=args.plain)

    # report
    subj_counter: dict = {}
    for _, _, subj in bodies:
        key = f"{subj[0]}과목 {subj[1]}" if subj else "(미분류)"
        subj_counter[key] = subj_counter.get(key, 0) + 1

    print(f"Source        : {src}")
    print(f"Output folder : {out_dir}")
    print(f"Intro chunk   : {'yes' if intro_text else 'no'}")
    print(f"Problems      : {len(bodies)}")
    print(f"Files written : {len(written)}")
    print(f"User-style    : {'no (plain)' if args.plain else 'yes (front-matter + heading rewrites)'}")
    print(f"Subjects assigned:")
    for k, v in subj_counter.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
