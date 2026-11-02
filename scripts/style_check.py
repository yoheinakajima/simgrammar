"""House-style lint for the book and the videos (book/STYLE.md).

Checks book/src, media/episodes, media/shorts, media/mega, media/intro, and the files in EXTRA against the patterns in book/tells.yaml, and checks
that no episode or short ends its narration on a question. Exits 1 on any error.

    python scripts/style_check.py            # all prose
    python scripts/style_check.py FILE ...   # some files
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from lib import ROOT, read_yaml

DIRS = ["book/src", "media/episodes", "media/shorts", "media/mega", "media/intro"]
EXTRA: list[str] = ["decisions/ADR-0006-visual-vocabulary.md", "media/visual/README.md"]
TOKEN = re.compile(r"\{\{[a-z_]+:[^}]+\}\}")
LINK = re.compile(r"\[\[[a-z0-9-]+\|([^\]]+)\]\]|\[\[([a-z0-9-]+)\]\]")
CITE = re.compile(r"\s?\[@src-[^\]]+\]")
OK = re.compile(r"<!--\s*tells-ok:\s*([a-z0-9 ,-]+?)\s*-->")
VOICE = re.compile(r"^\*\*Voice\.\*\*\s*(.*)$")


def patterns() -> list[dict]:
    spec = read_yaml(ROOT / "book" / "tells.yaml") or {}
    out = []
    for group in ("words", "phrases", "structures"):
        for p in spec.get(group) or []:
            out.append({**p, "re": re.compile(p["pattern"], re.I), "severity": p.get("severity", "error")})
    return out


def plain(line: str) -> str:
    line = TOKEN.sub("", line)
    line = LINK.sub(lambda m: m.group(1) or m.group(2).replace("-", " "), line)
    line = CITE.sub("", line)
    return line


def files(args: list[str]) -> list[Path]:
    if args:
        return [Path(a).resolve() for a in args]
    fs = [p for d in DIRS for p in sorted((ROOT / d).glob("*.md"))]
    return fs + [ROOT / x for x in EXTRA if (ROOT / x).exists()]


def check_file(p: Path, pats: list[dict]) -> list[tuple[str, str]]:
    found = []
    in_code = False
    rel = p.relative_to(ROOT) if p.is_relative_to(ROOT) else p
    lines = p.read_text(encoding="utf-8").splitlines()
    for n, raw in enumerate(lines, start=1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        allowed = set()
        for m in OK.finditer(raw):
            allowed.update(x.strip() for x in m.group(1).split(","))
        text = plain(OK.sub("", raw))
        for pat in pats:
            if pat["id"] in allowed:
                continue
            m = pat["re"].search(text)
            if m:
                found.append((pat["severity"], f"{rel}:{n}: {pat['id']}: '{m.group(0).strip()}' ({pat['why']})"))
    if rel.parts[:1] == ("media",):
        voices = [(n, VOICE.match(l).group(1)) for n, l in enumerate(lines, start=1) if VOICE.match(l)]
        if voices and plain(voices[-1][1]).rstrip().endswith("?"):
            found.append(("error", f"{rel}:{voices[-1][0]}: closing-question: the last narration line ends on a question; end on a statement"))
    return found


def main(argv: list[str]) -> int:
    pats = patterns()
    errors = warns = 0
    for p in files(argv):
        for sev, msg in check_file(p, pats):
            print(("ERROR " if sev == "error" else "warn  ") + msg)
            errors += sev == "error"
            warns += sev != "error"
    print(f"style: {errors} error(s), {warns} warning(s). {'OK' if not errors else 'FAIL'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
