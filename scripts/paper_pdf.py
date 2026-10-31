#!/usr/bin/env python3
"""Typeset the paper as a PDF: dist/paper/paper.md and its figure SVGs -> LaTeX with TikZ figures -> paper.pdf.

  python scripts/paper_pdf.py             write pdf-out/paper.tex and pdf-out/figures/*.tex, then compile pdf-out/paper.pdf
  python scripts/paper_pdf.py --tex-only  write the LaTeX source only (no TeX engine needed)
  python scripts/paper_pdf.py --out DIR   write to DIR instead of pdf-out/

Optional and outside `make check` and CI (ADR-0008); `make pdf` runs `make build` first. The LaTeX is written by this
script alone from the built paper, so the same build gives the same source. The PDF is compiled with tectonic, a
self-contained XeTeX engine that fetches its TeX packages and fonts from a versioned bundle and caches them (the first run
needs the network). It runs in deterministic mode with SOURCE_DATE_EPOCH set to the paper's date, so no clock time enters
the file, and one tectonic version gives a byte-identical PDF. The source is kept out of dist/ because `make build`
removes files it did not write. Figures are drawn from the same SVGs the site shows: the subset scripts/viz.py and
scripts/analyze.py write (rect, line, circle, polyline, path, text, g) is translated to TikZ, and anything outside it
stops the script rather than drawing a wrong picture.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402
from markdown_it import MarkdownIt  # noqa: E402

from lib import ROOT, read_yaml  # noqa: E402

TECTONIC = "0.17.0"  # the version the byte-identical PDF was checked with
OUT = ROOT / "pdf-out"
SVG_NS = "{http://www.w3.org/2000/svg}"
NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
URL = re.compile(r"https?://[^\s<>()\[\]]*[^\s<>()\[\].,;:!?'\"]")
WIKI = re.compile(r"^(?:\.\./)+wiki/(\w+)/([a-z0-9-]+)\.md$")
TEX_ESC = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&", "#": r"\#", "^": r"\^{}", "_": r"\_",
           "%": r"\%", "~": r"\textasciitilde{}", "<": r"\textless{}", ">": r"\textgreater{}", "|": r"\textbar{}",
           "ρ": r"\ensuremath{\rho}"}
# page geometry, in points: the table and figure sizing below assume it
TEXT_W, TEXT_H = 469.75, 650.0
TABLE_CH, TABLE_SEP = 4.3, 3.0  # width of a footnotesize character, with room for capitals; \tabcolsep


def esc(s: str, breaks: str = "") -> str:
    """LaTeX-escape plain text; `breaks` are characters after which a line may break (paths, ids)."""
    return "".join(TEX_ESC.get(c, c) + (r"\allowbreak{}" if c in breaks else "") for c in s)


def esc_url(u: str) -> str:
    return u.replace("\\", "/").replace("%", r"\%").replace("#", r"\#").replace("&", r"\&").replace("~", r"\~{}")


def num(x: float) -> str:
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ---------------------------------------------------------------- SVG -> TikZ

INHERITED = ("fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "stroke-dasharray", "stroke-linejoin",
             "stroke-linecap", "font-size", "font-weight", "font-style", "text-anchor")


def svg_color(v: str) -> str | None:
    v = v.strip()
    m = re.fullmatch(r"var\(--[\w-]+\s*,\s*(.+)\)", v)
    if m:
        v = m.group(1).strip()
    if v in ("none", "transparent", ""):
        return None
    if re.fullmatch(r"#[0-9a-fA-F]{3}", v):
        return "".join(c * 2 for c in v[1:]).lower()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v[1:].lower()
    named = {"white": "ffffff", "black": "000000"}
    if v in named:
        return named[v]
    raise SystemExit(f"paper_pdf: unsupported SVG colour {v!r}")


def px(v, default=0.0) -> float:
    m = NUM.match(str(v).strip()) if v is not None else None
    return float(m.group(0)) if m else default


class Figure:
    """One SVG figure as a tikzpicture, in SVG units (1 px = 1 pt, y down); the paper scales the whole picture to fit."""

    def __init__(self, svg: str, name: str):
        self.name = name
        self.root = ET.fromstring(svg)
        vb = [float(x) for x in NUM.findall(self.root.get("viewBox", ""))]
        self.box = vb if len(vb) == 4 else [0, 0, px(self.root.get("width")), px(self.root.get("height"))]
        self.colors: set[str] = set()
        self.lines: list[str] = []

    def c(self, hexv: str) -> str:
        self.colors.add(hexv)
        return f"sg{hexv}"

    def style(self, el, parent: dict) -> dict:
        st = {k: v for k, v in parent.items() if k in INHERITED}
        for k in INHERITED + ("opacity", "display"):
            if el.get(k) is not None:
                st[k] = el.get(k)
        for decl in (el.get("style") or "").split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                st[k.strip()] = v.strip()
        st["_opacity"] = parent.get("_opacity", 1.0) * float(st.pop("opacity", 1) or 1)
        return st

    def paint(self, st: dict, fill=True) -> list[str] | None:
        o = []
        f = svg_color(st.get("fill", "#000000")) if fill else None
        s = svg_color(st.get("stroke", "none"))
        if f:
            o.append(f"fill={self.c(f)}")
            fo = float(st.get("fill-opacity", 1)) * st["_opacity"]
            if fo < 1:
                o.append(f"fill opacity={num(fo)}")
        if s:
            o.append(f"draw={self.c(s)}")
            o.append(f"line width={num(px(st.get('stroke-width', 1), 1))}pt")
            so = float(st.get("stroke-opacity", 1)) * st["_opacity"]
            if so < 1:
                o.append(f"draw opacity={num(so)}")
            dash = [px(x) for x in re.split(r"[\s,]+", st.get("stroke-dasharray", "none").strip()) if NUM.match(x)]
            if dash:
                dash = dash * 2 if len(dash) % 2 else dash
                o.append("dash pattern=" + " ".join(f"{'on' if i % 2 == 0 else 'off'} {num(d)}pt" for i, d in enumerate(dash)))
            if st.get("stroke-linejoin") in ("round", "bevel"):
                o.append(f"line join={st['stroke-linejoin']}")
            if st.get("stroke-linecap") in ("round", "square"):
                o.append(f"line cap={'rect' if st['stroke-linecap'] == 'square' else 'round'}")
        return o or None

    def path_d(self, d: str) -> str:
        toks = re.findall(r"[MmLlHhVvCcSsQqZz]|" + NUM.pattern, d)
        if re.search(r"[AaTt]", d):
            raise SystemExit(f"paper_pdf: {self.name}: SVG path command outside the supported subset in {d[:60]!r}")
        out, i, cmd = [], 0, None
        x = y = sx = sy = 0.0
        prev_c2 = None

        def take(n):
            nonlocal i
            v = [float(t) for t in toks[i:i + n]]
            i += n
            return v

        while i < len(toks):
            if toks[i].isalpha():
                cmd = toks[i]
                i += 1
                if cmd in "Zz":
                    out.append("-- cycle")
                    x, y = sx, sy
                    prev_c2 = None
                    continue
            rel = cmd.islower()
            ox, oy = (x, y) if rel else (0.0, 0.0)
            C = cmd.upper()
            if C == "M":
                a, b = take(2)
                x, y = ox + a, oy + b
                sx, sy = x, y
                out.append(f"({num(x)},{num(y)})")
                cmd = "l" if rel else "L"  # further pairs after a moveto are line segments
                prev_c2 = None
            elif C in "LHV":
                if C == "L":
                    a, b = take(2)
                    x, y = ox + a, oy + b
                elif C == "H":
                    x = ox + take(1)[0]
                else:
                    y = oy + take(1)[0]
                out.append(f"-- ({num(x)},{num(y)})")
                prev_c2 = None
            elif C in "CS":
                if C == "C":
                    x1, y1, x2, y2, a, b = take(6)
                    c1 = (ox + x1, oy + y1)
                else:
                    x2, y2, a, b = take(4)
                    c1 = (2 * x - prev_c2[0], 2 * y - prev_c2[1]) if prev_c2 else (x, y)
                c2 = (ox + x2, oy + y2)
                x, y = ox + a, oy + b
                out.append(f".. controls ({num(c1[0])},{num(c1[1])}) and ({num(c2[0])},{num(c2[1])}) .. ({num(x)},{num(y)})")
                prev_c2 = c2
            elif C == "Q":
                qx, qy, a, b = take(4)
                qx, qy, ex, ey = ox + qx, oy + qy, ox + a, oy + b
                c1 = (x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y))
                c2 = (ex + 2 / 3 * (qx - ex), ey + 2 / 3 * (qy - ey))
                x, y = ex, ey
                out.append(f".. controls ({num(c1[0])},{num(c1[1])}) and ({num(c2[0])},{num(c2[1])}) .. ({num(x)},{num(y)})")
                prev_c2 = None
        return " ".join(out)

    def text_runs(self, el, st) -> list[tuple[str, str | None]]:
        base = svg_color(st.get("fill", "#000000"))
        runs = [(el.text or "", base)]
        for ch in el:
            if ch.tag == SVG_NS + "tspan":
                runs.append((ch.text or "", svg_color(self.style(ch, st).get("fill", "#000000"))))
            elif ch.tag not in (SVG_NS + "title", SVG_NS + "desc"):
                raise SystemExit(f"paper_pdf: {self.name}: <{ch.tag.removeprefix(SVG_NS)}> inside <text> is outside the supported subset")
            runs.append((ch.tail or "", base))
        return runs

    def text(self, el, st):
        runs = self.text_runs(el, st)
        flat = re.sub(r"\s+", " ", "".join(t for t, _ in runs))
        if not flat.strip():
            return
        base = runs[0][1]
        body, lead = [], True
        for t, col in runs:
            t = re.sub(r"\s+", " ", t)
            if lead:
                t = t.lstrip()
                lead = not t
            if not t:
                continue
            body.append(esc(t) if col == base or col is None else rf"\textcolor{{{self.c(col)}}}{{{esc(t)}}}")
        while body and body[-1].endswith(" "):
            body[-1] = body[-1].rstrip()
        anchor = {"start": "base west", "middle": "base", "end": "base east"}.get(st.get("text-anchor", "start"), "base west")
        size = px(st.get("font-size", 16), 16)
        font = rf"\ttfamily\fontsize{{{num(size)}}}{{{num(size * 1.2)}}}\selectfont"
        if str(st.get("font-weight", "normal")) in ("bold", "bolder", "600", "700", "800", "900"):
            font += r"\bfseries"
        if st.get("font-style") == "italic":
            font += r"\itshape"
        o = [f"anchor={anchor}", "inner sep=0pt", "outer sep=0pt", f"font={{{font}}}"]
        if base:
            o.append(f"text={self.c(base)}")
        op = float(st.get("fill-opacity", 1)) * st["_opacity"]
        if op < 1:
            o.append(f"text opacity={num(op)}")
        x, y = px(el.get("x")) + px(el.get("dx")), px(el.get("y")) + px(el.get("dy"))
        self.lines.append(rf"\node[{', '.join(o)}] at ({num(x)},{num(y)}) {{{''.join(body)}}};")

    def transform(self, t: str) -> list[str]:
        o = []
        for fn, args in re.findall(r"(\w+)\s*\(([^)]*)\)", t):
            a = [float(v) for v in NUM.findall(args)]
            if fn == "translate":
                o.append(f"shift={{({num(a[0])},{num(a[1] if len(a) > 1 else 0)})}}")
            elif fn == "rotate":  # SVG turns clockwise on screen; the y-down TikZ frame turns the other way
                o.append(f"rotate around={{{num(-a[0])}:({num(a[1])},{num(a[2])})}}" if len(a) == 3 else f"rotate={num(-a[0])}")
            elif fn == "scale":
                o.append(f"xscale={num(a[0])}, yscale={num(a[1] if len(a) > 1 else a[0])}")
            else:
                raise SystemExit(f"paper_pdf: {self.name}: SVG transform {fn}() is outside the supported subset")
        return o + ["transform shape"] if o else o

    def walk(self, el, parent: dict):
        tag = el.tag.removeprefix(SVG_NS)
        if tag in ("title", "desc"):
            return
        st = self.style(el, parent)
        if st.get("display") == "none":
            return
        scope = self.transform(el.get("transform", "")) if el.get("transform") else []
        if scope:
            self.lines.append(rf"\begin{{scope}}[{', '.join(scope)}]")
        if tag in ("svg", "g"):
            for ch in el:
                self.walk(ch, st)
        elif tag == "rect":
            o = self.paint(st)
            if o:
                if px(el.get("rx")):
                    o.append(f"rounded corners={num(px(el.get('rx')))}pt")
                x, y, w, h = (px(el.get(k)) for k in ("x", "y", "width", "height"))
                self.lines.append(rf"\path[{', '.join(o)}] ({num(x)},{num(y)}) rectangle ++({num(w)},{num(h)});")
        elif tag == "line":
            o = self.paint(st, fill=False)
            if o:
                pts = [px(el.get(k)) for k in ("x1", "y1", "x2", "y2")]
                self.lines.append(rf"\path[{', '.join(o)}] ({num(pts[0])},{num(pts[1])}) -- ({num(pts[2])},{num(pts[3])});")
        elif tag == "circle":
            o = self.paint(st)
            if o:
                self.lines.append(rf"\path[{', '.join(o)}] ({num(px(el.get('cx')))},{num(px(el.get('cy')))}) circle[radius={num(px(el.get('r')))}];")
        elif tag in ("polyline", "polygon"):
            o = self.paint(st)
            v = [float(n) for n in NUM.findall(el.get("points", ""))]
            if o and len(v) >= 4:
                pts = " -- ".join(f"({num(v[i])},{num(v[i + 1])})" for i in range(0, len(v) - 1, 2))
                self.lines.append(rf"\path[{', '.join(o)}] {pts}{' -- cycle' if tag == 'polygon' else ''};")
        elif tag == "path":
            o = self.paint(st)
            if o:
                self.lines.append(rf"\path[{', '.join(o)}] {self.path_d(el.get('d', ''))};")
        elif tag == "text":
            self.text(el, st)
        else:
            raise SystemExit(f"paper_pdf: {self.name}: SVG element <{tag}> is outside the supported subset")
        if scope:
            self.lines.append(r"\end{scope}")

    def tex(self) -> str:
        self.walk(self.root, {"_opacity": 1.0, "font-size": "16"})
        x, y, w, h = self.box
        head = [f"% {self.name}: drawn by scripts/paper_pdf.py from dist/paper/figures/{self.name}.svg. Do not edit."]
        head += [rf"\providecolor{{sg{c}}}{{HTML}}{{{c.upper()}}}" for c in sorted(self.colors)]
        return "\n".join(head + [r"\begin{tikzpicture}[x=1pt, y=-1pt]",
                                 rf"\useasboundingbox ({num(x)},{num(y)}) rectangle ++({num(w)},{num(h)});",
                                 rf"\clip ({num(x)},{num(y)}) rectangle ++({num(w)},{num(h)});"]
                         + self.lines + [r"\end{tikzpicture}"]) + "\n"


# ---------------------------------------------------------------- Markdown -> LaTeX

def plain(children) -> str:
    return "".join(c.content for c in children or [] if c.type in ("text", "code_inline"))


class Paper:
    def __init__(self, site: str, figures: dict[str, tuple[float, float]]):
        self.site = site
        self.figures = figures  # name -> (width, height) of the SVG viewBox

    def href(self, h: str) -> str:
        m = WIKI.match(h)
        if m:
            return f"{self.site}{m.group(1)}/{m.group(2)}/"
        if re.match(r"^[a-z]+:", h):
            return h
        return f"{self.site}dist/paper/{h}"  # a path relative to paper.md, as published under /dist/

    def text(self, s: str, breaks: str = "") -> str:
        out, last = [], 0
        for m in URL.finditer(s):
            out.append(esc(s[last:m.start()], breaks) + rf"\url{{{esc_url(m.group(0))}}}")
            last = m.end()
        return "".join(out) + esc(s[last:], breaks)

    def inline(self, children, breaks: str = "") -> str:
        out = []
        for c in children or []:
            t = c.type
            if t == "text":
                out.append(self.text(c.content, breaks))
            elif t == "softbreak":
                out.append("\n")
            elif t == "hardbreak":
                out.append("\\par\n")
            elif t in ("strong_open", "em_open"):
                out.append(r"\textbf{" if t == "strong_open" else r"\emph{")
            elif t in ("strong_close", "em_close", "link_close"):
                out.append("}")
            elif t == "code_inline":
                out.append(rf"\texttt{{{esc(c.content, '/._-:')}}}")
            elif t == "link_open":
                h = c.attrGet("href") or ""
                out.append(rf"\hyperlink{{{h[1:]}}}{{" if h.startswith("#") else rf"\href{{{esc_url(self.href(h))}}}{{")
            elif t == "html_inline":
                m = re.fullmatch(r'<a id="([^"]+)">', c.content.strip())
                out.append(rf"\hypertarget{{{m.group(1)}}}{{}}" if m else "")
            elif t == "image":
                out.append(self.figure(c.attrGet("src") or ""))
            else:
                raise SystemExit(f"paper_pdf: unsupported inline markdown token {t}")
        return "".join(out)

    def figure(self, src: str) -> str:
        name = Path(src).stem
        w, h = self.figures[name]
        fit = r"{\linewidth}{!}" if h / w <= TEXT_H * 0.85 / TEXT_W else r"{!}{0.85\textheight}"
        return f"\n\\begin{{center}}\n\\resizebox{fit}{{\\input{{figures/{name}.tex}}}}\n\\end{{center}}\n"

    def table(self, toks) -> str:
        rows, cur = [], []
        for t in toks:
            if t.type == "tr_open":
                cur = []
            elif t.type in ("th_open", "td_open"):
                s = t.attrGet("style") or ""
                cur.append({"align": "r" if "right" in s else "c" if "center" in s else "l", "head": t.type == "th_open"})
            elif t.type == "inline":
                cur[-1]["tex"] = self.inline(t.children, "-/")
                cur[-1]["plain"] = plain(t.children)
            elif t.type == "tr_close":
                rows.append(cur)
        n = len(rows[0])
        align = [c["align"] for c in rows[0]]
        # lengths in characters; header cells are bold, so they count wider
        size = lambda c, s: len(s) * (1.25 if c["head"] else 1)
        nat = [max(size(r[i], r[i].get("plain", "")) for r in rows if i < len(r)) or 1 for i in range(n)]
        word = [max((size(r[i], w) for r in rows if i < len(r) for w in re.split(r"[\s/-]+", r[i].get("plain", ""))), default=1) for i in range(n)]
        budget = (TEXT_W - 2 * TABLE_SEP * n) / TABLE_CH
        if sum(nat) <= budget:
            spec = "".join(align)
        else:
            low = [min(nat[i], max(3, min(word[i], 18))) for i in range(n)]
            lo, hi = 0.0, float(max(nat))
            for _ in range(60):  # widest columns give way first, never below their longest word (up to 18 characters)
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if sum(min(nat[i], max(mid, low[i])) for i in range(n)) <= budget else (lo, mid)
            w = [min(nat[i], max(lo, low[i])) for i in range(n)]
            spec = "".join(rf">{{\{'raggedleft' if align[i] == 'r' else 'centering' if align[i] == 'c' else 'raggedright'}\arraybackslash}}"
                           rf"p{{{num(w[i] / sum(w) * (TEXT_W - 2 * TABLE_SEP * n))}pt}}" for i in range(n))

        def row(r, bold=False):
            cells = [c.get("tex", "") for c in r] + [""] * (n - len(r))
            cells = [("{}" if c.startswith("[") else "") + (rf"\textbf{{{c}}}" if bold and c else c) for c in cells]
            return " & ".join(cells) + r" \\"

        body = [row(rows[0], bold=True), r"\midrule", r"\endhead"] + [row(r) for r in rows[1:]]
        return "\n".join([rf"\begingroup\footnotesize\setlength{{\tabcolsep}}{{{num(TABLE_SEP)}pt}}", rf"\begin{{longtable}}{{{spec}}}", r"\toprule"]
                         + body + [r"\bottomrule", r"\end{longtable}", r"\endgroup", ""]) + "\n"

    def blocks(self, toks) -> str:
        out, i = [], 0
        while i < len(toks):
            t = toks[i]
            ty = t.type
            if ty == "heading_open":
                title = self.inline(toks[i + 1].children)
                cmd, toc = {"h1": ("section", 1), "h2": ("section", 1), "h3": ("subsection", 2)}.get(t.tag, ("subsubsection", 3))
                out.append(f"\\{cmd}*{{{title}}}\\phantomsection\\addcontentsline{{toc}}{{{cmd}}}{{{title}}}\n\n")
                i += 3
                continue
            if ty == "paragraph_open":
                out.append(self.inline(toks[i + 1].children) + ("\n" if t.hidden else "\n\n"))
                i += 3
                continue
            if ty == "table_open":
                j = next(k for k in range(i, len(toks)) if toks[k].type == "table_close")
                out.append(self.table(toks[i:j + 1]))
                i = j + 1
                continue
            if ty == "bullet_list_open":
                out.append("\\begin{itemize}\n")
            elif ty == "ordered_list_open":
                start = int(t.attrGet("start") or 1)
                out.append("\\begin{enumerate}" + (f"[start={start}]" if start != 1 else "") + "\n")
            elif ty in ("bullet_list_close", "ordered_list_close"):
                out.append("\\end{itemize}\n\n" if ty == "bullet_list_close" else "\\end{enumerate}\n\n")
            elif ty == "list_item_open":
                out.append("\\item{} ")
            elif ty == "blockquote_open":
                out.append("\\begin{quote}\n")
            elif ty == "blockquote_close":
                out.append("\\end{quote}\n\n")
            elif ty in ("fence", "code_block"):
                out.append("\\begin{verbatim}\n" + t.content.rstrip("\n") + "\n\\end{verbatim}\n\n")
            elif ty == "hr":
                out.append("\\par\\noindent\\rule{\\linewidth}{0.4pt}\\par\n\n")
            elif ty == "html_block":
                out += [rf"\hypertarget{{{a}}}{{}}" for a in re.findall(r'<a id="([^"]+)">', t.content)]
            elif ty not in ("list_item_close",):
                raise SystemExit(f"paper_pdf: unsupported markdown block token {ty}")
            i += 1
        return "".join(out)


def latex(paper_md: str, meta: dict, manifest: dict, figures: dict) -> str:
    _, fm, body = paper_md.split("---\n", 2)
    fm = yaml.safe_load(fm)
    md = MarkdownIt("commonmark", {"html": True}).enable("table")  # as scripts/web.py renders it
    site = meta["site"]["url"]
    tex_body = Paper(site, figures).blocks(md.parse(body))
    authors = [esc(a) for a in fm["author"]]
    short = fm["dataset_sha256"][:12]
    pdfmeta = ", ".join([f"pdftitle={{{esc(fm['title'])}: {esc(fm['subtitle'])}}}", f"pdfauthor={{{', '.join(authors)}}}",
                         f"pdfsubject={{Version {esc(fm['version'])}, dataset sha256 {fm['dataset_sha256']}}}"])
    return "\n".join([
        f"% {fm['title']} v{fm['version']}: written by scripts/paper_pdf.py from dist/paper/paper.md (dataset {fm['dataset_sha256']}).",
        "% Do not edit; edit report/src and rebuild. Compile with XeLaTeX (tectonic): it loads IBM Plex Mono through fontspec.",
        r"\documentclass[10pt]{article}",
        r"\usepackage[letterpaper, textwidth=" + f"{TEXT_W}pt, textheight={TEXT_H}pt" + r", centering]{geometry}",
        r"\usepackage{fontspec}",
        r"\setmonofont{IBMPlexMono}[Extension=.otf, UprightFont=*-Regular, BoldFont=*-Bold, ItalicFont=*-Italic, BoldItalicFont=*-BoldItalic, Scale=MatchLowercase]",
        r"\usepackage{xcolor, graphicx, tikz, longtable, array, booktabs, enumitem, parskip, fancyhdr}",
        r"\usepackage[hyphens]{url}",
        r"\usepackage{hyperref}",
        r"\definecolor{sgaccent}{HTML}{0550AE}",
        r"\hypersetup{colorlinks=true, linkcolor=sgaccent, urlcolor=sgaccent, citecolor=sgaccent, " + pdfmeta + "}",
        r"\setlist{itemsep=0.2em, topsep=0.3em}",
        r"\setcounter{tocdepth}{2}",
        r"\setlength{\emergencystretch}{3em}",
        r"\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}",
        rf"\fancyfoot[L]{{\footnotesize {esc(fm['title'])} v{esc(fm['version'])} \textperiodcentered{{}} dataset \texttt{{{short}}}}}",
        r"\fancyfoot[R]{\footnotesize\thepage}",
        rf"\title{{\textbf{{{esc(fm['title'])}}}\\[0.5em]\large {esc(fm['subtitle'])}}}",
        r"\author{" + r" \and ".join(authors) + "}",
        rf"\date{{Version {esc(fm['version'])} \textperiodcentered{{}} {esc(fm['date'])}\\[0.6em]\small dataset sha256 \texttt{{{fm['dataset_sha256']}}}\\"
        rf"contract {esc(manifest['contract_version'])} \textperiodcentered{{}} \url{{{esc_url(site + 'paper/')}}}}}",
        r"\begin{document}",
        r"\maketitle\thispagestyle{fancy}",
        r"\tableofcontents",
        r"\clearpage",
        tex_body.rstrip(),
        r"\end{document}",
        ""])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT, help="output directory (default pdf-out/)")
    ap.add_argument("--tex-only", action="store_true", help="write the LaTeX source without compiling it")
    args = ap.parse_args()
    dist = ROOT / "dist"
    if not (dist / "paper" / "paper.md").exists():
        raise SystemExit("paper_pdf: dist/paper/paper.md is missing; run `make build` first")
    meta = read_yaml(ROOT / "report" / "meta.yaml")
    manifest = json.loads((dist / "manifest.json").read_text(encoding="utf-8"))
    out = args.out.resolve()
    shutil.rmtree(out / "figures", ignore_errors=True)
    (out / "figures").mkdir(parents=True)
    figures = {}
    for p in sorted((dist / "paper" / "figures").glob("*.svg")):
        f = Figure(p.read_text(encoding="utf-8"), p.stem)
        (out / "figures" / f"{p.stem}.tex").write_text(f.tex(), encoding="utf-8")
        figures[p.stem] = (f.box[2], f.box[3])
    tex = latex((dist / "paper" / "paper.md").read_text(encoding="utf-8"), meta, manifest, figures)
    (out / "paper.tex").write_text(tex, encoding="utf-8")
    print(f"paper_pdf: wrote {out / 'paper.tex'} and {len(figures)} figures")
    if args.tex_only:
        return
    exe = shutil.which("tectonic")
    if not exe:
        raise SystemExit("paper_pdf: tectonic is not installed (https://tectonic-typesetting.github.io; `brew install tectonic`); "
                         "--tex-only writes the source for another XeLaTeX")
    version = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout.split()[-1]
    if version != TECTONIC:
        print(f"paper_pdf: tectonic {version}; the byte-identical PDF was checked with {TECTONIC}, so this one may differ")
    epoch = calendar.timegm(date.fromisoformat(str(meta["date"])).timetuple())
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    r = subprocess.run([exe, "-Z", "deterministic-mode", "--chatter", "minimal", "paper.tex"], cwd=out, env=env)
    if r.returncode:
        raise SystemExit(f"paper_pdf: tectonic failed ({r.returncode}); rerun it in {out} with --keep-logs to see the TeX log")
    pdf = out / "paper.pdf"
    print(f"paper_pdf: {pdf} ({pdf.stat().st_size} bytes) sha256 {hashlib.sha256(pdf.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
