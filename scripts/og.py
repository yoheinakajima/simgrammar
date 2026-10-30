"""Link-preview images (og:image) for the website, 1200 x 630 PNG, drawn from the dithered icons (ADR-0006) and the
vendored IBM Plex fonts (media/fonts). scripts/web.py calls images() and every page names its image in og:image.

  og/site.png                    the paper (home page)
  og/<type>.png                  the game, mechanic, technique, opportunity, and source indexes
  og/watch.png, og/book.png      the watch page and the book's contents
  og/watch/<episode>.png         every episode page
  og/<type>/<id>.png             every game, mechanic, technique, and opportunity page
  og/book/<chapter>.png          every book chapter

A 480 px panel on the left draws the subject: a record's icon, a game's parts, an opportunity's mechanics, a chapter's
mechanics, or for the indexes the icons of what they list. Icons are pasted at 2, 1, 1/2 or 1/4 of their 192 px raster,
so every dither pixel stays whole. The right side sets the kind and id, the name, the summary, and one line of counts.
"""
from __future__ import annotations

import io
import re

from PIL import Image, ImageDraw, ImageFont

from lib import ROOT, read_yaml

W, H, ART, PAD = 1200, 630, 480, 56
PAPER, PANEL, INK, MUTED, FAINT, RULE = (250, 250, 247), (238, 238, 233), (23, 23, 23), (85, 85, 79), (140, 140, 134), (200, 200, 194)
_fonts: dict = {}


def font(name: str, size: int):
    if (name, size) not in _fonts:
        _fonts[(name, size)] = ImageFont.truetype(str(ROOT / "media" / "fonts" / f"IBMPlex{name}.woff2"), size)
    return _fonts[(name, size)]


def wrap(text: str, f, width: int, max_lines: int) -> list[str]:
    """Greedy word wrap; the last line ends in an ellipsis when the text does not fit."""
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if not cur or f.getlength(t) <= width:
            cur = t
            continue
        lines.append(cur)
        cur = w
        if len(lines) == max_lines:
            break
    else:
        if cur:
            lines.append(cur)
        return lines
    last = lines[-1]
    while last and f.getlength(last + "…") > width:
        last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
    lines[-1] = last + "…"
    return lines


def _icon(png: bytes, size: int) -> Image.Image:
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    return im if size == im.width else im.resize((size, size), Image.NEAREST)


def art(im: Image.Image, icons: list[bytes]):
    """Lay icons out in the left panel: one large, a 2 x 2, a 3 x 3, a 4 x 4, or an 8-column mosaic."""
    n = len(icons)
    if not n:
        return
    if n == 1:
        size, cols, gap = 384, 1, 0
    elif n <= 4:
        size, cols, gap = 192, 2, 24
    elif n <= 9:
        size, cols, gap = 96, 3, 24
    elif n <= 16:
        size, cols, gap = 96, 4, 12
    else:
        size, cols, gap = 48, 8, 8
        icons = icons[:80]
    rows = (len(icons) + cols - 1) // cols
    gw, gh = cols * size + (cols - 1) * gap, rows * size + (rows - 1) * gap
    x0, y0 = (ART - gw) // 2, (H - gh) // 2
    for k, png in enumerate(icons):
        ic = _icon(png, size)
        im.paste(ic, (x0 + (k % cols) * (size + gap), y0 + (k // cols) * (size + gap)), ic)


def card(eyebrow: str, title: str, desc: str, foot: str, icons: list[bytes]) -> bytes:
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, ART, H], fill=PANEL)
    art(im, icons)
    d.line([(ART, 0), (ART, H)], fill=INK, width=2)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=2)
    x, tw = ART + PAD, W - ART - 2 * PAD
    mark = font("Mono-Medium", 20)
    domain = read_yaml(ROOT / "report" / "meta.yaml")["site"]["domain"]
    d.text((W - PAD, PAD + 2), domain, font=mark, fill=FAINT, anchor="ra")
    eb = font("Mono-Medium", 22)
    d.text((x, PAD), wrap(eyebrow, eb, tw - int(mark.getlength(domain)) - 24, 1)[0], font=eb, fill=MUTED)
    for size in (64, 54, 46):
        tf = font("Sans-SemiBold", size)
        tl = wrap(title, tf, tw, 3)
        if not tl[-1].endswith("…"):
            break
    y = PAD + 48
    for line in tl:
        d.text((x, y), line, font=tf, fill=INK)
        y += round(size * 1.08)
    y += 16
    df = font("Sans-Regular", 28)
    room = max(1, (H - 130 - y) // 38)
    for line in wrap(desc, df, tw, min(room, 5)):
        d.text((x, y), line, font=df, fill=MUTED)
        y += 38
    d.line([(x, H - 98), (W - PAD, H - 98)], fill=RULE, width=2)
    ff = font("Mono-Regular", 22)
    d.text((x, H - 80), wrap(foot, ff, tw, 1)[0], font=ff, fill=MUTED)
    out = io.BytesIO()
    im.quantize(colors=32, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(out, format="PNG")   # five tones and type edges: 32 colours keep it exact enough and a third the size
    return out.getvalue()


def images(w) -> dict[str, bytes]:
    """Every link-preview image for the site built by web.Web `w`."""
    def png(i):
        k = w.icon_id(i)
        return w.built[f"visual/icons/{k}@4x.png"] if k else None

    def pngs(ids):
        return [p for p in (png(i) for i in ids) if p]

    def name(i):
        return w.by_id[i].data.get("name", i)

    live = lambda t: [e for e in w.ents.get(t, []) if not e.data.get("deprecated")]
    mechs = sorted(live("mechanic"), key=lambda e: (-w.derived.get(e.id, {}).get("prevalence", 0), e.data["name"]))
    top = pngs(e.id for e in mechs)
    counts = {t: len(live(t)) for t in ("game", "mechanic", "technique", "opportunity", "source")}
    meta = w.meta
    outs = {"web/og/site.png": card("the paper · v" + str(meta["version"]), meta["title"], meta["subtitle"] + ".",
                                    f'{counts["game"]} games · {counts["mechanic"]} mechanics · {counts["technique"]} techniques', top)}
    index = {
        "game": ("Every game is a set of parts", "Each catalogued simulation game drawn as the mechanics it is built from.", f'{counts["game"]} games', top),
        "mechanic": ("Mechanics", "Every mechanic as its icon, grouped by family and ordered by how many games use it.", f'{counts["mechanic"]} mechanics in 21 families', top),
        "technique": ("Techniques", "Every mathematical, AI, ML, and LLM technique in the set, with its maturity in games.", f'{counts["technique"]} techniques',
                      pngs(e.id for e in sorted(live("technique"), key=lambda e: e.id))),
        "opportunity": ("What could be built, and when", "Every design opportunity by horizon, with the mechanics it builds on and the risks it carries.",
                        f'{counts["opportunity"]} opportunities', pngs(f"horizon-{h}" for h in ("now", "1-2y", "3-5y", "5y-plus"))),
        "source": ("Sources", "Every source cited by a record or by the paper.", f'{counts["source"]} sources', top),
    }
    for t, (title, desc, foot, icons) in index.items():
        outs[f"web/og/{t}.png"] = card(f"{t} index", title, desc, foot, icons)
    shown = []
    for v in w.episodes + w.shorts:
        shown += [i for i in v["shows"] if i not in shown]
    ne, ns = len(w.episodes), len(w.shorts)
    outs["web/og/watch.png"] = card("watch", f"The book in {ne} episodes, and {ns} one-minute findings" if ne else f"{ns} findings, under a minute each",
                                    "Videos drawn from the dataset's records: episodes that follow the book, and shorts that each state one finding.",
                                    f"{ne} episodes · {ns} shorts", pngs(shown))
    for ep in w.episodes:
        chapters = " and ".join(str(c) for c in ep["covers"])
        n = len({i for sc in ep["scenes"] for i in sc["shows"]})
        outs[f"web/og/watch/{ep['key']}.png"] = card(f"episode {ep['n']} · chapter{'s' if len(ep['covers']) > 1 else ''} {chapters}", ep["title"],
                                                     ep["summary"],
                                                     f"{w.mmss(ep['seconds'])} · {len(ep['scenes'])} scenes · {n} records on screen", pngs(ep["shows"][:16]))
    outs["web/og/book.png"] = card("the book", "The Grammar of Simulation, as a book", "Thirteen chapters on the parts simulation games share, rendered from the dataset.",
                                   "13 chapters · glossary · catalog", top)
    for e in mechs:
        der = w.derived.get(e.id, {})
        outs[f"web/og/mechanic/{e.id}.png"] = card(f"mechanic · {e.id}", e.data["name"], e.data.get("summary", ""),
                                                   f'used by {der.get("prevalence", 0)} games · first seen {der.get("earliest_year") or "n/a"}', pngs([e.id]))
    for e in live("game"):
        ms = sorted(e.data.get("mechanics", []), key=lambda m: (m.get("role") != "core", name(m["id"]) if m["id"] in w.by_id else m["id"]))
        outs[f"web/og/game/{e.id}.png"] = card(f"game · {e.id}", e.data["name"], e.data.get("summary", ""),
                                               f'{len(ms)} parts · {e.data.get("year", "")} · {w.term("subgenre", e.data.get("subgenre")).lower()}',
                                               pngs(m["id"] for m in ms[:16]))
    for e in live("technique"):
        outs[f"web/og/technique/{e.id}.png"] = card(f"technique · {e.id}", e.data["name"], e.data.get("summary", ""),
                                                    f'{w.term("technique_maturity", e.data.get("maturity")).lower()} · {e.data.get("year", "")} · '
                                                    f'{w.derived.get(e.id, {}).get("affects_count", 0)} mechanics affected', pngs([e.id]))
    for e in live("opportunity"):
        inv = [i for i in e.data.get("involves", []) if i in w.by_id]
        outs[f"web/og/opportunity/{e.id}.png"] = card(f"opportunity · {e.id}", e.data["name"], e.data.get("summary", ""),
                                                      f'horizon {w.term("horizon", e.data.get("horizon")).lower()} · impact {e.data.get("impact")} of 5',
                                                      pngs(inv[:16]))
    for stem in w.chapters:
        if stem == "00-contents":
            continue
        title = re.search(r"^# (.*)$", w.built[f"book/{stem}.md"], re.M).group(1)
        ms = [i for i, rs in w.book_refs.items() if any(r[0] == stem for r in rs) and w.by_id[i].type == "mechanic"]
        ms.sort(key=lambda i: -w.derived.get(i, {}).get("prevalence", 0))
        outs[f"web/og/book/{stem}.png"] = card(f"the book · {stem}", title, "A chapter of The Grammar of Simulation, rendered from the dataset.",
                                               f"{len(ms)} mechanics in this chapter" if ms else "the book", pngs(ms[:16]) or top)
    return outs
