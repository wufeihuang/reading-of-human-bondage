#!/usr/bin/env python3
"""Extract one chapter of Of Human Bondage from the Project Gutenberg text.

Usage:
    python3 extract_chapter.py 3          # writes chapter-03.txt, prints stats
    python3 extract_chapter.py --next     # reads progress.md and extracts the next one

The Gutenberg edition (#351) marks chapters with a bare Roman numeral on its own
line. The number of chapters in the source is 122.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "pg351.txt"

ROMAN = {c: v for c, v in zip("IVXLCDM", (1, 5, 10, 50, 100, 500, 1000))}


def to_int(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s):
        v = ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def headings(lines):
    out = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s and re.fullmatch(r"[IVXLCDM]+", s) and to_int(s) < 200:
            if i > 0 and lines[i - 1].strip() == "":
                out.append((i, to_int(s)))
    # keep the first occurrence of each number
    seen, res = set(), []
    for i, n in out:
        if n not in seen:
            seen.add(n)
            res.append((i, n))
    return res


def previous_chapter() -> int:
    prog = HERE / "progress.md"
    if not prog.exists():
        return 0
    m = re.search(r"已完成[:：]\s*第\s*(\d+)\s*章", prog.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else 0


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 1
    n = previous_chapter() + 1 if args[0] == "--next" else int(args[0])

    lines = SOURCE.read_text(encoding="utf-8").split("\n")
    heads = headings(lines)
    starts = {num: i for i, num in heads}
    if n not in starts:
        print(f"chapter {n} not found (found {len(heads)} headings: "
              f"{min(starts)}-{max(starts)})")
        return 2
    end = next((i for i, num in heads if num == n + 1), len(lines))
    body = "\n".join(lines[starts[n] + 1:end]).strip()
    # 最后一章后面跟着 Gutenberg 的许可协议，切掉
    body = body.split("*** END OF")[0].strip()
    out = HERE / f"chapter-{n:02d}.txt"
    out.write_text(body + "\n", encoding="utf-8")
    print(f"{out.name}: {len(body.split())} words, {len(body)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
