"""Project the dataset into a static website (dist/web), styled with Register (web/register.css).

Pages:
  index.html                         the paper, rendered from report/src with interactive figures, and the grammar mosaic
  <type>/index.html                  one index per entity type: mechanics as icon tiles, games as parts boards, opportunities
                                     by horizon, each with its sortable table as the plain-text twin; techniques and sources a table
  <type>/<id>/index.html             one page per entity, with its icon, its parts board (games), the shorts that show it,
                                     and where the book, the episodes and the shorts mention it
  book/index.html, book/<chapter>/   the book (book/src as rendered by this build), one chapter a page, each with its episode
  watch/index.html                   the published episodes and shorts (media/published.yaml)
  watch/episode-NN/                  one page per episode: its summary, the player and its scenes, the records it names as cards
                                     with the times each is on screen, and the transcript behind a disclosure
  find/index.html                    every chapter, episode, short, record and source on one filterable page
  data/index.html                    downloads, provenance log, contract
  og/<type>/<id>.png, og/*.png       a link-preview image per page (scripts/og.py)
  paper.md, references.bib, manifest.json, figures/*.svg, llms.txt, CNAME, robots.txt, sitemap.xml, 404.html, assets/*

Everything here is a deterministic function of data/, report/, vocab/, schema/, book/, media/, and web/; icons come from
the build's dist/visual (ADR-0006). The video files are not: the Pages workflow fetches the ones media/published.yaml lists
from their GitHub release and checks each sha256. Pages work without JavaScript; assets/simgrammar.js only adds interaction.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path

from markdown_it import MarkdownIt

from lib import ROOT, counted, get_path, narration_digest, read_yaml, vocab_terms
from report_render import GITHUB_HANDLE_RE, VOCAB_COLUMNS, _decl_rows, _fmt, link_label, render, table_value

WEB_SRC = ROOT / "web"
# The primary nav leads with the subject; the paper is one tab among them. Sources, find, and how the atlas is made sit in the utility nav.
# Readers meet opportunity records as bets (the home page and the book call them that); the URLs and the paper keep the record type's name.
READER_NAME = {"opportunity": ("bet", "bets")}
NAV = [("game", "Games", "game/"), ("mechanic", "Mechanics", "mechanic/"), ("technique", "Techniques", "technique/"), ("opportunity", "Bets", "opportunity/"),
       ("watch", "Watch", "watch/"), ("book", "Book", "book/"), ("paper", "Paper", "paper/")]
UTILITY = [("find", "find", "find/"), ("source", "sources", "source/"), ("about", "about", "about/")]
FAVICON = "free-placement"   # the icon the browser tab shows
# The front page's lead, also its link-preview description: what the atlas is for a reader, where the paper's subtitle says it for a scholar.
LEAD = ("Every simulation game is assembled from a shared set of parts: production chains, needs, markets, weather, raids. Naming the parts shows "
        "why games feel alike, which combinations no one has built yet, and where AI can change how a game plays.")
STATE = {"asserted": "optional", "sourced": "waiting", "verified": "done", "contested": "blocked"}
SKIP_FACTS = {"id", "type", "name", "aliases", "summary", "status", "provenance", "sources", "claims", "deprecated", "key_results", "falsifiable_signal",
              "assertions", "ratings", "store_ids", "archived"}
OUTCOME_STATE = {"confirmed": "done", "refuted": "stop", "ambiguous": "blocked", "withdrawn": "superseded"}
STORE_URL = {"steam": "https://store.steampowered.com/app/{}/", "igdb": "https://www.igdb.com/games/{}", "wikidata": "https://www.wikidata.org/wiki/{}"}
LONG = {"game": ["core_loop", "design_notes"], "mechanic": ["definition", "player_experience"], "technique": ["mechanism"],
        "opportunity": ["thesis", "design_sketch", "validation_experiment"], "source": ["notes"]}
LISTS = {"mechanic": ["design_levers", "failure_modes", "dynamics", "open_questions"], "technique": ["limitations"], "opportunity": ["key_risks"]}


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def host(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else url).removeprefix("www.")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class Web:
    def __init__(self, ents, edges, analysis, vocabs, registry, schemas, ctx, manifest, meta, built=None):
        self.ents, self.edges, self.analysis, self.vocabs = ents, edges, analysis, vocabs
        self.registry, self.schemas, self.ctx, self.manifest, self.meta = registry, schemas, ctx, manifest, meta
        self.built = built or {}
        self.icons = {k[len("visual/icons/"):-len("@4x.png")] for k in self.built if k.startswith("visual/icons/") and k.endswith("@4x.png") and ".accent@" not in k}
        self.by_id = ctx.by_id
        self.published = read_yaml(ROOT / "media" / "published.yaml") if (ROOT / "media" / "published.yaml").exists() else {}
        self.shorts, self.shorts_of = [], defaultdict(list)
        for sh in self.published.get("shorts", []):
            md = self.built.get(f"media/shorts/{sh['script']}", "")
            title = re.search(r"^# Short \d+\. (.*)$", md, re.M)
            unknown = [i for i in sh.get("shows", []) if i not in self.by_id]
            if not md or unknown:
                raise SystemExit(f"media/published.yaml: {sh['key']} names a script this build did not render or unknown records {unknown}")
            frm = re.search(r"\(chapter (\d+), episode (\d+)\)", md)
            sh = {**sh, "n": int(sh["key"].rsplit("-", 1)[1]), "title": title.group(1) if title else sh["key"],
                  "voice": re.findall(r"^\*\*Voice\.\*\* (.*)$", md, re.M),
                  "chapter": int(frm.group(1)) if frm else None, "episode": int(frm.group(2)) if frm else None}
            self.shorts.append(sh)
            for i in sh["shows"]:
                self.shorts_of[i].append(sh)
        self.episodes, self.moments = [], defaultdict(list)
        for ep in self.published.get("episodes", []):
            md = self.built.get(f"media/episodes/{ep['script']}", "")
            title = re.search(r"^# Episode \d+\. (.*)$", md, re.M)
            summary = re.search(r"^\*\*Summary\.\*\* (.*)$", md, re.M)
            covers = re.search(r"Covers book chapters? ([\d, and]+)\.", md)
            said = self.episode_voice(md)
            unknown = [i for i in ep.get("shows", []) + [i for sc in ep["scenes"] for i in sc["shows"]] if i not in self.by_id]
            missing = [sc["name"] for sc in ep["scenes"] if sc["name"] not in said]
            if not title or not summary or not covers or unknown or missing:
                raise SystemExit(f"media/published.yaml: {ep['key']} names a script this build did not render or one with no **Summary.** line, "
                                 f"scenes it lacks {missing}, or unknown records {unknown}")
            scenes = []
            for k, sc in enumerate(ep["scenes"]):
                if said[sc["name"]]:   # the title card has no narration and is not a scene to jump to
                    scenes.append({**sc, "end": ep["scenes"][k + 1]["start"] if k + 1 < len(ep["scenes"]) else ep["seconds"], "voice": said[sc["name"]],
                                   "changed": narration_digest(" ".join(said[sc["name"]])) != sc["said"]})
            ep = {**ep, "n": int(ep["key"].rsplit("-", 1)[1]), "title": title.group(1), "summary": summary.group(1).strip(), "covers": [int(x) for x in re.findall(r"\d+", covers.group(1))], "scenes": scenes,
                  "tracks": self.subtitle_tracks(ep, md, scenes)}
            self.episodes.append(ep)
            for sc in scenes:
                for i, t in sorted(sc["shows"].items(), key=lambda kv: (kv[1], kv[0])):
                    self.moments[i].append((ep, t, sc["name"]))
        # the sources the videos cite: an episode's by scene, a short's anywhere in it
        self.ep_cites, self.short_cites = defaultdict(list), defaultdict(list)
        for ep in self.episodes:
            for sc in ep["scenes"]:
                for sid in dict.fromkeys(re.findall(r"#ref-([a-z0-9-]+)", " ".join(sc["voice"]))):
                    if sid in self.by_id:
                        self.ep_cites[sid].append((ep, sc["start"], sc["name"]))
        for sh in self.shorts:
            for sid in dict.fromkeys(re.findall(r"#ref-([a-z0-9-]+)", " ".join(sh["voice"]))):
                if sid in self.by_id:
                    self.short_cites[sid].append(sh)
        self.paper_refs = defaultdict(list)   # filled by paper(), which build_web runs before the record pages
        self._words = {}
        self.chapters = sorted(k[len("book/"):-3] for k in self.built if re.fullmatch(r"book/\d\d-[a-z0-9-]+\.md", k))
        self.chapter_of = {int(st[:2]): st for st in self.chapters if re.match(r"(0[1-9]|1[0-9])-", st)}
        self.book_refs = self.find_book_refs()
        self.site = meta["site"]
        self.by_id = ctx.by_id
        self.derived = analysis["derived"]
        self.short = manifest["dataset_sha256"][:8]
        self.types = [t for t, s in registry["types"].items() if not s.get("meta")]
        self.props = {t: schemas[Path(registry["types"][t]["schema"]).name]["properties"] for t in self.types}
        self.edges_out, self.edges_in = defaultdict(list), defaultdict(list)
        for ed in edges:
            self.edges_out[ed.source].append(ed)
            self.edges_in[ed.target].append(ed)
        self.vt = {}
        self.runs = {e.id: e for e in ents.get("run", [])}

    SUBTITLE_LABELS = {"ja": "日本語"}   # the languages media/subtitles/ holds, by the label a player's menu shows

    def subtitle_tracks(self, ep, md, voiced):
        """An episode's subtitle tracks, [(lang, label, path under the site root, WebVTT)], timed from its render as
        media/published.yaml records it (subtitles.vtt). A track is left out, with a note on the build's output, when its
        cues do not fit the render, or when a scene's narration has changed since the render (its cues carry the new wording)."""
        import sys
        import subtitles
        out = []
        for lang, label in self.SUBTITLE_LABELS.items():
            src = self.built.get(f"media/subtitles/{lang}/{ep['script']}")
            if not src:
                continue
            text, problems = subtitles.vtt(ep["scenes"], ep["seconds"], subtitles.scene_numbers(md), src)
            problems += [f"scene '{sc['name']}' is worded differently from the render" for sc in voiced if sc["changed"]]
            if problems:
                print(f"web: {ep['key']} {lang} subtitles not offered: {'; '.join(problems)}", file=sys.stderr)
                continue
            out.append((lang, label, f"media/subtitles/{lang}/{ep['key']}.vtt", text))
        return out

    # ------------------------------------------------------------------ helpers
    def term(self, vname, t):
        if vname not in self.vt:
            self.vt[vname] = vocab_terms(self.vocabs, vname)
        return self.vt[vname].get(str(t), {}).get("label", str(t))

    def vocab_of(self, t, field):
        p = self.props[t].get(field) or {}
        return p.get("x-vocab") or (p.get("items") or {}).get("x-vocab")

    def link(self, eid, base, text=None):
        e = self.by_id.get(eid)
        if not e:
            return esc(text or eid)
        return f'<a href="{base}{e.type}/{eid}/" data-internal>{esc(text or e.data.get("name", eid))}</a>'

    def icon_id(self, eid):
        """The icon that stands for a record: its own, else a technique's category icon (as the video frames resolve it)."""
        if eid in self.icons:
            return eid
        e = self.by_id.get(eid)
        if e and e.type == "technique" and e.data.get("category") in self.icons:
            return e.data["category"]
        return None

    def icon(self, eid, base, size=48, alt=""):
        """A dithered icon at 24, 48 or 96 css px, so each of its 48 dither pixels lands on whole device pixels."""
        i = self.icon_id(eid)
        return f'<img data-icon src="{base}assets/icons/{i}.png" width="{size}" height="{size}" alt="{esc(alt)}" loading="lazy">' if i else ""

    def chip(self, eid, base):
        e = self.by_id.get(eid)
        if not e:
            return f'<span class="chip">{esc(eid)}</span>'
        ic = self.icon(eid, base, 24)
        return (f'<a class="chip" data-style="{"icon" if ic else "name"}" href="{base}{e.type}/{eid}/" data-internal>'
                f'{ic}{esc(e.data.get("name", eid))}</a>')

    def chips(self, ids, base):
        return '<div class="cluster" data-gap="chips">' + "".join(self.chip(x, base) for x in ids) + "</div>"

    def gh(self, path):
        return f'{self.site["repo"]}/blob/main/{path}'

    @staticmethod
    def dl(path, base):
        """Generated projections are not committed; the Pages workflow publishes them under /dist/ beside the site."""
        return f"{base}dist/{path}"

    def page(self, *, title, desc, body, depth, nav, path, image="og/site.png"):
        base = "../" * depth
        fam = "".join(f'<li><a href="{esc(u)}">{esc(n)}</a></li>' for n, u in self.site.get("family", []))
        fam += f'<li><a href="{base or "./"}" aria-current="true" data-internal>simgrammar</a></li>'
        navh, utility = ("".join(f'<a href="{base}{href}"{" aria-current=" + chr(34) + "page" + chr(34) if key == nav else ""} data-internal>{label}</a>'
                                 for key, label, href in links) for links in (NAV, UTILITY))
        url = self.site["url"] + path
        if 'data-person="' in body:
            body += f'<script type="application/json" id="people">{self.people_json()}</script>'
        return f"""<!doctype html>
<html lang="en" data-theme="{esc(self.site.get('theme', 'neutral'))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(self.site['url'] + image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="{base}assets/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&amp;family=IBM+Plex+Mono:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}assets/register.css">
<link rel="alternate" type="text/markdown" href="{base}paper.md" title="The paper as markdown">
<script src="{base}assets/simgrammar.js" defer></script>
</head>
<body>
<a class="skip-link" href="#content">Skip to content</a>
<div class="family shell" aria-label="Site family"><ul>{fam}</ul><span>simulation games, part by part</span></div>
<header class="topbar shell">
  <a class="brand" href="{base or './'}" data-internal>simgrammar <small>the grammar of simulation</small></a>
  <input type="checkbox" id="menu" class="menu-toggle"><label for="menu" class="menu-label">menu</label>
  <nav class="nav" aria-label="Primary">{navh}</nav>
  <nav class="nav-utility" aria-label="Utility">{utility}</nav>
</header>
<main id="content" class="shell">
{body}
<footer class="site-footer"><span>paper v{esc(self.meta['version'])} · dataset {self.short}</span><span><a href="{base}about/" data-internal>how this is made</a> · <a href="{esc(self.site['repo'])}">github</a></span></footer>
</main>
</body>
</html>
"""

    # ------------------------------------------------------------------ tables
    def cell(self, col, v, base, link_cols, cap=None):
        if col == "links" and isinstance(v, list):   # a contributor's profile links
            return " · ".join(f'<a href="{esc(u)}">{esc(link_label(u))}</a>' for u in v)
        if isinstance(v, list):
            if col in link_cols:
                shown = v[:cap] if cap else v
                more = len(v) - len(shown)
                return ", ".join(self.link(x, base) if x in self.by_id else esc(x) for x in shown) + (f", and {more} more" if more else "")
            return esc(", ".join(_fmt(x) for x in v))
        if col in link_cols and isinstance(v, str) and v in self.by_id:
            return self.link(v, base)
        if col in VOCAB_COLUMNS and isinstance(v, str):
            return esc(self.term(VOCAB_COLUMNS[col], v))
        if col == "github" and isinstance(v, str) and GITHUB_HANDLE_RE.match(v):
            return f'<a href="https://github.com/{esc(v)}">{esc(v)}</a>'
        return esc(_fmt(v))

    def table(self, columns, headers, rows, base, link_cols=(), caption=None, cap=None, name=None):
        th = "".join(f'<th{" class=" + chr(34) + "num" + chr(34) if self._numeric(rows, c) else ""}>{esc(h)}</th>' for c, h in zip(columns, headers))
        trs = []
        for r in rows:
            tds = []
            for c in columns:
                v = r.get(c) if isinstance(r, dict) else None
                cls = ' class="num"' if self._numeric(rows, c) else ""
                if name == "contributors" and c == "contributor":   # the name opens the contributor's card
                    tds.append(f'<td><a href="https://github.com/{esc(r["github"])}" data-person="{esc(r["github"])}">{esc(v)}</a></td>')
                    continue
                tds.append(f"<td{cls}>{self.cell(c, v, base, set(link_cols), cap)}</td>")
            trs.append("<tr>" + "".join(tds) + "</tr>")
        t = (f'<div class="table-wrap"><table class="data" data-style="dense" data-sortable{" data-name=" + chr(34) + esc(name) + chr(34) if name else ""}>'
             f"<thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>")
        cap_html = f'<p class="small muted">{esc(caption)}</p>' if caption else ""
        if len(rows) > 40:
            return f'<details class="disclosure"><summary>table · {len(rows)} rows{" · " + esc(name) if name else ""}</summary>{t}{cap_html}</details>'
        return t + cap_html

    @staticmethod
    def _numeric(rows, c):
        vals = [r.get(c) for r in rows if isinstance(r, dict) and r.get(c) is not None]
        return bool(vals) and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals)

    def report_table(self, name, base):
        ctx = self.ctx
        if name in ctx.decl_tables:
            spec = ctx.decl_tables[name]
            if spec.get("kind") == "count-by":
                from collections import Counter
                c = Counter()
                for e in ctx.ents.get(spec["entity"], []):
                    if e.data.get("deprecated"):
                        continue
                    v = get_path(e.data, spec["field"])
                    for x in (v if isinstance(v, list) else [v]):
                        if x is not None:
                            c[x] += 1
                rows = [{"term": self.term(spec["vocab"], k) if spec.get("vocab") else k, "count": n} for k, n in sorted(c.items(), key=lambda x: (-x[1], str(x[0])))]
                return self.table(["term", "count"], [spec.get("label", spec["field"]), self.registry["types"][spec["entity"]]["plural"]], rows, base, name=name)
            cols = spec["columns"]
            paths = [c["path"] if isinstance(c, dict) else c for c in cols]
            heads = [c.get("label") if isinstance(c, dict) else c.split(".")[-1].replace("_", " ") for c in cols]
            ent_t = spec["entity"]
            rows = []
            for r in _decl_rows(ctx, spec):
                row = {}
                for p in paths:
                    v = get_path(r, p)
                    vn = self.vocab_of(ent_t, p) if "." not in p else None
                    if p == "name":
                        v = r["id"]
                    elif vn and v is not None:
                        v = [self.term(vn, x) for x in v] if isinstance(v, list) else self.term(vn, v)
                    row[p] = v
                rows.append(row)
            return self.table(paths, heads, rows, base, link_cols={"name"}, caption=spec.get("caption"), name=name)
        t = self.analysis["tables"].get(name)
        if t is None:
            return None
        links = set(t.get("link_columns", []))
        rows = [{c: v if c in links else table_value(ctx, name, c, v) for c, v in r.items()} for r in t["rows"]]
        return self.table(t["columns"], [c.replace("_", " ") for c in t["columns"]], rows, base, link_cols=t.get("link_columns", []),
                          caption=t["description"], cap=t.get("max_links"), name=name)

    # ------------------------------------------------------------------ figures
    def figure_static(self, name, n):
        f = self.analysis["figures"][name]
        svg = re.sub(r"^<svg ([^>]*?)width='\d+' height='\d+' style=\"", "<svg class=\"plot\" \\1style=\"width:100%;max-width:none;height:auto;", f["svg"], count=1)
        svg = svg.replace("width:100%;max-width:none;", "width:100%;max-width:none;min-width:480px;", 1)
        title = {"legibility-vs-emergence": "Legibility against emergence potential", "exposure-by-family": "Technique exposure by family",
                 "mechanic-accumulation": "Mechanics by first appearance"}.get(name, name)
        return (f'<figure class="chart" id="fig-{name}"><div class="chart-head"><span><b>figure {n}</b> · {esc(title)}</span><span>{esc(name)}.svg</span></div>'
                f'<div class="chart-body"><div class="table-wrap" style="border-top:0">{svg}</div></div><figcaption class="chart-caption">{esc(f["caption"])} '
                f'<span class="run">source · dist/analysis/figures/{esc(name)}.svg · dataset {self.short}</span></figcaption></figure>')

    @staticmethod
    def fluid(svg):
        """Inline SVGs scale to the column: drop the fixed width and height the standalone file keeps."""
        return re.sub(r'^(<svg[^>]*?) width="\d+" height="\d+"', r"\1", svg, count=1).replace("max-width:100%;height:auto", "width:100%;max-width:none;height:auto", 1)

    def scroller(self, v):
        """On wide screens the figure fills the column. Below its minimum width it keeps readable text and scrolls
        sideways inside .table-wrap, the one scroll container Register allows."""
        svg = self.fluid(v["svg"]).replace("width:100%;max-width:none;", f"width:100%;max-width:none;min-width:{v.get('min_width', 0)}px;", 1)
        hint = '<p class="small faint show-sm">swipe sideways to see the whole figure; the table below holds every value</p>'
        wrap = f'<div class="table-wrap" style="border-top:0">{svg}</div>'
        if v.get("aside"):
            return f'<div class="split"><div style="min-width:0">{wrap}{hint}</div><div style="min-width:0">{v["aside"]}</div></div>'
        return wrap + hint

    def figure_viz(self, name, n, base):
        v = self.analysis["vizzes"][name]
        tw = v["twin"]
        if "table" in tw:
            twin = self.report_table(tw["table"], base) or ""
            nrows = len(self.analysis["tables"][tw["table"]]["rows"])
        else:
            twin = self.table(tw["columns"], [c.replace("_", " ") for c in tw["columns"]], tw["rows"], base, link_cols=tw.get("link_columns", []), cap=8)
            nrows = len(tw["rows"])
        if twin.startswith("<details"):
            twin = re.sub(r"^<details class=\"disclosure\"><summary>.*?</summary>", "", twin)[: -len("</details>")]
        return (f'<figure class="chart" id="fig-{name}" data-viz="{name}" aria-describedby="cap-{name}">'
                f'<div class="chart-head"><span><b>figure {n}</b> · {esc(v["title"])}</span><span>{esc(v["head"])}</span></div>'
                f'<div class="controls" data-viz-controls hidden>{v["controls"]}</div>'
                f'<div class="chart-body">{self.scroller(v)}</div>{v.get("legend", "")}'
                f'<p class="live" data-readout aria-live="polite" hidden></p>'
                f'<p class="chart-caption" id="cap-{name}">{esc(v["caption"])} <span class="run">source · {esc(v["source"])} · dataset {self.short}</span></p>'
                f'<details class="disclosure"><summary>plain-text twin · {counted(nrows, "row")}</summary><p class="small muted">{esc(tw["note"])}</p>{twin}</details>'
                f'{v["data"]}</figure>')

    # ------------------------------------------------------------------ paper
    def paper(self):
        """The paper, at paper/: process is at home here, so its header keeps the version, dataset, and contract."""
        ctx = self.ctx
        ctx.web_base = "../"
        ctx.citations = []
        md = MarkdownIt("commonmark", {"html": True}).enable("table")
        parts = []
        for p in sorted((ROOT / "report" / "src").glob("*.md")):
            txt, _ = render(p.read_text(encoding="utf-8"), ctx, "web")
            parts.append(md.render(txt))
        body = "\n".join(parts)
        toc = []

        def head(m):
            lvl, inner = m.group(1), m.group(2)
            plain = re.sub(r"<[^>]+>", "", inner)
            hid = slug(plain)
            if lvl == "2":
                toc.append((hid, plain))
                return f'<hr class="rule" data-style="wedge"><h2 id="{hid}">{inner}</h2>'
            return f'<h{lvl} id="{hid}">{inner}</h{lvl}>'
        body = re.sub(r"<h([23])>(.*?)</h\1>", head, body)
        counter = {"n": 0}

        def place(m):
            kind, name = m.group(1), m.group(2)
            if kind == "TABLE":
                return self.report_table(name, "../") or ""
            counter["n"] += 1
            return self.figure_static(name, counter["n"]) if kind == "FIGURE" else self.figure_viz(name, counter["n"], "../")
        body = body.replace("<table>", '<div class="table-wrap"><table class="data" data-style="dense">').replace("</table>", "</table></div>")
        body = re.sub(r"<!--(TABLE|FIGURE|VIZ):([a-z0-9-]+)-->", place, body)
        self.paper_refs.clear()
        for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>(.*?)(?=<h2 id=|\Z)', body, re.S):
            hid, title, sec = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)), m.group(3)
            for i in dict.fromkeys(re.findall(r'href="(?:\.\./)?(?:game|mechanic|technique|opportunity|source)/([a-z0-9-]+)/"', sec)
                                   + re.findall(r'href="#ref-([a-z0-9-]+)"', sec)):
                if i in self.by_id:
                    self.paper_refs[i].append((hid, title))
        body = body.replace('<hr class="rule" data-style="wedge">', "", 1)
        # references
        refs = []
        for i, sid in enumerate(ctx.citations, start=1):
            s = self.by_id[sid].data
            au = ", ".join(s.get("authors", [])[:6]) + (" et al." if len(s.get("authors", [])) > 6 else "")
            loc = s.get("url") or (f"https://doi.org/{s['doi']}" if s.get("doi") else "") or (f"https://arxiv.org/abs/{s['arxiv']}" if s.get("arxiv") else "")
            refs.append(f'<div class="row" id="ref-{sid}"><div class="id" data-ref="{i}"></div><div><span class="who">{esc(au)}</span> ({esc(s["date"])}). '
                        f'<a href="../source/{sid}/" data-internal>{esc(s["name"])}</a>. <span class="venue">{esc(s.get("venue", ""))}</span>'
                        f'<span class="ids">{f"<a href={chr(34)}{esc(loc)}{chr(34)}>{esc(host(loc))}</a>" if loc else ""}</span></div></div>')
        toc += [("references", "References"), ("cite", "Cite"), ("receipt", "Build receipt")]
        meta, man = self.meta, self.manifest
        counts = self.counts()
        tocs = "".join(f'<a href="#{hid}" data-internal>{esc(t)}</a>' for hid, t in toc)
        authors = ", ".join(self.analysis["byline"])
        authors_html = self.byline_html("../")
        # BibTeX names: "Last, First" for a personal name, braces for a one-word handle or the group name so they stay whole
        bib_names = " and ".join(f"{a.rsplit(' ', 1)[1]}, {a.rsplit(' ', 1)[0]}" if " " in a and a != "SimGrammar contributors" else f"{{{a}}}"
                                 for a in self.analysis["byline"])
        bib = (f"@misc{{nakajima{meta['date'][:4]}grammar,\n  title = {{{meta['title']}: {meta['subtitle']}}},\n  author = {{{bib_names}}},\n"
               f"  year = {{{meta['date'][:4]}}},\n  version = {{{meta['version']}}},\n  url = {{{self.site['url']}paper/}},\n  note = {{Dataset {self.short}; full sha256 in manifest.json}}\n}}")
        nruns = len(self.ents.get("run", []))
        header = f"""<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>paper</li></ol></nav>
<div class="page-header corners">
  <p class="eyebrow"><span class="id">v{esc(meta['version'])}</span> <span>{esc(meta['date'])}</span> <span>dataset <b>{self.short}</b></span> <span>contract {esc(man['contract_version'])}</span></p>
  <h1>{esc(meta['title'])}</h1>
  <p class="dek">{esc(meta['subtitle'])}.</p>
  <div class="meta"><span><b>{authors_html}</b></span>{"".join(f"<span>{counted(counts[t], t)}</span>" for t in ("game", "mechanic", "technique", "opportunity", "source"))}<span>{counted(man['edges'], "typed edge")}</span><span>{counted(nruns, "research run")}</span></div>
  <div class="actions"><a class="btn" href="#abstract" data-internal>Read the paper</a><a class="btn" data-style="ghost" href="../about/" data-internal>How it is made</a><a class="btn" data-style="ghost" href="{esc(self.site['repo'])}">Contribute on GitHub</a></div>
  <div class="twins"><b>this paper as</b><a href="../paper.md" data-internal>markdown</a><a href="../references.bib" data-internal>bibtex</a><a href="../manifest.json" data-internal>manifest json</a><a href="../llms.txt" data-internal>llms.txt</a></div>
</div>"""
        main = f"""<div class="sidebar">
<aside class="hide-md sticky"><nav class="toc" aria-label="Contents"><span class="toc-head">contents</span>{tocs}</nav></aside>
<article class="prose" style="min-width:0">
<details class="disclosure show-md" data-toc-mobile><summary>contents · {len(toc)} sections</summary><nav class="toc" aria-label="Contents">{tocs}</nav></details>
{body}
<section class="section" id="references"><div class="section-line"><h2>references <span>· {len(refs)} cited in the text</span></h2><a href="../source/" data-internal>all {counted(counts['source'], "source")}</a></div>
<div class="register" data-kind="refs">{''.join(refs)}</div></section>
<section class="section cite" id="cite"><div class="section-line"><h2>cite</h2><span>bibtex</span></div>
<div class="cite-line"><span class="chip">{esc(authors)}</span><span class="chip">{esc(meta['date'][:4])}</span><span class="chip">v{esc(meta['version'])}</span><span class="chip">dataset {self.short}</span></div>
<div class="prompt"><div class="copy-row"><span>bibtex</span><span>{esc(meta['title'].lower())} · v{esc(meta['version'])}</span></div><pre>{esc(bib)}</pre></div></section>
<section class="section" id="receipt"><div class="section-line"><h2>build receipt <span>· reproduce this page</span></h2><span>python scripts/build.py</span></div>
<dl class="receipt" data-size="wide"><dt>dataset</dt><dd><span class="hash" data-prefix="sha256:">{man['dataset_sha256']}</span></dd>
<dt>contract</dt><dd>{esc(man['contract_version'])} · <a href="{esc(self.gh('CONTRACT.md'))}">CONTRACT.md</a></dd>
<dt>entities</dt><dd>{', '.join(f'{n} {t}' for t, n in man['counts'].items())}</dd>
<dt>edges</dt><dd>{man['edges']}</dd>
<dt>generator</dt><dd>{esc(man['generator'])} · scripts/web.py · scripts/viz.py</dd>
<dt>check</dt><dd><code>make check</code> fails if any page differs from a fresh build</dd></dl>
<p><span class="endmark"></span></p></section>
</article></div>"""
        return self.page(title=f"The paper · {meta['title']} · simgrammar", desc=meta["subtitle"], body=header + main, depth=1, nav="paper", path="paper/", image="og/paper.png")

    def counts(self):
        return {t: sum(1 for e in self.ents.get(t, []) if not e.data.get("deprecated")) for t in self.types}

    # ------------------------------------------------------------------ home
    def paper_anchor(self, sec):
        """The id of the paper heading numbered `sec` ("5.6"), as paper() gives it."""
        for p in sorted((ROOT / "report" / "src").glob("*.md")):
            m = re.search(rf"^#+ ({re.escape(sec)} .+)$", p.read_text(encoding="utf-8"), re.M)
            if m:
                return slug(m.group(1))
        raise SystemExit(f"web.py: no paper section {sec}")

    def section_link(self, title, inner, href, label):
        """A section whose line ends in a link onward, as the paper's references end in "all sources"."""
        return (f'<section class="section" id="{slug(title)}"><div class="section-line"><h2>{esc(title)}</h2><a href="{href}" data-internal>{esc(label)}</a></div>'
                f"{inner}</section>")

    def board(self, ids, base, line=None):
        """Record cards as the episode pages draw them: icon, a short label, the name, and the summary."""
        rows = "".join(f'<div class="row"><div class="id"><a href="{base}{self.by_id[i].type}/{i}/" data-internal>{self.card_icon(self.by_id[i], base)}</a></div><div>'
                       f'<small>{esc((line or self.card_line)(self.by_id[i]))}</small><h3>{self.link(i, base)}</h3><p>{esc(self.by_id[i].data.get("summary", ""))}</p></div></div>'
                       for i in ids)
        return f'<div class="register" data-kind="board" data-size="sm">{rows}</div>'

    def home(self):
        """The front door: what the atlas is and why it matters, then a way into every part of it. The paper has its own tab."""
        base, meta, st = "", self.meta, self.analysis["stats"]
        counts = self.counts()
        findings = [
            (f'{st["pct_uses_since_2010_on_pre2001"]:.0f}%', "of the parts in games since 2010 were already in a game by 2000", "5.2"),
            # the paper's wording: legibility falls as emergence potential, the unscripted variety a mechanic generates, rises
            (f'{st["rho_legibility_emergence_potential"]}', "mechanics that generate more unscripted variety are rated harder to read (ρ)", "5.6"),
            # exposure is zero exactly when no technique record has an affects edge to the mechanic
            (f'{st["pct_uses_on_zero_exposure"]:.0f}%', "of mechanic uses fall on mechanics that no technique in this dataset is linked to", "8.2"),
            (f'{st["n_technique_runtime_breaks"]} of {st["n_technique_runtime"]}', "AI techniques that run during play break exact replay", "6.4"),
        ]
        # register.css pads every number but the first on its left, so when the strip wraps to two rows on a phone the second
        # row starts indented. A hidden empty number in front makes every finding a following number: all four pad alike.
        nums = "".join(f'<div class="number"><b>{esc(v)}</b><span>{esc(lab)}</span><small><a href="paper/#{self.paper_anchor(sec)}" data-internal>§{sec}</a></small></div>'
                       for v, lab, sec in findings)
        live = lambda t: [e for e in self.ents.get(t, []) if not e.data.get("deprecated")]
        # the games the book and the videos lean on most: chapters that link or name it, episodes and shorts that show it
        reach = {e.id: len({r[0] for r in self.book_refs.get(e.id, [])}) + len({ep["n"] for ep, _, _ in self.moments.get(e.id, [])}) + len(self.shorts_of.get(e.id, []))
                 for e in live("game")}
        games = sorted(reach, key=lambda i: (-reach[i], self.by_id[i].data["name"]))[:8]
        mname = {e.id: e.data["name"] for e in self.ents.get("mechanic", [])}

        def game_row(e):
            ms = sorted(e.data.get("mechanics", []), key=lambda m: (m.get("role") != "core", mname.get(m["id"], m["id"])))
            icons = "".join(f'<a href="mechanic/{m["id"]}/" title="{esc(mname.get(m["id"], m["id"]))}" data-internal>{self.icon(m["id"], base, 24, mname.get(m["id"], m["id"]))}</a>' for m in ms)
            return (f'<div class="row"><div class="id">{esc(e.data.get("year", ""))}</div><h3>{self.link(e.id, base)} <span>{esc(self.term("subgenre", e.data.get("subgenre")))}</span></h3>'
                    f'<div class="cluster" data-gap="icons">{icons}</div><div class="end">{len(ms)}</div></div>')
        game_sec = self.section_link("start with a game you know", '<p class="small muted">Each game drawn as the parts it is built from, core parts first. '
                                     'Open one to see how it does each part, and which other games share them.</p>'
                                     f'<div class="register" data-kind="parts">{"".join(game_row(self.by_id[i]) for i in games)}</div>',
                                     "game/", f"all {counted(counts['game'], 'game')}")
        watch = ""
        if self.episodes or self.shorts:
            eps = "".join(f'<div class="row">{self.episode_figure(ep, base, 480, self.ep_url(ep, base))}<p class="eyebrow"><span class="id">episode {ep["n"]}</span> '
                          f'<span>{self.mmss(ep["seconds"])}</span></p><h3><a href="{self.ep_url(ep, base)}" data-internal>{esc(ep["title"])}</a></h3><p>{esc(ep["summary"])}</p></div>'
                          for ep in self.episodes[:2])
            shorts = "".join(self.short_tile(sh, base) for sh in self.shorts[:4])
            watch = self.section_link("watch", (f'<div class="register" data-kind="episodes">{eps}</div>' if eps else "")
                                      + (f'<div class="register" data-kind="watch">{shorts}</div>' if shorts else ""),
                                      "watch/", f"{counted(len(self.episodes), 'episode')} and {counted(len(self.shorts), 'short')}")
        mat = {t: i for i, t in enumerate(["shipped-mainstream", "shipped-niche", "prototype", "research"])}
        techs = sorted(live("technique"), key=lambda e: (mat.get(e.data.get("maturity"), 9), -self.derived.get(e.id, {}).get("affects_count", 0), e.data["name"]))[:6]
        tech_sec = self.section_link("ai that already reaches games", '<p class="small muted">The techniques furthest along in shipped games, and the mechanics each one changes.</p>'
                                     + self.board([e.id for e in techs], base), "technique/", f"all {counted(counts['technique'], 'technique')}")
        ops = sorted(live("opportunity"), key=lambda e: (-(self.derived.get(e.id, {}).get("priority") or 0), e.data["name"]))[:4]
        op_sec = self.section_link("what could be built next", '<p class="small muted">Design bets ranked by impact, feasibility, and novelty. Each one names a test a small team '
                                   'could run and a dated prediction anyone can check.</p>'
                                   + self.board([e.id for e in ops], base, lambda e: f'{self.term("horizon", e.data.get("horizon")).lower()} · resolves by {e.data.get("falsifiable_signal", {}).get("resolve_by", "")}'),
                                   "opportunity/", f"all {counted(counts['opportunity'], 'bet')}")
        parts, cur = [], None
        for line in self.built.get("book/00-contents.md", "").splitlines():
            if line.startswith("## "):
                cur = [line[3:], []]
                parts.append(cur)
            elif cur and (m := re.match(r"^(\d+)\. \[(.*?)\]\((\d\d-[a-z0-9-]+)\.md\)", line)):
                cur[1].append(f'<a href="book/{m.group(3)}/" data-internal>{m.group(1)}. {esc(m.group(2))}</a>')
        book_rows = "".join(f'<div class="row"><div class="id">{esc(re.sub(r"[.].*", "", h).lower())}</div><div><h3>{esc(re.sub(r"^Part [IVX]+[.] ", "", h))}</h3><p>{" · ".join(ch)}</p></div></div>'
                            for h, ch in parts if ch)
        book_sec = self.section_link("the book", '<p class="small muted">The findings at book length, for reading straight through: what the parts are, how they trade off, '
                                     'where AI lands, and what to build.</p>' + f'<div class="register">{book_rows}</div>', "book/", "contents") if book_rows else ""
        paper_sec = self.section(
            "the paper and the data",
            '<div class="register" data-size="wide">'
            f'<div class="row"><div class="id">paper</div><div><h3><a href="paper/" data-internal>{esc(meta["title"])}</a></h3><p>Every finding with its method and statistics, '
            'figures you can explore, and the full catalog of games and techniques. The place to check a claim.</p></div></div>'
            '<div class="row"><div class="id">about</div><div><h3><a href="about/" data-internal>How the atlas is made</a></h3><p>Every game, mechanic, and technique is an open '
            'record with its sources, so any number here can be traced to where it came from, checked, and corrected by anyone.</p></div></div></div>')
        header = f"""<div class="page-header corners">
  <p class="eyebrow"><span class="id">atlas</span> <span>simulation games, part by part</span></p>
  <h1>{esc(meta['title'])}</h1>
  <p class="dek">{esc(LEAD)}</p>
  <div class="meta"><span><b>{self.byline_html(base)}</b></span><span>{counted(counts['game'], 'game')}</span><span>{counted(counts['mechanic'], 'mechanic')}</span><span>{counted(counts['technique'], 'technique')}</span><span>{counted(counts['opportunity'], 'bet')}</span></div>
  <div class="actions"><a class="btn" href="game/" data-internal>Browse the games</a><a class="btn" data-style="ghost" href="watch/" data-internal>Watch the series</a><a class="btn" data-style="ghost" href="book/" data-internal>Read the book</a><a class="btn" data-style="ghost" href="paper/" data-internal>Read the paper</a></div>
</div>
<div class="numbers"><div class="number" hidden></div>{nums}</div>
<p class="small faint">four findings from the paper; each links to the section that makes the case</p>
{self.mosaic(base)}"""
        body = header + game_sec + watch + tech_sec + op_sec + book_sec + paper_sec
        return self.page(title=f"{meta['title']} · simgrammar", desc=LEAD, body=body, depth=0, nav="", path="")

    # ------------------------------------------------------------------ shorts and the book
    @staticmethod
    def mmss(sec):
        sec = int(round(sec))
        return f"{sec // 60}:{sec % 60:02d}"

    def voice_html(self, line, base):
        """A narration line as html: its citations become links to the source pages, its record links to record pages."""
        t = esc(line)
        t = re.sub(r"\s*\[((?:\[\d+\]\(#ref-[a-z0-9-]+\)(?:,\s*)?)+)\]",
                   lambda m: "".join(f' <a href="{base}source/{sid}/" data-internal>[{n}]</a>' for n, sid in re.findall(r"\[(\d+)\]\(#ref-([a-z0-9-]+)\)", m.group(1))), t)
        t = re.sub(r"\[([^\]]+)\]\((?:\.\./)+wiki/(\w+)/([a-z0-9-]+)\.md\)", lambda m: f'<a href="{base}{m.group(2)}/{m.group(3)}/" data-internal>{m.group(1)}</a>', t)
        return t.replace("**", "").replace("*", "")

    def short_figure(self, sh, base, width=270):
        """A short's poster, which plays in place. Its opening frame states the finding in its lower lines, so the play
        label sits under the picture instead of on it, and the tile's eyebrow gives the length as well."""
        return (f'<figure class="image" data-ratio="9/16"><a class="frame" href="{base}media/shorts/{esc(sh["file"])}" data-play>'
                f'<img src="{base}media/shorts/{esc(sh["poster"])}" width="{width}" height="{round(width * 16 / 9)}" alt="Short {sh["n"]}: {esc(sh["title"])}, opening frame" loading="lazy">'
                f'</a><figcaption><span>play · {self.mmss(sh["seconds"])}</span></figcaption></figure>')

    def watch_section(self, e, base):
        ss = self.shorts_of.get(e.id, [])
        if not ss:
            return ""
        blocks = "".join(
            f'<div class="split" data-style="watch">{self.short_figure(sh, base)}<div><p class="eyebrow"><span class="id">short {sh["n"]}</span> <span>{self.mmss(sh["seconds"])}</span></p>'
            f'<h3>{esc(sh["title"])}</h3><details class="disclosure" open><summary>transcript</summary>{"".join(f"<p>{self.voice_html(v, base)}</p>" for v in sh["voice"])}</details>'
            + (f'<p class="small faint">also on the pages for</p>{self.chips([i for i in sh["shows"] if i != e.id], base)}' if len(sh["shows"]) > 1 else "")
            + "</div></div>" for sh in ss)
        return self.section("watch", blocks, f'{counted(len(ss), "short")} with this record on screen')

    # ------------------------------------------------------------------ episodes
    @staticmethod
    def episode_voice(md):
        """An episode script's narration by scene, {scene name: [Voice lines]}, with comments to the style checker dropped."""
        out, cur = {}, None
        for line in md.splitlines():
            m = re.match(r"^## \d+\. (.+?)(?: \((.+?)\))?\s*$", line)
            if m:
                cur = m.group(1)
                out[cur] = []
            elif cur and line.startswith("**Voice.** "):
                out[cur].append(re.sub(r"\s*<!--.*?-->", "", line[len("**Voice.** "):]).strip())
        return out

    @staticmethod
    def ep_url(ep, base):
        return f"{base}watch/{ep['key']}/"

    def icon_links(self, ids, base):
        return ('<div class="cluster" data-gap="icons">' + "".join(
            f'<a href="{base}{self.by_id[i].type}/{i}/" title="{esc(self.by_id[i].data.get("name", i))}" data-internal>{self.icon(i, base, 24, self.by_id[i].data.get("name", i))}</a>'
            for i in ids if self.icon(i, base, 24)) + "</div>")

    def covers(self, ep, base):
        return " and ".join(f'<a href="{base}book/{self.chapter_of[c]}/" data-internal>chapter {c}, {esc(self.chapter_name(self.chapter_of[c]))}</a>'
                            for c in ep["covers"] if c in self.chapter_of)

    def chapter_name(self, stem):
        return re.sub(r"^Chapter \d+\. ", "", re.search(r"^# (.*)$", self.built[f"book/{stem}.md"], re.M).group(1))

    def episode_figure(self, ep, base, width, link=None):
        """An episode at 16:9. On its own page, the title card, which becomes the video; elsewhere, the frame with the most
        records on screen, linking the episode page."""
        h = round(width * 9 / 16)
        if link:   # the frame carries the episode's caption along its foot, so no plate sits on it; the eyebrow beside it gives the length
            return (f'<figure class="image" data-ratio="16/9"><a class="frame" href="{link}" data-internal>'
                    f'<img src="{base}media/episodes/{esc(ep["thumb"])}" width="{width}" height="{h}" alt="Episode {ep["n"]}: {esc(ep["title"])}, a frame from the episode" loading="lazy">'
                    f'</a></figure>')
        # the subtitle tracks wait in a template, which simgrammar.js moves into the video it makes; without script each file is a link
        tracks = "".join(f'<track kind="subtitles" srclang="{lang}" label="{esc(label)}" src="{base}{path}">' for lang, label, path, _ in ep["tracks"])
        subs = " ".join(f'<a href="{base}{path}" hreflang="{lang}" lang="{lang}">{esc(label)}</a>' for lang, label, path, _ in ep["tracks"])
        return (f'<figure class="image" data-ratio="16/9"><a class="frame" href="{base}media/episodes/{esc(ep["file"])}" data-play="episode" data-internal>'
                f'<img src="{base}media/episodes/{esc(ep["poster"])}" width="{width}" height="{h}" alt="Episode {ep["n"]}: {esc(ep["title"])}, title card">'
                f'<span class="plate">play · {self.mmss(ep["seconds"])}</span></a>' + (f'<template data-tracks>{tracks}</template>' if tracks else "")
                + f'<figcaption><span class="provenance">captions in the picture</span>' + (f'<span>subtitles · {subs}</span>' if subs else "") + '</figcaption></figure>')

    CARD_TYPES = ("game", "mechanic", "technique", "opportunity")

    def card_line(self, e):
        """The short label above a record's name on an episode page."""
        d = e.data
        if e.type == "game":
            return " · ".join(x for x in (str(d.get("year", "")), self.term("subgenre", d.get("subgenre")).lower()) if x)
        if e.type == "mechanic":
            return self.term("mechanic_family", d.get("family")).lower()
        if e.type == "technique":
            return " · ".join(x for x in (self.term("technique_category", d.get("category")).lower(), str(d.get("year", "")), self.term("technique_maturity", d.get("maturity")).lower()) if x)
        return f'horizon {self.term("horizon", d.get("horizon")).lower()} · impact {d.get("impact")} of 5'

    def card_icon(self, e, base, size=48):
        """A record's icon on an episode page; a game shows its subgenre's emblem and an opportunity its horizon, as the videos do."""
        d = e.data
        if self.icon_id(e.id):
            return self.icon(e.id, base, size, d.get("name", e.id))
        if e.type == "game" and d.get("subgenre") in self.icons:
            return self.icon(d["subgenre"], base, size, self.term("subgenre", d["subgenre"]))
        if e.type == "opportunity" and f'horizon-{d.get("horizon")}' in self.icons:
            return self.icon(f'horizon-{d["horizon"]}', base, size, f'horizon {self.term("horizon", d["horizon"])}')
        return ""

    def episode_page(self, ep):
        base = "../../"
        f = f'{base}media/episodes/{esc(ep["file"])}'
        scenes = ep["scenes"]
        nav = "".join(f'<a class="row" href="{f}#t={sc["start"]:.1f}" data-seek="{sc["start"]:.1f}" data-internal><span class="id">{self.mmss(sc["start"])}</span>'
                      f'<h3>{esc(sc["name"])}</h3><span class="end">{self.mmss(sc["end"] - sc["start"])}</span></a>' for sc in scenes)
        k = self.episodes.index(ep)
        prev_, next_ = (self.episodes[k - 1] if k else None), (self.episodes[k + 1] if k + 1 < len(self.episodes) else None)
        pager = ('<nav class="pagination" aria-label="Episodes">' + (f'<a href="{self.ep_url(prev_, base)}" data-internal>← episode {prev_["n"]}</a>' if prev_ else "")
                 + f'<a href="{base}watch/" data-internal>all episodes</a>' + (f'<a href="{self.ep_url(next_, base)}" data-internal>episode {next_["n"]} →</a>' if next_ else "") + "</nav>")
        side = (f'<aside><div class="section-line"><h2>scenes</h2><span>{len(scenes)} · {self.mmss(ep["seconds"])}</span></div>'
                f'<div class="register" data-kind="scenes">{nav}</div><p class="small muted">The episode follows {self.covers(ep, base)} of the book.</p>{pager}</aside>')
        # the records on screen, in order of appearance, each with the times it is on screen
        moments = {}
        for sc in scenes:
            for i, t in sc["shows"].items():
                moments.setdefault(i, []).append((t, sc["name"]))
        order = sorted(moments, key=lambda i: (min(t for t, _ in moments[i]), i))
        # a record gets a card when the narration names or links it, or when its type has few records on screen
        voice = " ".join(v for sc in scenes for v in sc["voice"])
        linked = set(re.findall(r"\]\(\.\./wiki/\w+/([a-z0-9-]+)\.md\)", voice))
        plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", voice).lower()

        def named(i):
            d = self.by_id[i].data
            return i in linked or any(re.search(r"\b" + re.escape(n.lower()) + r"s?\b", plain) for n in [d.get("name", i)] + d.get("aliases", []))

        def card(i):
            e = self.by_id[i]
            times = " · ".join(f'<a href="{f}#t={t:.1f}" data-seek="{t:.1f}" data-t title="{esc(name)}" data-internal>{self.mmss(t)}</a>' for t, name in sorted(moments[i]))
            return (f'<div class="row"><div class="id"><a href="{base}{e.type}/{i}/" data-internal>{self.card_icon(e, base)}</a></div><div>'
                    f'<small>{esc(self.card_line(e))}</small><h3><a href="{base}{e.type}/{i}/" data-internal>{esc(e.data.get("name", i))}</a></h3>'
                    f'<p>{esc(e.data.get("summary", ""))}</p><p class="small">on screen {times}</p></div></div>')
        sections = []
        for t in self.CARD_TYPES:
            ids = [i for i in order if self.by_id[i].type == t]
            if not ids:
                continue
            cards = ids if len(ids) <= 16 else [i for i in ids if named(i)]
            rest = [i for i in ids if i not in cards]
            plural = self.registry["types"][t]["plural"]
            inner = (f'<div class="register" data-kind="board" data-size="sm">{"".join(card(i) for i in cards)}</div>' if cards else "") + (
                f'<p class="small faint">{"also on screen" if cards else "on screen"} · {counted(len(rest), self.registry["types"][t]["label"].lower(), plural)}</p>'
                + (self.chips(rest, base) if t in ("game", "opportunity") else self.icon_links(rest, base)) if rest else "")
            right = f"{len(cards)} named in the narration, {len(rest)} more on screen" if rest and cards else f"{len(ids)} on screen, in order of appearance"
            sections.append(self.section(f"{plural} in this episode", inner, right))
        rows = []
        for sc in scenes:
            rows.append(f'<div class="row" data-start="{sc["start"]:.1f}"><div class="id"><a href="{f}#t={sc["start"]:.1f}" data-seek="{sc["start"]:.1f}" data-internal>{self.mmss(sc["start"])}</a></div>'
                        f'<div><h3>{esc(sc["name"])}</h3>' + "".join(f"<p>{self.voice_html(v, base)}</p>" for v in sc["voice"])
                        + (f'<p class="small">The video, rendered {esc(ep["rendered"])}, words this scene differently: the dataset has changed since.</p>' if sc["changed"] else "")
                        + "</div></div>")
        changed = sum(1 for sc in scenes if sc["changed"])
        transcript = (f'<details class="disclosure" data-style="transcript"><summary>read the transcript, scene by scene · {counted(len(scenes), "scene")}'
                      + (f' · {changed} worded differently in the video' if changed else "") + f'</summary><div class="register" data-kind="script">{"".join(rows)}</div></details>')
        chapters = " and ".join(str(c) for c in ep["covers"])
        shorts = [sh for sh in self.shorts if sh["episode"] == ep["n"]]
        body = (f'<div data-episode><nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="{base}" data-internal>simgrammar</a></li><li><a href="../" data-internal>watch</a></li>'
                f'<li>episode {ep["n"]}</li></ol></nav>'
                f'<div class="page-header"><p class="eyebrow"><span class="id">episode {ep["n"]} of {len(self.episodes)}</span> <span>{self.mmss(ep["seconds"])}</span> '
                f'<span>{counted(len(scenes), "scene")}</span> <span>book chapter{"s" if len(ep["covers"]) > 1 else ""} {chapters}</span></p><h1>{esc(ep["title"])}</h1>'
                f'<p class="dek">{esc(ep["summary"])}</p></div>'
                f'<div class="split" data-style="episode">{self.episode_figure(ep, base, 960)}{side}</div>'
                + self.section("in the book", '<div class="grid" data-gap="board">' + "".join(self.chapter_block(self.chapter_of[c], base) for c in ep["covers"] if c in self.chapter_of) + "</div>",
                               f'the chapter{"s" if len(ep["covers"]) > 1 else ""} this episode follows')
                + "".join(sections)
                + (self.section("shorts from this episode", f'<div class="register" data-kind="watch">{"".join(self.short_tile(sh, base) for sh in shorts)}</div>',
                                f"{len(shorts)} · under a minute each") if shorts else "")
                + self.section("transcript", transcript, counted(len(scenes), "scene"))
                + "</div>")
        return self.page(title=f"Episode {ep['n']}: {ep['title']} · simgrammar", desc=ep["summary"],
                         body=body, depth=2, nav="watch", path=f"watch/{ep['key']}/", image=f"og/watch/{ep['key']}.png")

    def short_tile(self, sh, base, anchor=False):
        """A short as a tile: its poster that plays in place, its first sentence, the records it shows, and where it comes from."""
        about = [i for i in sh["shows"] if self.by_id[i].type != "game"][:2] + [i for i in sh["shows"] if self.by_id[i].type == "game"][:2]
        ep = next((x for x in self.episodes if x["n"] == sh["episode"]), None)
        frm = " · ".join(x for x in (f'<a href="{base}book/{self.chapter_of[sh["chapter"]]}/" data-internal>chapter {sh["chapter"]}</a>' if sh["chapter"] in self.chapter_of else "",
                                     f'<a href="{self.ep_url(ep, base)}" data-internal>episode {ep["n"]}</a>' if ep else "") if x)
        ident = f' id="{sh["key"]}"' if anchor else ""
        return (f'<div class="row"{ident}>{self.short_figure(sh, base, 216)}'
                f'<p class="eyebrow"><span class="id">short {sh["n"]}</span> <span>{self.mmss(sh["seconds"])}</span>{f" <span>from {frm}</span>" if frm else ""}</p>'
                + (f'<h3>{esc(sh["title"])}</h3>' if anchor else f'<h3><a href="{base}watch/#{sh["key"]}" data-internal>{esc(sh["title"])}</a></h3>')
                + f'<p>{self.voice_html(sh["voice"][0], base) if sh["voice"] else ""}</p>{self.chips(about, base)}</div>')

    def chapter_words(self, stem):
        """A chapter's length in words, without its source list, as its page counts it."""
        if stem not in self._words:
            html = MarkdownIt("commonmark", {"html": True}).enable("table").render(self.book_md(stem))
            self._words[stem] = len(re.sub(r"<[^>]+>", " ", html.split("<h2>Sources</h2>")[0]).split())
        return self._words[stem]

    def chapter_block(self, stem, base):
        """The block an episode page gives each chapter it follows: the chapter's length, its sections, and a link."""
        body = self.built[f"book/{stem}.md"].split("\n## Sources")[0]
        heads = [re.sub(r"[*`]", "", h) for h in re.findall(r"^## (.+)$", body, re.M)]
        words = self.chapter_words(stem)
        n = len([i for i, rs in self.book_refs.items() if any(r[0] == stem for r in rs) and self.by_id[i].type != "source"])
        return (f'<div class="panel" data-style="chapter"><p class="eyebrow"><span class="id">chapter {int(stem[:2])}</span> <span>{counted(f"{words:,}", "word")}</span> '
                f'<span>about {max(1, round(words / 230))} min</span>{f" <span>{counted(n, 'record')}</span>" if n else ""}</p>'
                f'<h3><a href="{base}book/{stem}/" data-internal>{esc(self.chapter_name(stem))}</a></h3>'
                + (f'<p>In this chapter: {" · ".join(esc(h) for h in heads)}.</p>' if heads else "")
                + f'<p class="small"><a href="{base}book/{stem}/" data-internal>read the chapter →</a></p></div>')

    def chapter_watch(self, stem, base):
        """The block a chapter page opens with when an episode follows it."""
        c = int(stem[:2])
        ep = next((e for e in self.episodes if c in e["covers"]), None)
        if not ep:
            return ""
        return (f'<div class="panel" data-style="watch">{self.episode_figure(ep, base, 480, self.ep_url(ep, base))}<div>'
                f'<p class="eyebrow"><span class="id">episode {ep["n"]}</span> <span>{self.mmss(ep["seconds"])}</span> <span>{counted(len(ep["scenes"]), "scene")}</span></p>'
                f'<h3><a href="{self.ep_url(ep, base)}" data-internal>{esc(ep["title"])}</a></h3><p>{esc(ep["summary"])}</p>'
                f'<p class="small"><a href="{self.ep_url(ep, base)}" data-internal>watch the episode →</a></p></div></div>')

    def find_book_refs(self):
        """Where the book mentions a record: chapters that link it, and for mechanics, chapters that name it in the text
        (its name as a whole phrase, outside headings and source lists). The glossary and catalog name everything, so they are left out."""
        refs = defaultdict(list)
        mechs = [e for e in self.ents.get("mechanic", []) if not e.data.get("deprecated")]
        for stem in self.chapters:
            if not re.match(r"(0[1-9]|1[0-9])-", stem):
                continue
            md = self.built[f"book/{stem}.md"].split("\n## Sources")[0]
            title = re.search(r"^# (.*)$", md, re.M).group(1)
            linked = []
            for i in re.findall(r"\]\(\.\./wiki/\w+/([a-z0-9-]+)\.md\)", md):
                if i in self.by_id and i not in linked:
                    linked.append(i)
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", re.sub(r"^#.*$", "", md, flags=re.M))
            plain = text.lower()
            named = [e.id for e in mechs if e.id not in linked and re.search(r"\b" + re.escape(e.data["name"].lower()) + r"s?\b", plain)]
            for t in ("technique", "opportunity"):   # a name or an alias, as a phrase
                named += [e.id for e in self.ents.get(t, []) if e.id not in linked and not e.data.get("deprecated") and any(
                          re.search(r"\b" + re.escape(n.lower()) + r"\b", plain) for n in [e.data["name"]] + [a for a in e.data.get("aliases") or [] if len(a) > 3])]
            named += [e.id for e in self.ents.get("game", []) if e.id not in linked and not e.data.get("deprecated")   # a game's name as written, capitals and all
                      and re.search(r"(?<![\w-])" + re.escape(e.data["name"]) + r"(?![\w-])(?! \d)", text)]
            for i in linked:
                refs[i].append((stem, title, "linked from the text"))
            for i in named:
                refs[i].append((stem, title, "named in the text"))
            for sid in dict.fromkeys(re.findall(r"\(#ref-([a-z0-9-]+)\)", md)):
                if sid in self.by_id:
                    refs[sid].append((stem, title, "cited in the text"))
        return refs

    def appears_section(self, e, base):
        src = e.type == "source"
        rows = [f'<div class="row"><div class="id">paper</div><div><h3><a href="{base}paper/#{hid}" data-internal>{esc(title)}</a></h3>'
                f'<p>{"cited" if src else "linked"} in this section of the paper</p></div><div class="end">paper</div></div>' for hid, title in self.paper_refs.get(e.id, [])]
        listed = {"mechanic": ("90-glossary", "glossary", lambda: f'listed under {self.term("mechanic_family", e.data.get("family")).lower()}, with its summary'),
                  "game": ("91-catalog", "catalog", lambda: "listed with its year, developer, subgenre, and number of mechanics")}.get(e.type)
        if listed and listed[0] in self.chapters:
            st, label, how = listed
            rows.append(f'<div class="row"><div class="id">{label}</div><div><h3><a href="{base}book/{st}/#{e.id}" data-internal>{esc(self.chapter_name(st))}</a></h3>'
                        f'<p>{esc(how())}</p></div><div class="end">book</div></div>')
        rows += [f'<div class="row"><div class="id">ch {int(stem[:2])}</div><div><h3><a href="{base}book/{stem}/" data-internal>{esc(title)}</a></h3><p>{esc(how)}</p></div>'
                f'<div class="end">book</div></div>' for stem, title, how in self.book_refs.get(e.id, [])]
        by_ep = {}
        for ep, t, scene in (self.ep_cites if src else self.moments).get(e.id, []):
            by_ep.setdefault(ep["n"], (ep, []))[1].append((t, scene))
        for n in sorted(by_ep):
            ep, ms = by_ep[n]
            times = ", ".join(f'<a href="{self.ep_url(ep, base)}#t={t:.1f}" data-t data-internal>{self.mmss(t)}</a> {esc(scene.lower())}' for t, scene in ms[:4])
            rows.append(f'<div class="row"><div class="id">ep {n}</div><div><h3><a href="{self.ep_url(ep, base)}" data-internal>{esc(ep["title"])}</a></h3>'
                        f'<p>{"cited at" if src else "on screen at"} {times}{f" and {len(ms) - 4} more" if len(ms) > 4 else ""}</p></div><div class="end">episode</div></div>')
        rows += [f'<div class="row"><div class="id">short {sh["n"]}</div><div><h3><a href="{base}watch/#{sh["key"]}" data-internal>{esc(sh["title"])}</a></h3>'
                 f'<p>{self.mmss(sh["seconds"])} · {"cited in" if src else "on screen in"} the short</p></div><div class="end">short</div></div>'
                 for sh in (self.short_cites if src else self.shorts_of).get(e.id, [])]
        if not rows:
            return ""
        npp, nb, ne, ns = len(self.paper_refs.get(e.id, [])), len(self.book_refs.get(e.id, [])), len(by_ep), len((self.short_cites if src else self.shorts_of).get(e.id, []))
        right = " · ".join(x for x in (f'the paper, {counted(npp, "section")}' if npp else "", counted(nb, "chapter") if nb else "", counted(ne, "episode") if ne else "",
                                       counted(ns, "short") if ns else "") if x)
        return self.section("appears in", f'<div class="register">{"".join(rows)}</div>', right)

    def families(self):
        """Mechanics by family, families with the most mechanics first, each family's mechanics most used first."""
        fam = defaultdict(list)
        for e in self.ents.get("mechanic", []):
            if not e.data.get("deprecated"):
                fam[e.data["family"]].append(e)
        for f in fam:
            fam[f].sort(key=lambda e: (-self.derived.get(e.id, {}).get("prevalence", 0), e.data["name"]))
        return sorted(fam.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    def mosaic(self, base):
        """Every mechanic as its icon, one row per family: the grammar at a glance. Its twin lists the same names."""
        fams = self.families()
        n = sum(len(v) for _, v in fams)
        rows = "".join(
            f'<div class="row"><div class="id">{esc(self.term("mechanic_family", f).lower())} <b>{len(ms)}</b></div><div>'
            + "".join(f'<a href="{base}mechanic/{e.id}/" title="{esc(e.data["name"])} · {counted(self.derived.get(e.id, {}).get("prevalence", 0), "game")}" data-card="{e.id}" data-internal>'
                      f'{self.icon(e.id, base, 24, e.data["name"])}</a>' for e in ms)
            + "</div></div>" for f, ms in fams)
        twin = "".join(f'<div class="row"><div class="id">{esc(self.term("mechanic_family", f).lower())}</div><div><p>'
                       + ", ".join(self.link(e.id, base) for e in ms) + "</p></div></div>" for f, ms in fams)

        def card(f, e):   # what the hover card reads (simgrammar.js); the same fields are on the record page and in the index table
            der = self.derived.get(e.id, {})
            first = self.by_id.get(der.get("earliest_game"))
            return [e.data["name"], self.term("mechanic_family", f).lower(), e.data.get("summary", ""), der.get("prevalence", 0), der.get("core_count", 0),
                    der.get("earliest_year"), first.data.get("name") if first else None, der.get("technique_count", 0)]
        cards = json.dumps({e.id: card(f, e) for f, ms in fams for e in ms}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")
        return (f'<figure class="chart" id="grammar"><div class="chart-head"><span><b>every mechanic</b> · {n} in {counted(len(fams), "family")}, most used first</span>'
                f'<a href="{base}mechanic/" data-internal>all {counted(n, "mechanic")}</a></div><div class="chart-body"><div class="register" data-kind="mosaic" data-cards="mosaic-cards">{rows}</div></div>'
                f'<script type="application/json" id="mosaic-cards">{cards}</script>'
                f'<p class="chart-caption">Each icon is one mechanic, a rule-system a designer would recognize across games. Point at one to see what it is, or open it.</p>'
                f'<details class="disclosure"><summary>plain-text twin · {counted(len(fams), "family")}</summary><div class="register" data-size="wide">{twin}</div></details></figure>')

    # ------------------------------------------------------------------ entity pages
    def meter(self, v, scale_max=5):
        if not isinstance(v, int):
            return esc(v)
        cells = "".join(f'<i data-state="{"done" if i < v else ""}"></i>' for i in range(scale_max))
        return f'<span class="meter" data-size="sm" role="img" aria-label="{v} of {scale_max}">{cells}</span> <span class="meter-label">{v} / {scale_max}</span>'

    def entity(self, e):
        t, d = e.type, e.data
        base = "../../"
        props = self.props[t]
        der = self.derived.get(e.id, {})
        plural = self.registry["types"][t]["plural"]
        st = d.get("status")
        eyebrow = [f'<span class="id">{esc(self.registry["types"][t]["label"].lower())}</span>']
        if d.get("deprecated"):
            eyebrow.append('<span class="status" data-state="superseded">deprecated</span>')
        meta = self.entity_meta(e)
        twins = (f'<p class="small"><b>this record as</b> <a href="{esc(self.gh(self.registry["types"][t]["dir"] + "/" + e.id + ".yaml"))}">yaml source</a>'
                 f' · <a href="{esc(self.dl("wiki/" + t + "/" + e.id + ".md", base))}">markdown</a> · <a href="{esc(self.dl("entities/" + plural + ".json", base))}">json</a></p>')
        icon = self.icon(e.id, base, 96)
        head = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="{base}" data-internal>simgrammar</a></li><li><a href="../" data-internal>{esc(READER_NAME.get(t, ("", plural))[1])}</a></li><li>{esc(d.get("name", e.id))}</li></ol></nav>'
                f'<div class="page-header"{" data-style=" + chr(34) + "icon" + chr(34) if icon else ""}>{icon}<p class="eyebrow">{" ".join(eyebrow)}</p><h1>{esc(d.get("name", e.id))}</h1>'
                + (f'<p class="dek">{esc(d["summary"])}</p>' if d.get("summary") else "") + meta + "</div>")
        if d.get("deprecated"):
            head += (f'<div class="note" data-surface="open"><span class="label">deprecated</span><p>{esc(d["deprecated"].get("reason", ""))} '
                     f'Superseded by {self.link(d["deprecated"]["superseded_by"], base)}.</p></div>')
        main = ([self.parts_board(e, base)] if t == "game" else []) + [self.watch_section(e, base)]
        for f in LONG.get(t, []):
            if d.get(f):
                cls = ' class="mono"' if f == "core_loop" else ""
                main.append(self.section(f.replace("_", " "), f'<p{cls}>{esc(d[f])}</p>'))
        for f in LISTS.get(t, []):
            if d.get(f):
                main.append(self.section(f.replace("_", " "), "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in d[f]) + "</ul>"))
        if t == "opportunity" and d.get("falsifiable_signal"):
            fs = d["falsifiable_signal"]
            res = fs.get("resolution")
            outcome = res["outcome"] if res else "open"
            res_html = ""
            if res:
                ev = ", ".join(self.link(x, base, x) for x in res.get("evidence") or [])
                res_html = (f'<p class="scope">resolved {esc(res["date"])} in <a href="{esc(self.gh("log/runs/" + res["run"] + ".yaml"))}">{esc(res["run"])}</a>'
                            + (f" · evidence {ev}" if ev else "") + f'</p><p>{esc(res["note"])}</p>')
            main.append(self.section("falsifiable prediction", f'<div class="register" data-kind="forecasts"><div class="row"><div class="id"><b>by {esc(fs["resolve_by"])}</b></div>'
                                     f'<div><h3>{esc(fs["prediction"])}</h3><p>{esc(fs["criteria"])}</p>{res_html}</div>'
                                     f'<div class="end"><span class="status" data-state="{OUTCOME_STATE.get(outcome, "waiting")}">{esc(outcome)}</span></div></div></div>'))
        about = []   # how this record was made and checked: one collapsed block at the end of the page
        if d.get("assertions"):
            items = "".join(f"<li><code>{esc(x)}</code></li>" for x in d["assertions"])
            about.append((f'checks against the data · {len(d["assertions"])}', f'<p class="small muted">The text above states findings about the catalog. '
                          f'If new data makes one false, the site stops building until the text is fixed.</p><ul>{items}</ul>'))
        if d.get("ratings"):
            rrows = "".join(f'<div class="row"><div class="id">{esc(r["field"].replace("_", " "))}<small>{esc(r["value"])}</small></div><div><p>{esc(r["rationale"])}</p>'
                            f'<p class="scope"><a href="{esc(self.gh("log/runs/" + r["run"] + ".yaml"))}">{esc(r["run"])}</a></p></div></div>' for r in d["ratings"])
            about.append((f'ratings · {len(d["ratings"])}', f'<p class="small muted">Scores rated by more than one rater; the score shown is the lower median.</p>'
                          f'<div class="register" data-kind="claims">{rrows}</div>'))
        main.append(self.appears_section(e, base))
        main.append(self.relations(e, base))
        claims = (d.get("key_results") or []) + (d.get("claims") or [])
        if claims:
            rows = []
            for i, c in enumerate(claims, start=1):
                srcs = ", ".join(self.link(s, base, self.cite_label(s)) for s in c.get("sources", []))
                disp = f'<p class="scope">disputed · {esc(c["disputes"])}</p>' if c.get("disputes") else ""
                quote = (f'<blockquote><p>{esc(c["quote"])}</p></blockquote>' + (f'<p class="scope">{esc(c["locator"])}</p>' if c.get("locator") else "")) if c.get("quote") else ""
                rows.append(f'<div class="row"><div class="id">c{i:02d}<small>{esc(c.get("confidence", ""))}</small></div><div><p>{esc(c["text"])}</p>'
                            f'{quote}<p class="scope">{srcs}</p>{disp}</div></div>')
            main.append(self.section("claims", f'<div class="register" data-kind="claims">{"".join(rows)}</div>', f"{len(claims)} with sources"))
        if t == "source":
            loc = d.get("url") or (f"https://doi.org/{d['doi']}" if d.get("doi") else None) or (f"https://arxiv.org/abs/{d['arxiv']}" if d.get("arxiv") else None)
            cited = der.get("incoming", {}).get("cited_by", [])
            main.append(self.section("cited by", self.list_links(cited, base) if cited else '<p class="muted">Cited in the report text.</p>', counted(len(cited), "record")))
            if loc:
                arch = f'<p class="scope">archived · <a href="{esc(d["archived"])}">wayback snapshot</a></p>' if d.get("archived") else ""
                main.insert(0, self.section("locator", f'<p><a href="{esc(loc)}">{esc(loc)}</a></p>{arch}'))
        if d.get("sources"):
            rows = []
            for sid in d["sources"]:
                s = self.by_id.get(sid)
                if not s:
                    continue
                sd = s.data
                rows.append(f'<div class="row"><div class="id"></div><div><span class="who">{esc(", ".join(sd.get("authors", [])[:3]))}</span> ({esc(sd.get("date"))}). '
                            f'{self.link(sid, base)}. <span class="venue">{esc(sd.get("venue", ""))}</span></div></div>')
            main.append(self.section("sources", f'<div class="register" data-kind="refs">{"".join(rows)}</div>', f"{len(rows)}"))
        about.append(("history", self.provenance(d.get("provenance", {}))))
        main.append(self.about_record(e, about, twins))
        aside = self.facts(e)
        jump = re.findall(r'<section class="section" id="([^"]+)"><div class="section-line"><h2>(.*?)</h2>', "".join(m for m in main if m))
        if len(jump) > 2:
            head += ('<nav class="cluster" data-gap="chips" data-style="jump" aria-label="On this page"><span>on this page</span>'
                     + "".join(f'<a class="chip" data-style="name" href="#{hid}" data-internal>{re.sub(r"<[^>]+>", "", h)}</a>' for hid, h in jump) + "</nav>")
        body = head + f'<div class="split"><div style="min-width:0">{"".join(m for m in main if m)}</div><aside class="aside" style="min-width:0">{aside}</aside></div>'
        # a source's title names where it is published, since a store page and a wiki article often share a game's name
        where = (d.get("venue") or self.term("source_kind", d.get("kind")).lower()) if t == "source" else ""
        title = " · ".join(x for x in (d.get("name", e.id), where if where != d.get("name") else "", self.registry["types"][t]["label"].lower(), "simgrammar") if x)
        desc = d.get("summary") or d.get("notes") or d.get("name", e.id)
        return self.page(title=title, desc=desc, body=body, depth=2, nav=t, path=f"{t}/{e.id}/", image=f"og/{t}/{e.id}.png" if t != "source" else "og/site.png")

    STATUS_WHY = {"asserted": "Not yet backed by a source. It is in the queue for someone to source.",
                  "sourced": "Its facts cite the sources below. No second person has checked them yet.",
                  "verified": "Someone other than its author checked its facts against the sources.",
                  "contested": "Its sources disagree; both sides are cited below."}

    def about_record(self, e, parts, twins):
        """The last section of a record page, collapsed: why the record can be trusted, then its status, checks, ratings,
        history, and files. A reader who only wants the game, mechanic, or technique never has to open it."""
        st = e.data.get("status")
        if e.type == "source":
            why = ("Every fact on this page comes from the record below, which says what the source is and where to read it, so any of it can be "
                   "checked against the source itself and corrected.")
        elif self.cites(e):
            why = "Every fact on this page comes from the record below and the sources it cites, so any of it can be traced, checked, and corrected."
        else:
            why = ("Every fact on this page comes from the record below, which cites no source yet: its facts are its author's reading until "
                   "someone adds a source. Any of it can be checked and corrected.")
        head = f'<p>{esc(why)} <a href="../../about/" data-internal>How the atlas is made</a>.</p>'
        say = self.STATUS_WHY.get(st, "")
        if st == "asserted" and self.cites(e):   # it lists sources, but they do not yet back its facts
            say = "Its sources do not yet back all of its facts. It is in the queue for someone to source."
        status = (f'<p><span class="status" data-state="{STATE.get(st, "optional")}">{esc(st)}</span> {esc(say)}</p>' if st else "")
        inner = head + status + "".join(f'<h3>{esc(h)}</h3>{html}' for h, html in parts if html) + twins
        return self.section("about this record", f'<details class="disclosure"><summary>status, checks, and history{f" · {esc(st)}" if st else ""}</summary>{inner}</details>')

    @staticmethod
    def cites(e):
        """Whether a record cites a source, in its sources or in a claim's."""
        d = e.data
        return bool(d.get("sources") or any(c.get("sources") for c in (d.get("claims") or []) + (d.get("key_results") or [])))

    def cite_label(self, sid):
        """A short citation for a source: first author's surname and year, else the work's name."""
        s = self.by_id.get(sid)
        if not s:
            return sid
        au, yr = s.data.get("authors") or [], str(s.data.get("date", ""))[:4]
        personal = s.data.get("kind") in ("paper", "preprint", "book", "talk")   # people's names; elsewhere an author is often a studio or a company
        who = (au[0].split()[-1] if personal else au[0]) if au and au[0].split() else s.data.get("name", sid)
        return f"{who}{' et al.' if len(au) > 2 else ''} {yr}".strip()

    def section(self, title, inner, right=""):
        return f'<section class="section" id="{slug(title)}"><div class="section-line"><h2>{esc(title)}</h2>{f"<span>{esc(right)}</span>" if right else ""}</div>{inner}</section>'

    def list_links(self, ids, base):
        return "<p>" + ", ".join(self.link(x, base) for x in ids) + "</p>"

    def entity_meta(self, e):
        d, der, t = e.data, self.derived.get(e.id, {}), e.type
        items = []
        if t == "game":
            items = [str(d.get("year", "")), d.get("developer", ""), self.term("subgenre", d.get("subgenre")), counted(der.get('mechanic_count', 0), "mechanic")]
        elif t == "mechanic":
            items = [self.term("mechanic_family", d.get("family")), self.term("maturity", d.get("maturity")), f"used by {counted(der.get('prevalence', 0), 'game')}",
                     f"first seen {der.get('earliest_year')}" if der.get("earliest_year") else ""]
        elif t == "technique":
            items = [self.term("technique_category", d.get("category")), str(d.get("year", "")), self.term("technique_maturity", d.get("maturity")),
                     f"determinism {self.term('determinism_impact', d.get('determinism_impact'))}", f"{counted(der.get('affects_count', 0), 'mechanic')} affected"]
        elif t == "opportunity":
            items = [self.term("opportunity_type", d.get("opportunity_type")), f"horizon {self.term('horizon', d.get('horizon'))}", f"impact {d['impact']} of 5" if d.get("impact") is not None else "",
                     f"resolves by {d.get('falsifiable_signal', {}).get('resolve_by', '')}"]
        elif t == "source":
            items = [self.term("source_kind", d.get("kind")), d.get("venue", ""), str(d.get("date", ""))]
        return '<div class="meta">' + "".join(f"<span>{esc(x)}</span>" for x in items if x and x != "None") + "</div>"

    def facts(self, e):
        t, d, props = e.type, e.data, self.props[e.type]
        skip = SKIP_FACTS | set(LONG.get(t, [])) | set(LISTS.get(t, []))
        rows = []
        scores = []
        for k, p in props.items():
            if k in skip or d.get(k) in (None, [], ""):
                continue
            if p.get("x-edge") or (p.get("items") or {}).get("x-edge") or (p.get("items") or {}).get("type") == "object" or k in ("mechanics", "affects"):
                continue
            v = d[k]
            if p.get("x-rubric"):
                scores.append((k, v, p.get("maximum", 5)))
                continue
            vn = p.get("x-vocab") or (p.get("items") or {}).get("x-vocab")
            if vn:
                v = ", ".join(self.term(vn, x) for x in v) if isinstance(v, list) else self.term(vn, v)
            elif isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            elif isinstance(v, bool):
                v = "yes" if v else "no"
            rows.append(f"<dt>{esc(k.replace('_', ' '))}</dt><dd>{esc(v)}</dd>")
        for store, sid in sorted((d.get("store_ids") or {}).items()):
            rows.append(f'<dt>{esc(store)}</dt><dd><a href="{esc(STORE_URL[store].format(sid))}">{esc(sid)}</a></dd>')
        out = []
        if rows:
            out.append(f'<h3>facts</h3><dl class="receipt">{"".join(rows)}</dl>')
        if scores:
            sc = "".join(f"<dt>{esc(k.replace('_', ' '))}</dt><dd>{self.meter(v, mx)}</dd>" for k, v, mx in scores)
            out.append(f'<h3 style="margin-top:24px">scores</h3><dl class="receipt">{sc}</dl><p class="small faint">each against fixed written anchors · '
                       f'<a href="../../paper/#{self.paper_anchor("2.3")}" data-internal>how scores work</a></p>')
        der = {k: v for k, v in self.derived.get(e.id, {}).items() if isinstance(v, (int, float, str)) and v is not None}
        if der:
            dr = "".join(f"<dt>{esc(k.replace('_', ' '))}</dt><dd>{self.link(v, '../../') if isinstance(v, str) and v in self.by_id else esc(_fmt(v))}</dd>" for k, v in der.items())
            out.append(f'<h3 style="margin-top:24px">across the catalog</h3><dl class="receipt">{dr}</dl>')
        return "".join(out)

    def relations(self, e, base):
        et = vocab_terms(self.vocabs, "edge_types")
        rows = []
        for ed in sorted(self.edges_out.get(e.id, []), key=lambda x: (x.type, x.target)):
            if ed.type == "cites" or ed.target not in self.by_id:
                continue
            a = ed.attr_dict()
            end = []
            if a.get("role"):
                end.append(a["role"])
            if a.get("effect"):
                end.append(self.term("effect", a["effect"]))
            note = f'<p>{esc(a["note"])}</p>' if a.get("note") else ""
            rank = 0 if a.get("role") == "core" else 1
            if e.type == "game" and ed.type == "uses":
                continue
            rows.append((ed.type, rank, f'<div class="row"><div class="id">{esc(et[ed.type]["label"].lower())}</div><div><h3>{self.icon(ed.target, base, 24)}{self.link(ed.target, base)}</h3>{note}</div>'
                         f'<div class="end">{esc(" · ".join(end))}</div></div>'))
        out = []
        if rows:
            rows.sort(key=lambda r: (r[0], r[1]))
            out.append(self.section("relations", f'<div class="register">{"".join(r[2] for r in rows)}</div>', counted(len(rows), "link")))
        inc = dict(self.derived.get(e.id, {}).get("incoming", {}))
        for ed in self.edges_in.get(e.id, []):   # the inverses the analysis does not list: synergy, requires, influenced, and the rest
            inv = et[ed.type].get("inverse", ed.type)
            if ed.type != "cites" and ed.source in self.by_id and inv not in self.derived.get(e.id, {}).get("incoming", {}):
                inc.setdefault(inv, [])
                if ed.source not in inc[inv]:
                    inc[inv].append(ed.source)
        inc_rows = []
        for k, ids in sorted(inc.items()):
            if k == "cited_by":
                continue
            inc_rows.append(f'<div class="row"><div class="id">{esc(k.replace("_", " "))}</div><div>{self.chips(ids, base)}</div>'
                            f'<div class="end">{len(ids)}</div></div>')
        if inc_rows:
            out.append(self.section("backlinks", f'<div class="register">{"".join(inc_rows)}</div>', "what links here"))
        return "".join(out)

    def parts_board(self, e, base):
        """A game's mechanics drawn as its parts, core first, each with the note on how this game does it. It replaces the
        game's `uses` rows in relations; the rows' text is all here, so the board is its own twin."""
        parts = []
        for ed in self.edges_out.get(e.id, []):
            if ed.type == "uses" and ed.target in self.by_id:
                a = ed.attr_dict()
                parts.append((0 if a.get("role") == "core" else 1, ed.target, a))
        parts.sort(key=lambda p: (p[0], self.by_id[p[1]].data["name"]))
        if not parts:
            return ""
        def tile(eid, a, size):
            fam = self.term("mechanic_family", self.by_id[eid].data["family"]).lower()
            note = f'<p>{esc(a["note"])}</p>' if a.get("note") else ""
            return f'<div class="row"><div class="id">{self.icon(eid, base, size)}</div><div><small>{esc(fam)}</small><h3>{self.link(eid, base)}</h3>{note}</div></div>'
        core = [p for p in parts if p[0] == 0]
        rest = [p for p in parts if p[0] != 0]
        inner = ""
        if core:
            inner += f'<p class="small faint">core · {len(core)}</p><div class="register" data-kind="board">{"".join(tile(i, a, 96) for _, i, a in core)}</div>'
        if rest:
            inner += f'<p class="small faint">supporting · {len(rest)}</p><div class="register" data-kind="board" data-size="sm">{"".join(tile(i, a, 48) for _, i, a in rest)}</div>'
        return self.section("parts", inner, f'{counted(len(parts), "mechanic")}, as {e.data.get("name", e.id)} does them')

    def provenance(self, prov):
        rows = []
        for rid, kind in [(prov.get("created"), "created")] + [(r, "reviewed") for r in prov.get("reviewed", [])]:
            if not rid:
                continue
            r = self.runs.get(rid)
            date = r.data.get("date") if r else ""
            rows.append(f'<div class="row" data-state="done"><div class="id">{esc(date)}</div><span class="dot"></span><span class="kind">{esc(kind)}</span>'
                        f'<span class="what"><a href="{esc(self.gh("log/runs/" + rid + ".yaml"))}">{esc(rid)}</a></span><span class="src">{esc(r.data.get("kind", "") if r else "")}</span></div>')
        return f'<div class="register" data-kind="log" data-style="timeline">{"".join(rows)}</div>' if rows else ""

    # ------------------------------------------------------------------ indexes
    def index(self, t):
        spec = {
            "game": (["name", "year", "subgenre", "_derived.cluster", "_derived.mechanic_count", "status"], ["name", "year", "subgenre", "cluster", "mechanics", "status"], ["name"]),
            "mechanic": (["name", "family", "_derived.prevalence", "_derived.earliest_year", "maturity", "legibility", "emergence_potential", "ai_leverage", "_derived.technique_exposure"],
                         ["name", "family", "games", "first seen", "maturity", "legibility", "emergence", "ai leverage", "exposure"], ["-_derived.prevalence", "name"]),
            "technique": (["name", "category", "year", "maturity", "determinism_impact", "_derived.affects_count"], ["name", "category", "year", "maturity", "determinism", "mechanics"], ["name"]),
            "opportunity": (["name", "opportunity_type", "horizon", "_derived.priority", "falsifiable_signal.resolve_by"], ["name", "type", "horizon", "priority", "resolves by"], ["-_derived.priority", "name"]),
            "source": (["name", "kind", "venue", "date"], ["name", "kind", "venue", "date"], ["-date", "name"]),
        }[t]
        cols, heads, sort = spec
        lst = [e for e in self.ents.get(t, []) if not e.data.get("deprecated")]
        recs = []
        for e in lst:
            r = dict(e.data)
            r["_derived"] = self.derived.get(e.id, {})
            recs.append(r)
        for key in reversed(sort):
            rev = key.startswith("-")
            k = key.lstrip("-")
            recs.sort(key=lambda r: (get_path(r, k) is None, str(get_path(r, k)) if not isinstance(get_path(r, k), (int, float)) else get_path(r, k)), reverse=rev)
        rows = []
        for r in recs:
            row = {}
            for c in cols:
                v = get_path(r, c)
                vn = self.vocab_of(t, c) if "." not in c else None
                if c == "name":
                    v = r["id"]
                elif vn and v is not None:
                    v = ", ".join(self.term(vn, x) for x in v) if isinstance(v, list) else self.term(vn, v)
                elif c == "_derived.cluster" and v:
                    v = v.lower()
                row[c] = v
            rows.append(row)
        base = "../"
        th = "".join(f'<th{" class=" + chr(34) + "num" + chr(34) if self._numeric(rows, c) else ""}>{esc(h)}</th>' for c, h in zip(cols, heads))
        trs = []
        for row in rows:
            tds = "".join(f'<td{" class=" + chr(34) + "num" + chr(34) if self._numeric(rows, c) else ""}>{self.link(row[c], base) if c == "name" else esc(_fmt(row[c]))}</td>' for c in cols)
            trs.append(f"<tr>{tds}</tr>")
        plural = self.registry["types"][t]["plural"]
        one, many = READER_NAME.get(t, (self.registry["types"][t]["label"].lower(), plural))   # what the index calls its records
        intro = {
            "game": "Each catalogued game drawn as the mechanics it is built from, core parts first. Each page holds the decomposition, design notes, claims, and sources.",
            "mechanic": "Every mechanic as its icon, grouped by family and ordered by how many games use it. The table below holds every score: rubric anchors from 1 to 5, "
                        "and exposure, the maturity-weighted reach of the technique set.",
            "technique": "Every mathematical, AI, ML, and LLM technique in the set, with its maturity in games and what it does to reproducibility.",
            "opportunity": "Every design bet on a board by horizon, highest impact first, with the mechanics it builds on, the techniques it uses, and the risks "
                           "those techniques carry. Each bet is an opportunity record with a dated, falsifiable prediction; the table orders them by priority.",
            "source": "Every source cited by a record or by the paper, newest first.",
        }[t]
        h1 = {"game": "Every game is a set of parts", "opportunity": "What could be built, and when"}.get(t, plural.capitalize())
        placeholder = {"game": "filter by game or by a part it has"}.get(t, f"type to filter {many}")
        table = f'<div class="table-wrap"><table class="data" data-style="dense" data-sortable data-filterable><thead><tr>{th}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'
        visual = {"mechanic": self.mechanic_tiles, "game": self.game_parts, "opportunity": self.opportunity_board}.get(t)
        if visual:
            table = visual(lst, base) + f'<details class="disclosure"><summary>plain-text twin · {counted(len(rows), "row")}, sortable</summary>{table}</details>'
        body = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>{esc(many)}</li></ol></nav>'
                f'<div class="page-header"><p class="eyebrow"><span class="id">{esc(many)}</span> <span>{counted(len(rows), "record")}</span></p><h1>{esc(h1)}</h1>'
                f'<p class="dek">{esc(intro)}</p><div class="twins"><b>this list as</b><a href="{esc(self.dl("tables/" + plural + ".csv", "../"))}">csv</a>'
                f'<a href="{esc(self.dl("entities/" + plural + ".json", "../"))}">json</a><a href="{esc(self.gh(self.registry["types"][t]["dir"]))}">yaml sources</a></div></div>'
                f'<div class="controls" data-filter-controls hidden><label class="field"><span>filter</span><input type="search" data-filter placeholder="{esc(placeholder)}"></label>'
                + (self.segmented("group", "Group games", [("subgenre", "by subgenre"), ("decade", "by decade")]) if t == "game" else "")
                + f'</div>{self.no_match(f"No {one} matches that filter.")}{table}')
        return self.page(title=f"{many.capitalize()} · simgrammar", desc=intro, body=body, depth=1, nav=t, path=f"{t}/", image=f"og/{t}.png")

    @staticmethod
    def segmented(name, label, options):
        """A view switch for simgrammar.js; without script the first view shows and the switch stays hidden."""
        bs = "".join(f'<button type="button" data-value="{v}" aria-pressed="{"true" if i == 0 else "false"}">{esc(t)}</button>' for i, (v, t) in enumerate(options))
        return f'<div class="segmented" role="group" aria-label="{esc(label)}" data-views="{name}">{bs}</div>'

    @staticmethod
    def no_match(sentence):
        """What a filtered list says when nothing in it matches; simgrammar.js shows it, and without script it stays hidden
        because the list is never filtered."""
        return (f'<p class="muted" data-filter-empty role="status" hidden>{esc(sentence)} Try fewer words or part of a name, '
                'or clear the filter to see the whole list.</p>')

    def group(self, head, inner, right=""):
        """A filterable group on an index page: a section the filter hides when nothing in it matches."""
        return (f'<section class="section" data-group><div class="section-line"><h2>{head}</h2>{f"<span>{esc(right)}</span>" if right else ""}</div>'
                f'{inner}</section>')

    def mechanic_tiles(self, lst, base):
        top = max((self.derived.get(e.id, {}).get("prevalence", 0) for e in lst), default=1) or 1

        def tile(e):
            der = self.derived.get(e.id, {})
            n = der.get("prevalence", 0)
            q = " ".join([e.data["name"], e.id, *e.data.get("aliases", [])]).lower()
            return (f'<a class="row" href="{base}mechanic/{e.id}/" data-q="{esc(q)}" data-internal>{self.icon(e.id, base, 48)}<h3>{esc(e.data["name"])}</h3>'
                    f'<span class="end"><span>{counted(n, "game")}</span><span>{der.get("earliest_year") or ""}</span></span>'
                    f'<span class="pbar"><i style="--p:{100 * n / top:.1f}%"></i></span></a>')
        groups = "".join(
            self.group(f'{self.icon(f, base, 24)}{esc(self.term("mechanic_family", f))} <span data-count>· {counted(len(ms), "mechanic")}</span>',
                       f'<div class="register" data-kind="tiles">{"".join(tile(e) for e in ms)}</div>',
                       f'{counted(sum(self.derived.get(e.id, {}).get("prevalence", 0) for e in ms), "use")} across the catalog')
            for f, ms in self.families())
        return f'<div data-filter-scope>{groups}</div>'

    def game_parts(self, lst, base):
        mname = {e.id: e.data["name"] for e in self.ents.get("mechanic", [])}

        def row(e, sub):
            ms = sorted(e.data.get("mechanics", []), key=lambda m: (m.get("role") != "core", mname.get(m["id"], m["id"])))
            icons = "".join(f'<a href="{base}mechanic/{m["id"]}/" data-m="{m["id"]}" data-role="{esc(m.get("role", ""))}" '
                            f'title="{esc(mname.get(m["id"], m["id"]))} · {esc(m.get("role", ""))}" data-internal>{self.icon(m["id"], base, 24, mname.get(m["id"], m["id"]))}</a>'
                            for m in ms)
            q = " ".join([e.data["name"], e.id, self.term("subgenre", e.data.get("subgenre"))] + [mname.get(m["id"], "") for m in ms]).lower()
            label = f' <span>{esc(self.term("subgenre", e.data.get("subgenre")))}</span>' if sub else ""
            return (f'<div class="row" data-q="{esc(q)}"><div class="id">{esc(e.data.get("year", ""))}</div><h3>{self.link(e.id, base)}{label}</h3>'
                    f'<div class="cluster" data-gap="icons">{icons}</div><div class="end">{len(ms)}</div></div>')
        by_sub, by_dec = defaultdict(list), defaultdict(list)
        for e in lst:
            by_sub[e.data.get("subgenre")].append(e)
            by_dec[e.data.get("year", 0) // 10 * 10].append(e)
        order = lambda e: (e.data.get("year", 0), e.data["name"])
        subs = "".join(self.group(f'{self.icon(s, base, 24)}{esc(self.term("subgenre", s))} <span data-count>· {counted(len(gs), "game")}</span>',
                                  f'<div class="register" data-kind="parts">{"".join(row(e, False) for e in sorted(gs, key=order))}</div>')
                       for s, gs in sorted(by_sub.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))))
        decs = "".join(self.group(f'{d}s <span data-count>· {counted(len(gs), "game")}</span>',
                                  f'<div class="register" data-kind="parts">{"".join(row(e, True) for e in sorted(gs, key=order))}</div>',
                                  f'{sum(len(e.data.get("mechanics", [])) for e in gs) / len(gs):.1f} parts a game')
                       for d, gs in sorted(by_dec.items()))
        legend = ('<div class="legend"><span><i></i>core part</span><span><i data-style="faint"></i>supporting part</span>'
                  '<span class="hide-sm">point at a part to light up every game that has it</span></div>')
        return (f'{legend}<div data-filter-scope data-parts-scope><div data-view="subgenre">{subs}</div>'
                f'<div data-view="decade" hidden>{decs}</div></div>')

    def opportunity_board(self, lst, base):
        risk_labels = {str(t["id"]): t.get("label", t["id"]) for t in self.vocabs["risk"]["terms"]}

        def icons(ids, label=None):
            return '<div class="cluster" data-gap="icons">' + "".join(
                f'<a href="{base}{self.by_id[i].type}/{i}/" title="{esc(self.by_id[i].data["name"])}" data-internal>{self.icon(i, base, 24, self.by_id[i].data["name"])}</a>'
                for i in ids if i in self.by_id) + "</div>"

        def card(e):
            d = e.data
            techs = [x for x in d.get("applies", []) if x in self.by_id]
            risks = sorted({r for x in techs for r in self.by_id[x].data.get("risks", [])})
            rk = '<div class="cluster" data-gap="icons">' + "".join(
                f'<span title="{esc(risk_labels.get(r, r))}">{self.icon("risk-" + r, base, 24, risk_labels.get(r, r))}</span>' for r in risks) + "</div>"
            q = " ".join([d["name"], e.id, d.get("summary", "")]).lower()
            dl = "".join(f"<dt>{k}</dt><dd>{self.meter(d.get(k))}</dd>" for k in ("impact", "feasibility", "novelty") if d.get(k) is not None)
            dl += f"<dt>builds on</dt><dd>{icons(d.get('involves', []))}</dd><dt>uses</dt><dd>{icons(techs)}</dd>"
            dl += f"<dt>risks</dt><dd>{rk}</dd>" if risks else ""
            return (f'<div class="row" data-q="{esc(q)}"><div class="id">{esc(self.term("opportunity_type", d.get("opportunity_type")).lower())}</div>'
                    f'<div><h3>{self.link(e.id, base)}</h3><p>{esc(d.get("summary", ""))}</p><dl class="receipt">{dl}</dl></div></div>')
        cols = []
        for h in ("now", "1-2y", "3-5y", "5y-plus"):
            ops = sorted((e for e in lst if e.data.get("horizon") == h), key=lambda e: (-(e.data.get("impact") or 0), -(e.data.get("feasibility") or 0), e.data["name"]))
            inner = "".join(card(e) for e in ops) or '<div class="row"><p>none yet</p></div>'
            cols.append(f'<section data-group><div class="section-line"><h2>{self.icon("horizon-" + h, base, 48)}{esc(self.term("horizon", h))} <span data-count>· {len(ops)}</span></h2></div>'
                        f'<div class="register" data-kind="cards">{inner}</div></section>')
        legend = '<div class="legend">' + "".join(f'<span>{self.icon("risk-" + r, base, 24)}{esc(lbl)}</span>' for r, lbl in risk_labels.items()) + "</div>"
        return f'{legend}<div class="grid" data-cols="4" data-gap="board" data-filter-scope>{"".join(cols)}</div>'

    # ------------------------------------------------------------------ data page
    def about_page(self):
        """How the atlas is made, for readers who want it: why it is built from open records, then the downloads, commands,
        research log, and vocabularies. Every other page keeps this one click away."""
        man = self.manifest
        plurals = [self.registry["types"][t]["plural"] for t in self.registry["types"] if not self.registry["types"][t].get("meta")]
        files = [
            ("dist/simgrammar-dist.zip", "everything below in one archive (assembled by the Pages workflow)", [("zip", "simgrammar-dist.zip")]),
            ("dist/tables/", "one flat table per entity type, edges.csv, game_mechanic_matrix.csv",
             [(n, f"tables/{n}.csv") for n in plurals + ["edges", "game_mechanic_matrix"]]),
            ("dist/entities/", "full records with computed fields under _derived", [(n, f"entities/{n}.json") for n in plurals]),
            ("dist/graph/", "nodes, edges, Cytoscape, GraphML", [("nodes", "graph/nodes.jsonl"), ("edges", "graph/edges.jsonl"), ("cytoscape", "graph/cytoscape.json"), ("graphml", "graph/graph.graphml")]),
            ("dist/analysis/", "every statistic, and every analysis table as csv", [("stats", "analysis/stats.json"), ("clusters", "analysis/game-clusters.csv"), ("white space", "analysis/whitespace.csv"), ("verification queue", "analysis/verification-queue.csv")]),
            ("dist/wiki/", "one markdown page per record and vocabulary, with backlinks", [("index", "wiki/index.md")]),
            ("dist/paper/", "the paper as markdown with its bibliography", [("paper", "paper/paper.md"), ("bibtex", "paper/references.bib")]),
            ("dist/manifest.json", "per-record and dataset sha256, schema and vocab hashes", [("manifest", "manifest.json")]),
        ]
        def anchors(links):
            return " ".join(f'<a href="{esc(self.dl(h, "../"))}">{esc(n)}</a>' for n, h in links)
        frows = "".join(f'<div class="row"><div class="id">{esc(p)}</div><div><p style="color:var(--ink)">{esc(dsc)}</p></div>'
                        f'<div class="end">{anchors(links)}</div></div>' for p, dsc, links in files)
        cmds = [("git clone " + self.site["repo"], "get the repository"), ("pip install -r requirements.txt", "pinned dependencies"),
                ("make check", "validate every rule, every report and record assertion, and the generated docs"), ("python scripts/find.py production chain", "search before you create a record"),
                ("python scripts/new.py run my-run --kind catalog", "open a run before you edit data"), ("make build", "build dist/ locally, including this site; CI builds and publishes it"),
                ("make sqlite", "query everything with SQL")]
        crows = "".join(f'<div class="row"><div class="id"></div><div><code>{esc(c)}</code><span class="why">{esc(w)}</span></div></div>' for c, w in cmds)
        runs = sorted(self.ents.get("run", []), key=lambda r: (str(r.data.get("date")), r.id), reverse=True)
        rrows = "".join(f'<div class="row" data-state="done"><div class="id">{esc(r.data.get("date"))}</div><span class="dot"></span><span class="kind">{esc(r.data.get("kind"))}</span>'
                        f'<span class="what"><a href="{esc(self.gh("log/runs/" + r.id + ".yaml"))}">{esc(r.id)}</a> · {esc(r.data.get("purpose", "")[:140])}</span>'
                        f'<span class="src">{esc(r.data.get("actor", ""))}</span></div>' for r in runs)
        vrows = "".join(f'<div class="row"><div class="id">{esc(n)}</div><div><p>{esc((v.get("description") or "").strip())}</p></div><div class="end">{counted(len(v.get("terms", [])), "term")}</div></div>'
                        for n, v in sorted(self.vocabs.items()) if n not in ("rubrics",))
        why = [("one set of records", "Every game, mechanic, technique, bet, and source is one plain-text record. The paper, the book, the videos, and this site "
                                      "are all built from those records, so they cannot drift apart: change a record and every page that uses it changes with it."),
               ("sources you can open", self.sources_line()),
               ("sentences that fail loudly", "When a sentence in the paper or the book interprets the data, a check sits beside it. If new data makes the sentence "
                                              "false, the build stops until someone rewrites it, so the text stays true as the catalog grows."),
               ("open to anyone", "People and AI agents add games, sources, and checks through pull requests, under written rules. Every change is logged as a run, "
                                  "and the contributors are credited in the paper.")]
        wrows = "".join(f'<div class="row"><div class="id">{esc(h)}</div><div><p style="color:var(--ink)">{esc(t)}</p></div></div>' for h, t in why)
        body = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>about</li></ol></nav>'
                f'<div class="page-header"><p class="eyebrow"><span class="id">about</span> <span>dataset <b>{self.short}</b></span> <span>contract {esc(man["contract_version"])}</span></p>'
                f'<h1>How the atlas is made, and why you can check it</h1><p class="dek">An atlas is only useful if you can trust it. This one is built so that any number '
                f'on any page can be traced to the records and sources behind it, checked, and corrected, by anyone.</p>'
                f'<div class="meta"><span><b>{self.byline_html("../")}</b></span><span><a href="../paper/#appendix-d-contributors" data-internal>all contributors</a></span></div>'
                f'<div class="twins"><b>start with</b><a href="{esc(self.gh("AGENTS.md"))}">AGENTS.md</a><a href="{esc(self.gh("CONTRACT.md"))}">CONTRACT.md</a><a href="../llms.txt" data-internal>llms.txt</a></div></div>'
                + self.section("why it is built this way", f'<div class="register" data-size="wide">{wrows}</div>')
                + self.section("downloads", f'<div class="register" data-size="wide">{frows}</div>', "generated projections, published beside this site")
                + self.section("commands", f'<div class="register" data-kind="cmds">{crows}</div>', "from the repository root")
                + self.section("research log", f'<div class="register" data-kind="log" data-style="timeline">{rrows}</div>', f"{counted(len(runs), 'run')}, newest first")
                + self.section("vocabularies", f'<div class="register" data-size="wide">{vrows}</div>', "closed; add terms through an ADR"))
        return self.page(title="About · simgrammar", desc="How the SimGrammar atlas is made and why it can be checked: open records, downloads, commands, research log, and vocabularies.",
                         body=body, depth=1, nav="about", path="about/")

    def sources_line(self):
        """How far the records' evidence goes, in counts the build takes from the data: records that cite a source, claims
        that quote one, sources with an archived snapshot."""
        recs = [e for t in self.CARD_TYPES for e in self.ents.get(t, []) if not e.data.get("deprecated")]
        claims = [c for e in recs for c in (e.data.get("claims") or []) + (e.data.get("key_results") or [])]
        quoted = [e for e in recs if any(c.get("quote") for c in (e.data.get("claims") or []) + (e.data.get("key_results") or []))]
        srcs = [e for e in self.ents.get("source", []) if not e.data.get("deprecated")]
        nq, na = sum(1 for c in claims if c.get("quote")), sum(1 for s in srcs if s.data.get("archived"))
        archived = (f"{na} of the {counted(len(srcs), 'source')} {'has' if na == 1 else 'have'} an archived snapshot so far" if na
                    else f"none of the {counted(len(srcs), 'source')} has an archived snapshot yet")
        return (f"{sum(1 for e in recs if self.cites(e))} of the {counted(len(recs), 'record')} cite the sources their facts come from; the rest are "
                f"marked asserted until someone sources them. {nq} of the {counted(len(claims), 'claim')}, on {counted(len(quoted), 'record')}, also "
                f"quote the passage that supports them, and {archived}. A record is marked sourced when its facts have sources, and verified when "
                "someone other than its author has checked them.")

    # ------------------------------------------------------------------ watch and book pages
    def watch_page(self):
        base = "../"
        tiles, twin = [], []
        for ep in self.episodes:
            url = self.ep_url(ep, base)
            chapters = " and ".join(str(c) for c in ep["covers"])
            chlinks = " and ".join(f'<a href="{base}book/{self.chapter_of[c]}/" data-internal>{c}</a>' for c in ep["covers"] if c in self.chapter_of)
            tiles.append(f'<div class="row" id="{ep["key"]}">{self.episode_figure(ep, base, 480, url)}<p class="eyebrow"><span class="id">episode {ep["n"]}</span> '
                         f'<span>{self.mmss(ep["seconds"])}</span> <span>chapter{"s" if len(ep["covers"]) > 1 else ""} {chlinks}</span></p>'
                         f'<h3><a href="{url}" data-internal>{esc(ep["title"])}</a></h3><p>{esc(ep["summary"])}</p>{self.icon_links([i for i in ep["shows"] if self.by_id[i].type != "game"][:8], base)}</div>')
            twin.append(f'<div class="row"><div class="id">episode {ep["n"]}</div><div><h3><a href="{url}" data-internal>{esc(ep["title"])}</a></h3>'
                        f'<p>{esc(ep["summary"])}</p><p>{self.mmss(ep["seconds"])} · {counted(len(ep["scenes"]), "scene")} · follows {self.covers(ep, base)}</p></div></div>')
        stiles, stwin = [], []
        for sh in self.shorts:
            stiles.append(self.short_tile(sh, base, anchor=True))
            stwin.append(f'<div class="row"><div class="id">short {sh["n"]}</div><div><h3>{esc(sh["title"])}</h3>'
                         + "".join(f"<p>{self.voice_html(v, base)}</p>" for v in sh["voice"]) + "</div></div>")
        ne, ns = len(self.episodes), len(self.shorts)
        minutes = round(sum(ep["seconds"] for ep in self.episodes) / 60)
        episodes = self.section("episodes", f'<div class="register" data-kind="episodes">{"".join(tiles)}</div>'
                                f'<details class="disclosure"><summary>plain-text twin · {counted(ne, "episode")}</summary><div class="register">{"".join(twin)}</div></details>',
                                f"{ne} · {minutes} min in all") if ne else ""
        shorts = self.section("shorts", f'<div class="register" data-kind="watch">{"".join(stiles)}</div>'
                              f'<details class="disclosure"><summary>plain-text twin · {counted(ns, "transcript")}</summary><div class="register">{"".join(stwin)}</div></details>',
                              f"{ns} · under a minute each") if ns else ""
        h1 = (f"The book in {counted(ne, 'episode')}, and {counted(ns, 'finding')} under a minute each" if ne and ns else
              f"The book in {counted(ne, 'episode')}" if ne else f"{counted(ns, 'finding')}, under a minute each")
        body = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>watch</li></ol></nav>'
                f'<div class="page-header"><p class="eyebrow"><span class="id">watch</span> <span>{counted(ne, "episode")} · {minutes} min</span> <span>{counted(ns, "short")}</span></p><h1>{h1}</h1>'
                f'<p class="dek">The episodes follow the book chapter by chapter. The shorts each state one finding in their first sentence. '
                f'Every game, mechanic, and technique on screen links to its page, and its page links back to the moment it appears.</p></div>'
                + (episodes + shorts if ne or ns else '<p class="muted">No videos are published yet.</p>'))
        return self.page(title="Watch · simgrammar", desc=f"The SimGrammar series: {counted(ne, 'episode')} that follow the book, and {counted(ns, 'short video')}, each stating one finding from the dataset.",
                         body=body, depth=1, nav="watch", path="watch/", image="og/watch.png")

    def book_md(self, stem):
        """A rendered chapter with its links pointed at the site: records, other chapters, and the paper's figures."""
        md = self.built[f"book/{stem}.md"]
        md = re.sub(r"\]\(\.\./wiki/(\w+)/([a-z0-9-]+)\.md\)", r"](../../\1/\2/)", md)
        md = re.sub(r"\]\((\d\d-[a-z0-9-]+)\.md\)", r"](../\1/)", md)
        md = re.sub(r'^(<a id="ref-([a-z0-9-]+)"></a>\[\d+\] .*?)\*(.+?)\*', lambda m: f"{m.group(1)}*[{m.group(3)}](../../source/{m.group(2)}/)*" if m.group(2) in self.by_id else m.group(0),
                    md, flags=re.M)
        return md.replace("](../paper/figures/", "](../../figures/")

    def book_toc(self, current, base):
        links = []
        for m in re.finditer(r"^(#+ .*|\d+\. \[.*?\]\((\d\d-[a-z0-9-]+)\.md\)|\[.*?\]\((\d\d-[a-z0-9-]+)\.md\)|- \[.*?\]\((\d\d-[a-z0-9-]+)\.md\))", self.built["book/00-contents.md"], re.M):
            line = m.group(1)
            stem = m.group(2) or m.group(3) or m.group(4)
            if line.startswith("## "):
                links.append(f'<span class="toc-head">{esc(line[3:].lower())}</span>')
            elif stem:
                label = re.search(r"\[(.*?)\]", line).group(1)
                num = re.match(r"(\d+)\. ", line)
                cur = ' aria-current="true"' if stem == current else ""
                links.append(f'<a href="{base}book/{stem}/"{cur} data-internal>{esc((num.group(1) + ". ") if num else "")}{esc(label)}</a>')
        return "".join(links)

    def book_chapter(self, stem):
        base = "../../"
        mdr = MarkdownIt("commonmark", {"html": True}).enable("table")
        body = mdr.render(self.book_md(stem))
        body = body.replace("<table>", '<div class="table-wrap"><table class="data" data-style="dense">').replace("</table>", "</table></div>")
        body = re.sub(r'<tr>\s*<td><a href="\.\./\.\./(game|mechanic)/([a-z0-9-]+)/">', r'<tr id="\2">\n<td><a href="../../\1/\2/">', body)   # rows of the glossary and the catalog
        body = self.person_links(body)
        title = re.search(r"^# (.*)$", self.built[f"book/{stem}.md"], re.M).group(1)
        words = self.chapter_words(stem)
        i = self.chapters.index(stem)
        prev_, next_ = (self.chapters[i - 1] if i > 1 else None), (self.chapters[i + 1] if i + 1 < len(self.chapters) else None)
        def name_of(st):
            return re.search(r"^# (.*)$", self.built[f"book/{st}.md"], re.M).group(1)
        pager = '<nav class="pagination" aria-label="Chapters">' + (f'<a href="../{prev_}/" data-internal>← {esc(name_of(prev_))}</a>' if prev_ else "") + \
                f'<a href="../" data-internal>contents</a>' + (f'<a href="../{next_}/" data-internal>{esc(name_of(next_))} →</a>' if next_ else "") + "</nav>"
        here = {i: [r[2] for r in rs if r[0] == stem] for i, rs in self.book_refs.items() if any(r[0] == stem for r in rs)}
        rel = ""
        for t in self.CARD_TYPES:
            ids = sorted((i for i in here if self.by_id[i].type == t), key=lambda x: self.by_id[x].data["name"].lower())
            if ids:
                nl = sum(1 for i in ids if "linked from the text" in here[i])
                rel += self.section(f'{self.registry["types"][t]["plural"]} in this chapter', self.chips(ids, base),
                                    " · ".join(x for x in (f"{nl} linked" if nl else "", f"{len(ids) - nl} named" if len(ids) > nl else "") if x))
        c = int(stem[:2]) if re.match(r"(0[1-9]|1[0-9])-", stem) else None
        shorts = [sh for sh in self.shorts if sh["chapter"] == c] if c else []
        if shorts:
            rel += self.section("shorts from this chapter", f'<div class="register" data-kind="watch">{"".join(self.short_tile(sh, base) for sh in shorts)}</div>', f"{len(shorts)} · under a minute each")
        toc = self.book_toc(stem, base)
        main = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="{base}" data-internal>simgrammar</a></li><li><a href="../" data-internal>book</a></li><li>{esc(self.chapter_label(stem))}</li></ol></nav>'
                f'<div class="sidebar"><aside class="hide-md sticky"><nav class="toc" aria-label="The book">{toc}</nav></aside>'
                f'<article class="prose" style="min-width:0"><details class="disclosure show-md"><summary>the book · contents</summary><nav class="toc" aria-label="The book">{toc}</nav></details>'
                f'<p class="eyebrow"><span class="id">{esc(self.chapter_label(stem))}</span> <span>about {max(1, round(words / 230))} min</span></p>'
                f'{self.chapter_watch(stem, base) if re.match(r"(0[1-9]|1[0-9])-", stem) else ""}{body}{pager}{rel}</article></div>')
        return self.page(title=f"{title} · the book · simgrammar", desc=f"{title}, a chapter of The Grammar of Simulation, rendered from the dataset.",
                         body=main, depth=2, nav="book", path=f"book/{stem}/", image=f"og/book/{stem}.png")

    @staticmethod
    def chapter_label(stem):
        """A chapter's short name for an eyebrow or breadcrumb: "chapter 3", or the back matter's own name."""
        return f"chapter {int(stem[:2])}" if re.match(r"(0[1-9]|1[0-9])-", stem) else stem[3:].replace("-", " ")

    def byline_html(self, base):
        """The byline's names, each linked to the contributors table (paper appendix D) and opening the contributor's card on
        hover; "SimGrammar contributors", once there are more contributors than the byline names, links to the table alone."""
        handle = {r["contributor"]: r["github"] for r in self.analysis["tables"]["contributors"]["rows"]}
        return ", ".join(f'<a href="{base}paper/#appendix-d-contributors"' + (f' data-person="{esc(handle[a])}"' if a in handle else "") + f' data-internal>{esc(a)}</a>'
                         for a in self.analysis["byline"])

    def people_json(self):
        """Each contributor's card, keyed by GitHub handle, for simgrammar.js. Its twin is the contributors table."""
        cards = {r["github"]: {"name": r["contributor"], "since": r["first_run"], "runs": r["runs"], "records": r["records_created"],
                               "sources": r["sources_added"], "verified": r["records_verified"], "rated": r["scores_rated"],
                               "links": [["github", f"https://github.com/{r['github']}"]] + [[link_label(u), u] for u in r["links"]]}
                 for r in self.analysis["tables"]["contributors"]["rows"]}
        return json.dumps(cards, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")

    def person_links(self, html):
        """In markdown-rendered pages, a contributors-table name opens the contributor's card, as it does in the paper."""
        for r in self.analysis["tables"]["contributors"]["rows"]:
            h = esc(r["github"])
            html = re.sub(rf'<td>{re.escape(esc(r["contributor"]))}</td>(\s*<td><a href="https://github\.com/{re.escape(h)}">)',
                          lambda m: f'<td><a href="https://github.com/{h}" data-person="{h}">{esc(r["contributor"])}</a></td>{m.group(1)}', html)
        return html

    def book_index(self):
        base = "../"
        words = sum(len(re.sub(r"[#*\[\]()]", " ", self.built[f"book/{st}.md"].split("\n## Sources")[0]).split()) for st in self.chapters if st[:2] not in ("00", "90", "91"))
        rows = []
        for st in self.chapters:
            if st == "00-contents":
                continue
            title = re.search(r"^# (.*)$", self.built[f"book/{st}.md"], re.M).group(1)
            ep = next((e for e in self.episodes if re.match(r"(0[1-9]|1[0-9])-", st) and int(st[:2]) in e["covers"]), None)
            rows.append(f'<div class="row"><div class="id">{esc(st[:2])}</div><div><h3><a href="{st}/" data-internal>{esc(title)}</a></h3>'
                        + (f'<p>on screen in <a href="{self.ep_url(ep, base)}" data-internal>episode {ep["n"]}, {esc(ep["title"])}</a></p>' if ep else "")
                        + f'</div><div class="end">about {max(1, round(self.chapter_words(st) / 230))} min</div></div>')
        body = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>book</li></ol></nav>'
                f'<div class="page-header"><p class="eyebrow"><span class="id">book</span> <span>{sum(1 for st in self.chapters if re.match(r"(0[1-9]|1[0-9])-", st))} chapters, a preface, and back matter</span> <span>about {words // 1000}k words</span></p>'
                f'<h1>The Grammar of Simulation, as a book</h1><p class="dek">The findings at book length, for reading straight through: what the parts of a simulation game are, '
                f'what they cost, where AI changes them, and what to build next, with a glossary of every mechanic and the catalog of games.</p><div class="meta"><span><b>{self.byline_html(base)}</b></span></div></div>'
                f'<div class="register" data-size="wide">{"".join(rows)}</div>')
        return self.page(title="The book · simgrammar", desc="The Grammar of Simulation as a book, one chapter a page, rendered from the dataset.", body=body,
                         depth=1, nav="book", path="book/", image="og/book.png")

    def find_page(self):
        """Every node of the site on one page, grouped by kind; simgrammar.js filters it as you type, and ?q= starts a filter."""
        base = "../"

        def row(q, ident, href, name, sub, end="", ic=""):
            return (f'<div class="row" data-q="{esc(q.lower())}"><div class="id">{esc(ident)}</div><div><h3>{ic}<a href="{href}" data-internal>{esc(name)}</a></h3>'
                    + (f"<p>{esc(sub)}</p>" if sub else "") + f'</div><div class="end">{esc(end)}</div></div>')
        groups = []
        chs = [st for st in self.chapters if st != "00-contents"]
        rows = []
        for st in chs:
            title = re.search(r"^# (.*)$", self.built[f"book/{st}.md"], re.M).group(1)
            heads = [re.sub(r"[*`]", "", h) for h in re.findall(r"^## (.+)$", self.built[f"book/{st}.md"].split("\n## Sources")[0], re.M)]
            rows.append(row(" ".join([title, st] + heads), f"ch {int(st[:2])}" if re.match(r"(0[1-9]|1[0-9])-", st) else "", f"{base}book/{st}/", title, " · ".join(heads),
                            f"about {max(1, round(self.chapter_words(st) / 230))} min"))
        groups.append(("the book", rows))
        groups.append(("episodes", [row(" ".join([ep["title"], ep["key"], ep["summary"]]), f'ep {ep["n"]}', self.ep_url(ep, base), ep["title"], ep["summary"], self.mmss(ep["seconds"]))
                                    for ep in self.episodes]))
        groups.append(("shorts", [row(" ".join([sh["title"], sh["key"]] + sh["voice"][:1]), f'short {sh["n"]}', f"{base}watch/#{sh['key']}", sh["title"],
                                      re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", sh["voice"][0]).replace("*", "") if sh["voice"] else "", self.mmss(sh["seconds"])) for sh in self.shorts]))
        for t in self.CARD_TYPES + ("source",):
            lst = sorted((e for e in self.ents.get(t, []) if not e.data.get("deprecated")), key=lambda e: e.data.get("name", e.id).lower())
            rows = []
            for e in lst:
                d = e.data
                if t == "source":
                    sub = " · ".join(x for x in (", ".join(d.get("authors", [])[:3]), str(d.get("date", "")), d.get("venue", "")) if x)
                    rows.append(row(" ".join([d.get("name", e.id), e.id, sub]), "", f"{base}source/{e.id}/", d.get("name", e.id), sub, d.get("kind", "")))
                else:
                    ic = self.card_icon(e, base, 24)
                    rows.append(row(" ".join([d["name"], e.id, self.card_line(e)] + (d.get("aliases") or [])), "", f"{base}{t}/{e.id}/", d["name"],
                                    d.get("summary", ""), self.card_line(e), ic))
            groups.append((self.registry["types"][t]["plural"], rows))
        n = sum(len(r) for _, r in groups)
        body = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>find</li></ol></nav>'
                f'<div class="page-header"><p class="eyebrow"><span class="id">find</span> <span>{counted(n, "page")}</span></p><h1>Find anything on this site</h1>'
                f'<p class="dek">Every chapter, episode, short, game, mechanic, technique, opportunity, and source, each linked to its page. '
                f'Type to filter by name, alias, or summary; each page links on to everything related to it.</p></div>'
                f'<div class="controls" data-filter-controls hidden><label class="field"><span>filter</span><input type="search" data-filter placeholder="type a name, an id, or a word"></label></div>'
                + self.no_match("No page matches that filter.")
                + f'<div data-filter-scope>' + "".join(self.group(f'{esc(title)} <span data-count>· {len(rows)}</span>', self.find_list(title, rows)) for title, rows in groups if rows) + "</div>")
        return self.page(title="Find · simgrammar", desc=f"Every page of the SimGrammar site in one filterable list: {n} chapters, videos, records, and sources.",
                         body=body, depth=1, nav="find", path="find/")

    @staticmethod
    def find_list(title, rows):
        """A find group's rows; the sources, by far the longest list, stay folded until opened or a filter matches one."""
        reg = f'<div class="register" data-size="wide">{"".join(rows)}</div>'
        return f'<details class="disclosure" data-filter-open><summary>show all {len(rows)}</summary>{reg}</details>' if title == "sources" else reg

    def llms_txt(self):
        m, man = self.meta, self.manifest
        lines = [f"# simgrammar · {m['title']}", "", f"> {m['subtitle']}. A versioned dataset of simulation game mechanics with provenance, and the paper projected from it.", "",
                 f"dataset sha256: {man['dataset_sha256']}", f"contract: {man['contract_version']} · paper v{m['version']} ({m['date']})", "",
                 "## Read", f"- {self.site['url']}paper/: the paper", f"- {self.site['url']}paper.md: the paper as markdown", f"- {self.site['url']}references.bib: bibliography", f"- {self.site['url']}manifest.json: counts and hashes",
                 f"- {self.site['url']}book/: the book, one chapter a page", f"- {self.site['url']}watch/: the episodes and shorts, with transcripts", f"- {self.site['url']}find/: every page of the site in one list", "",
                 "## Data", f"- {self.site['url']}dist/simgrammar-dist.zip: every projection in one archive",
                 f"- {self.site['url']}dist/tables/games.csv (and mechanics, techniques, opportunities, sources, edges, game_mechanic_matrix): csv tables",
                 f"- {self.site['url']}dist/entities/games.json (and the other types): full json records",
                 f"- {self.site['url']}dist/graph/nodes.jsonl, edges.jsonl: the graph", f"- {self.site['url']}about/: how the atlas is made, every download, the research log, the vocabularies", "",
                 "## Contribute", f"- {self.site['repo']}/blob/main/AGENTS.md: procedure for humans and agents", f"- {self.site['repo']}/blob/main/CONTRACT.md: invariants and validator rules", ""]
        return "\n".join(lines)

    def not_found(self):
        body = ('<div class="page-header"><p class="eyebrow"><span class="id">404</span></p><h1>No record at this address</h1>'
                '<p class="dek">Record ids never change once merged, so this address never held a page, or the record was deprecated before it was published.</p>'
                '<div class="actions"><a class="btn" href="/" data-internal>Back to the start</a></div></div>')
        return self.page(title="Not found · simgrammar", desc="Page not found.", body=body, depth=0, nav="", path="404.html").replace('href="assets/', 'href="/assets/').replace('src="assets/', 'src="/assets/')


def favicon(png: bytes) -> bytes:
    """The 192 px icon raster sampled every fourth pixel: 48 px, one pixel per dither pixel."""
    import io
    from PIL import Image
    out = io.BytesIO()
    Image.open(io.BytesIO(png)).resize((48, 48), Image.NEAREST).save(out, format="PNG")
    return out.getvalue()


def build_web(ents, edges, analysis, vocabs, registry, schemas, ctx, manifest, meta, paper_md, references_bib, figure_svgs, built=None) -> dict[str, str | bytes]:
    w = Web(ents, edges, analysis, vocabs, registry, schemas, ctx, manifest, meta, built)
    outs = {}
    outs["web/paper/index.html"] = w.paper()   # first: it records which records each section links, for the record pages
    outs["web/index.html"] = w.home()
    for t in w.types:
        outs[f"web/{t}/index.html"] = w.index(t)
        for e in sorted(ents.get(t, []), key=lambda e: e.id):
            outs[f"web/{t}/{e.id}/index.html"] = w.entity(e)
    outs["web/about/index.html"] = w.about_page()
    outs["web/find/index.html"] = w.find_page()
    outs["web/watch/index.html"] = w.watch_page()
    for ep in w.episodes:
        outs[f"web/watch/{ep['key']}/index.html"] = w.episode_page(ep)
        for _, _, path, vtt in ep["tracks"]:   # built with the site, so the Pages deploy serves them beside the fetched videos
            outs[f"web/{path}"] = vtt
    if w.chapters:
        outs["web/book/index.html"] = w.book_index()
        for stem in w.chapters:
            if stem != "00-contents":
                outs[f"web/book/{stem}/index.html"] = w.book_chapter(stem)
    outs["web/404.html"] = w.not_found()
    outs["web/llms.txt"] = w.llms_txt()
    # the paper's entity links point into dist/wiki; on the site they point at the record pages
    outs["web/paper.md"] = re.sub(r"\]\(\.\./wiki/([a-z]+)/([a-z0-9-]+)\.md\)", lambda m: f"]({meta['site']['url']}{m.group(1)}/{m.group(2)}/)", paper_md)
    outs["web/references.bib"] = references_bib
    outs["web/manifest.json"] = json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    for name, svg in figure_svgs.items():
        outs[f"web/figures/{name}.svg"] = svg
    outs["web/CNAME"] = meta["site"]["domain"] + "\n"
    root = meta["site"]["url"]
    pages = sorted(k[len("web/"):-len("index.html")] for k in outs if k.startswith("web/") and k.endswith("index.html"))
    outs["web/sitemap.xml"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                               + "".join(f"  <url><loc>{esc(root + p)}</loc></url>\n" for p in pages) + "</urlset>\n")
    outs["web/robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: {root}sitemap.xml\n"
    outs["web/.nojekyll"] = ""
    for f in ("register.css", "simgrammar.js"):
        outs[f"web/assets/{f}"] = (WEB_SRC / f).read_text(encoding="utf-8")
    for i in sorted(w.icons):
        outs[f"web/assets/icons/{i}.png"] = w.built[f"visual/icons/{i}@4x.png"]
    if FAVICON in w.icons:
        outs["web/assets/favicon.png"] = favicon(w.built[f"visual/icons/{FAVICON}@4x.png"])
    if w.icons:
        import og
        outs.update(og.images(w))
    return outs
