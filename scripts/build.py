#!/usr/bin/env python3
"""Project data/ into every output format. Deterministic: same data -> byte-identical dist/.

  python scripts/build.py              write dist/ and refresh GENERATED blocks in README.md, CONTRACT.md, AGENTS.md
  python scripts/build.py --check      build in memory; exit 1 if a GENERATED block is stale (E023). Writes nothing.
  python scripts/build.py --out DIR    write the projections to DIR instead of dist/ (CI builds twice under different
                                       PYTHONHASHSEED values and diffs the two trees to prove determinism, I11)
  python scripts/build.py --sqlite     also write dist/simgrammar.sqlite

dist/ is not committed (ADR-0004). CI builds it on every push and the Pages workflow publishes dist/web as the site
with the other projections under /dist/.

Projections:
  dist/manifest.json                 counts, schema/vocab hashes, per-entity and dataset sha256
  dist/entities/<plural>.json        full entities + `_derived`
  dist/tables/*.csv                  one flat table per type, edges.csv, game_mechanic_matrix.csv
  dist/graph/                        nodes.jsonl, edges.jsonl, cytoscape.json, graph.graphml
  dist/analysis/                     stats.json, <table>.csv, figures/*.svg
  dist/wiki/                         one markdown page per entity and vocab, with computed backlinks
  dist/paper/                        paper.md (rendered report), references.bib, figures/
  dist/book/, dist/media/episodes/   book chapters (book/src) and episode scripts (media/episodes), rendered
  dist/site/data.json                compact bundle for site/index.html
  dist/visual/                       the video icons from media/visual, dithered (scripts/visual, ADR-0006)
  dist/web/                          the website: paper with interactive figures, the book, a page per record with its icon,
                                     icon indexes, the watch page, link-preview images (scripts/web.py, scripts/og.py)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze  # noqa: E402
import validate  # noqa: E402
from lib import (  # noqa: E402
    ROOT,
    canonical_json,
    extract_edges,
    load_entities,
    load_registry,
    load_schemas,
    load_vocabs,
    pretty_json,
    read_yaml,
    replace_generated_blocks,
    sha256,
    to_csv,
    vocab_terms,
)
from report_render import Context, link_label, render  # noqa: E402
from rules import RULES  # noqa: E402
from web import build_web  # noqa: E402

DIST = ROOT / "dist"
GENERATED_DOCS = ["README.md", "CONTRACT.md", "AGENTS.md"]
REQUIRED_BLOCKS = {"CONTRACT.md": ["rules", "edge-types", "vocab-index", "rubric-index"]}


def entity_record(e, derived):
    rec = dict(e.data)
    rec["_derived"] = derived.get(e.id, {})
    return rec


def flat_columns(schema: dict) -> list[str]:
    cols = []
    for k, v in schema.get("properties", {}).items():
        if k in ("claims", "deprecated"):
            continue
        cols.append(k)
    return cols


def flatten(e, cols, derived):
    row = {}
    for c in cols:
        v = e.data.get(c)
        if c == "provenance" and isinstance(v, dict):
            v = v.get("created")
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            if c == "mechanics":
                row["mechanics_core"] = [x["id"] for x in v if x.get("role") == "core"]
                row["mechanics_supporting"] = [x["id"] for x in v if x.get("role") != "core"]
                continue
            v = [x.get("id") for x in v]
        elif isinstance(v, dict):
            v = canonical_json(v)
        row[c] = v
    for k, v in derived.get(e.id, {}).items():
        if not isinstance(v, dict):
            row[k] = v
    row["deprecated"] = bool(e.data.get("deprecated"))
    return row


def wiki_page(e, ctx: Context, vocabs, registry, schemas, edges_out, analysis) -> str:
    d = e.data
    terms_cache = {}

    def term_label(vname, t):
        if vname not in terms_cache:
            terms_cache[vname] = vocab_terms(vocabs, vname)
        return terms_cache[vname].get(str(t), {}).get("label", t)

    sfile = Path(registry["types"][e.type]["schema"]).name
    props = schemas[sfile]["properties"]
    lines = [f"# {d.get('name', e.id)}", ""]
    if d.get("deprecated"):
        lines += [f"> **Deprecated.** Superseded by [[{d['deprecated']['superseded_by']}]]: {d['deprecated']['reason']}", ""]
    lines += [f"*{registry['types'][e.type]['label']}* · `{e.id}` · status: **{d.get('status', 'n/a')}**", ""]
    if d.get("summary"):
        lines += [d["summary"], ""]
    # facts table: scalar and vocab fields
    facts = []
    for k, sch in props.items():
        if k in ("id", "type", "name", "summary", "status", "provenance", "sources", "claims", "deprecated", "assertions", "ratings", "store_ids"):
            continue
        v = d.get(k)
        if v is None:
            continue
        vn = sch.get("x-vocab") or (sch.get("items") or {}).get("x-vocab")
        if isinstance(v, list) and v and isinstance(v[0], dict):
            continue
        if isinstance(v, str) and len(v) > 160:
            continue
        if isinstance(v, list) and v and isinstance(v[0], str) and len(" ".join(v)) > 160 and not vn:
            continue
        if vn:
            v = ", ".join(term_label(vn, x) for x in v) if isinstance(v, list) else term_label(vn, v)
        elif isinstance(v, list):
            v = ", ".join(f"[[{x}]]" if x in ctx.by_id else str(x) for x in v)
        elif isinstance(v, str) and v in ctx.by_id and k not in ("developer",):
            v = f"[[{v}]]"
        facts.append(f"| {k.replace('_', ' ')} | {v} |")
    der = analysis["derived"].get(e.id, {})
    for k, v in der.items():
        if isinstance(v, (int, float, str)) and v is not None:
            vv = f"[[{v}]]" if isinstance(v, str) and v in ctx.by_id else v
            facts.append(f"| {k.replace('_', ' ')} *(computed)* | {vv} |")
    if facts:
        lines += ["| field | value |", "|---|---|", *facts, ""]
    # long text fields
    for k, sch in props.items():
        v = d.get(k)
        if k in ("store_ids", "assertions", "ratings"):
            if not v:
                continue
            if k == "store_ids" and isinstance(v, dict):
                lines += ["## Store ids", ""] + [f"- {store}: `{sid}`" for store, sid in sorted(v.items())] + [""]
            if k == "assertions" and v:
                lines += ["## Checks against the data", "", "The build fails (E032) if any of these stops holding.", ""] + [f"- `{x}`" for x in v] + [""]
            if k == "ratings" and v:
                lines += ["## Ratings", ""] + [f"- {r['field']} = {r['value']} (run `{r['run']}`): {r['rationale']}" for r in v] + [""]
        elif isinstance(v, str) and len(v) > 160:
            lines += [f"## {k.replace('_', ' ').title()}", "", v, ""]
        elif isinstance(v, list) and v and isinstance(v[0], str) and not (sch.get("items") or {}).get("x-vocab") and not (sch.get("items") or {}).get("x-edge") and "$ref" not in (sch.get("items") or {}):
            if len(" ".join(v)) > 160 or k in ("design_levers", "failure_modes", "dynamics", "limitations", "key_risks", "open_questions"):
                lines += [f"## {k.replace('_', ' ').title()}", ""] + [f"- {x}" for x in v] + [""]
        elif k == "falsifiable_signal" and isinstance(v, dict):
            lines += ["## Falsifiable signal", "", f"- **Prediction:** {v['prediction']}", f"- **Resolve by:** {v['resolve_by']}", f"- **Criteria:** {v['criteria']}"]
            r = v.get("resolution")
            lines += [f"- **Outcome:** {r['outcome']} ({r['date']}, run `{r['run']}`){': ' + '; '.join(f'[[{x}]]' for x in r.get('evidence') or []) if r.get('evidence') else ''}. {r['note']}"] if r else ["- **Outcome:** open"]
            lines.append("")

    # outgoing edges with attributes
    out = defaultdict(list)
    for ed in edges_out.get(e.id, []):
        if ed.type == "cites":
            continue
        a = ed.attr_dict()
        extra = []
        if "role" in a:
            extra.append(a["role"])
        if "effect" in a:
            extra.append(term_label("effect", a["effect"]))
        txt = f"[[{ed.target}]]" + (f" ({', '.join(extra)})" if extra else "") + (f": {a['note']}" if a.get("note") else "")
        out[ed.type].append(txt)
    et = vocab_terms(vocabs, "edge_types")
    if out:
        lines += ["## Relations", ""]
        for t in sorted(out):
            lines += [f"**{et[t]['label']}**", ""] + [f"- {x}" for x in out[t]] + [""]
    inc = der.get("incoming", {})
    if inc:
        lines += ["## Backlinks (computed)", ""]
        for t, ids in inc.items():
            lines += [f"**{t.replace('_', ' ')}:** " + ", ".join(f"[[{x}]]" for x in ids), ""]
    if d.get("claims") or d.get("key_results"):
        lines += ["## Claims", ""]
        for c in (d.get("key_results") or []) + (d.get("claims") or []):
            srcs = "; ".join(f"@{s}" for s in c["sources"])
            lines.append(f"- {c['text']} *(confidence: {c['confidence']})* [{srcs}]" + (f" Quote: \"{c['quote']}\"" + (f" ({c['locator']})" if c.get("locator") else "") if c.get("quote") else "")
                         + (f" **Disputed:** {c['disputes']}" if c.get("disputes") else ""))
        lines.append("")
    if d.get("sources"):
        lines += ["## Sources", ""] + [f"- [[{s}]]" for s in d["sources"]] + [""]
    if e.type == "source":
        loc = d.get("url") or (f"https://doi.org/{d['doi']}" if d.get("doi") else None) or (f"https://arxiv.org/abs/{d['arxiv']}" if d.get("arxiv") else None)
        lines += ["## Citation", "", f"{', '.join(d.get('authors', []))} ({d.get('date')}). *{d['name']}*. {d.get('venue', '')} {loc or ''}", ""]
        if d.get("archived"):
            lines += [f"Archived: {d['archived']}", ""]
    prov = d.get("provenance", {})
    lines += ["---", f"Provenance: created in run `{prov.get('created')}`" + (f"; reviewed in {', '.join('`'+r+'`' for r in prov.get('reviewed', []))}" if prov.get("reviewed") else "") + ".", ""]
    text, _ = render("\n".join(lines), ctx, "wiki")
    return text


def graphml(nodes, edges) -> str:
    keys = [("type", "node"), ("name", "node"), ("group", "node"), ("etype", "edge")]
    out = ["<?xml version='1.0' encoding='UTF-8'?>", "<graphml xmlns='http://graphml.graphdrawing.org/xmlns'>"]
    for k, dom in keys:
        out.append(f"  <key id='{k}' for='{dom}' attr.name='{k}' attr.type='string'/>")
    out.append("  <graph id='simgrammar' edgedefault='directed'>")
    for n in nodes:
        out.append(f"    <node id='{escape(n['id'])}'><data key='type'>{escape(n['type'])}</data><data key='name'>{escape(n['name'])}</data><data key='group'>{escape(str(n.get('group') or ''))}</data></node>")
    for i, ed in enumerate(edges):
        out.append(f"    <edge id='e{i}' source='{escape(ed['source'])}' target='{escape(ed['target'])}'><data key='etype'>{escape(ed['type'])}</data></edge>")
    out += ["  </graph>", "</graphml>", ""]
    return "\n".join(out)


def bibtex(src) -> str:
    d = src.data
    kind = {"paper": "article", "preprint": "misc", "book": "book"}.get(d["kind"], "misc")
    f = [f"  title = {{{d['name']}}}"]
    if d.get("authors"):
        f.append(f"  author = {{{' and '.join(d['authors'])}}}")
    f.append(f"  year = {{{str(d['date'])[:4]}}}")
    if d.get("venue"):
        f.append(f"  howpublished = {{{d['venue']}}}")
    if d.get("url"):
        f.append(f"  url = {{{d['url']}}}")
    if d.get("doi"):
        f.append(f"  doi = {{{d['doi']}}}")
    if d.get("arxiv"):
        f.append(f"  eprint = {{{d['arxiv']}}}")
        f.append("  archivePrefix = {arXiv}")
    f.append(f"  note = {{Accessed {d['accessed']}}}")
    return f"@{kind}{{{d['id']},\n" + ",\n".join(f) + "\n}\n"


def generated_blocks(ents, analysis, vocabs, registry) -> dict[str, str]:
    st = analysis["stats"]
    blocks = {}
    rows = ["| Entity type | Count | Sourced or verified |", "|---|---:|---:|"]
    for t, spec in registry["types"].items():
        if spec.get("meta"):
            continue
        lst = [e for e in ents.get(t, []) if not e.data.get("deprecated")]
        sv = sum(1 for e in lst if e.data.get("status") in ("sourced", "verified")) if t != "source" else len(lst)
        rows.append(f"| {spec['plural']} | {len(lst)} | {sv} |")
    rows.append(f"| runs (provenance log) | {len(ents.get('run', []))} | n/a |")
    rows.append("")
    rows.append(f"Typed edges: **{st.get('n_edges', 0)}** · game→mechanic uses: **{st.get('n_uses_edges', 0)}** · games span **{st.get('year_min')}–{st.get('year_max')}**.")
    blocks["stats"] = "\n".join(rows)
    r = ["| Rule | Name | Check | Fix |", "|---|---|---|---|"]
    for code, spec in RULES.items():
        r.append(f"| {code} | {spec['name']} | {spec['check']} | {spec['fix']} |")
    blocks["rules"] = "\n".join(r)
    et = ["| Edge | Owner → Target | Inverse (computed) | Symmetric | Meaning |", "|---|---|---|---|---|"]
    for t in vocabs["edge_types"]["terms"]:
        et.append(f"| `{t['id']}` | {t['owner']} → {t['target']} | `{t['inverse']}` | {'yes' if t['symmetric'] else 'no'} | {t['definition']} |")
    blocks["edge-types"] = "\n".join(et)
    vi = ["| Vocabulary | Terms | Description |", "|---|---:|---|"]
    for name, v in sorted(vocabs.items()):
        if name == "rubrics":
            continue
        vi.append(f"| [`{name}`](vocab/{name}.yaml) | {len(v.get('terms', []))} | {v.get('description', '').strip()} |")
    blocks["vocab-index"] = "\n".join(vi)
    ri = ["| Scale | Applies to | Question |", "|---|---|---|"]
    for name, s in vocabs["rubrics"]["scales"].items():
        ri.append(f"| `{name}` | {s['applies_to']} | {s['question']} |")
    blocks["rubric-index"] = "\n".join(ri)
    # names and links only: run counts would change this committed block in every PR (the paper and book tables carry them)
    cr = ["| contributor | github | first run | links |", "|---|---|---|---|"]
    for row in analysis["tables"]["contributors"]["rows"]:
        h = row["github"]
        links = " · ".join(f"[{link_label(u)}]({u})" for u in row["links"])
        cr.append(f"| {row['contributor']} | [{h}](https://github.com/{h}) | {row['first_run']} | {links} |")
    blocks["contributors"] = "\n".join(cr)
    site = (read_yaml(ROOT / "report" / "meta.yaml") or {})["site"]["url"]
    bl = [f"[{a}]({site}paper/#appendix-d-contributors)" if a == "SimGrammar contributors" else a for a in analysis["byline"]]
    blocks["byline"] = "By " + (", ".join(bl[:-1]) + (", and " if len(bl) > 2 else " and ") + bl[-1] if len(bl) > 1 else "".join(bl)) + "."
    return blocks


def build() -> tuple[dict[str, str | bytes], dict[str, str]]:
    registry = load_registry()
    vocabs = load_vocabs()
    schemas = load_schemas()
    ents, _ = load_entities(registry)
    data_types = [t for t, s in registry["types"].items() if not s.get("meta")]
    edges = [ed for t in data_types for e in ents.get(t, []) for ed in extract_edges(e, schemas, registry)]
    analysis = analyze.compute(ents, edges, vocabs)
    derived = analysis["derived"]
    ctx = Context(ents, edges, analysis, vocabs, registry)
    by_id = ctx.by_id
    outs: dict[str, str] = {}

    # ---- entities + tables
    for t in data_types:
        spec = registry["types"][t]
        lst = sorted(ents.get(t, []), key=lambda e: e.id)
        outs[f"entities/{spec['plural']}.json"] = pretty_json([entity_record(e, derived) for e in lst])
        sch = schemas[Path(spec["schema"]).name]
        cols = flat_columns(sch)
        rows = [flatten(e, cols, derived) for e in lst]
        allcols = []
        for r in rows:
            for k in r:
                if k not in allcols:
                    allcols.append(k)
        outs[f"tables/{spec['plural']}.csv"] = to_csv(rows, allcols)
    erows = [{"source": ed.source, "source_type": by_id[ed.source].type, "type": ed.type, "target": ed.target,
              "target_type": by_id[ed.target].type if ed.target in by_id else "", **{k: v for k, v in ed.attrs}} for ed in edges]
    erows.sort(key=lambda r: (r["type"], r["source"], r["target"]))
    outs["tables/edges.csv"] = to_csv(erows, ["source", "source_type", "type", "target", "target_type", "role", "effect", "note"])
    games = sorted(ents.get("game", []), key=lambda e: e.id)
    mechs = sorted(ents.get("mechanic", []), key=lambda e: e.id)
    mrows = []
    for g in games:
        roles = {m["id"]: (2 if m["role"] == "core" else 1) for m in g.data.get("mechanics", [])}
        mrows.append({"game": g.id, **{m.id: roles.get(m.id, 0) for m in mechs}})
    outs["tables/game_mechanic_matrix.csv"] = to_csv(mrows, ["game"] + [m.id for m in mechs])

    # ---- graph
    group_field = {"game": "subgenre", "mechanic": "family", "technique": "category", "opportunity": "opportunity_type", "source": "kind"}
    nodes = []
    for t in data_types:
        for e in sorted(ents.get(t, []), key=lambda e: e.id):
            n = {"id": e.id, "type": t, "name": e.data.get("name"), "summary": e.data.get("summary"), "group": e.data.get(group_field.get(t, ""))}
            for k in ("prevalence", "priority", "technique_exposure", "cluster"):
                if k in derived.get(e.id, {}):
                    n[k] = derived[e.id][k]
            nodes.append(n)
    gedges = [{"source": ed.source, "target": ed.target, "type": ed.type, **({"attrs": ed.attr_dict()} if ed.attrs else {})} for ed in edges]
    gedges.sort(key=lambda r: (r["type"], r["source"], r["target"]))
    outs["graph/nodes.jsonl"] = "".join(canonical_json(n) + "\n" for n in nodes)
    outs["graph/edges.jsonl"] = "".join(canonical_json(x) + "\n" for x in gedges)
    cy = {"elements": {"nodes": [{"data": n} for n in nodes],
                       "edges": [{"data": {"id": f"{x['type']}:{x['source']}->{x['target']}", **{k: v for k, v in x.items() if k != 'attrs'}}} for x in gedges]}}
    outs["graph/cytoscape.json"] = pretty_json(cy)
    outs["graph/graph.graphml"] = graphml(nodes, gedges)

    # ---- analysis
    outs["analysis/stats.json"] = pretty_json(analysis["stats"])
    for name, tb in sorted(analysis["tables"].items()):
        outs[f"analysis/{name}.csv"] = to_csv(tb["rows"], tb["columns"])
    for name, fig in sorted(analysis["figures"].items()):
        outs[f"analysis/figures/{name}.svg"] = fig["svg"]
        outs[f"paper/figures/{name}.svg"] = fig["svg"]
    for name, vz in sorted(analysis.get("vizzes", {}).items()):
        outs[f"analysis/figures/viz-{name}.svg"] = vz["svg"] + "\n"
        outs[f"paper/figures/viz-{name}.svg"] = vz["svg"] + "\n"

    # ---- wiki
    edges_out = defaultdict(list)
    for ed in edges:
        edges_out[ed.source].append(ed)
    idx = ["# SimGrammar wiki", "", "Generated from `data/` by `scripts/build.py`. Do not edit; edit the YAML and rebuild.", ""]
    for t in data_types:
        spec = registry["types"][t]
        lst = sorted((e for e in ents.get(t, []) if not e.data.get("deprecated")), key=lambda e: (e.data.get("name") or e.id).lower())
        idx.append(f"## [{spec['plural'].title()}]({t}/index.md) ({len(lst)})")
        tl = [f"# {spec['plural'].title()}", "", "| name | summary |", "|---|---|"]
        for e in lst:
            tl.append(f"| [{e.data.get('name')}]({e.id}.md) | {(e.data.get('summary') or '').replace('|', '/')} |")
            outs[f"wiki/{t}/{e.id}.md"] = wiki_page(e, ctx, vocabs, registry, schemas, edges_out, analysis)
        outs[f"wiki/{t}/index.md"] = "\n".join(tl) + "\n"
    idx += ["", "## Vocabularies", ""]
    for name, v in sorted(vocabs.items()):
        if name == "rubrics":
            continue
        idx.append(f"- [{name}](vocab/{name}.md)")
        vl = [f"# Vocabulary: {name}", "", v.get("description", "").strip(), "", "| id | label | definition |", "|---|---|---|"]
        for term in v.get("terms", []):
            vl.append(f"| `{term['id']}` | {term.get('label', '')} | {term.get('definition', '')} |")
        outs[f"wiki/vocab/{name}.md"] = "\n".join(vl) + "\n"
    outs["wiki/index.md"] = "\n".join(idx) + "\n"

    # ---- paper
    meta = read_yaml(ROOT / "report" / "meta.yaml")
    ctx.citations = []
    parts = []
    for p in sorted((ROOT / "report" / "src").glob("*.md")):
        txt, _ = render(p.read_text(encoding="utf-8"), ctx, "paper")
        parts.append(txt.strip() + "\n")
    fm = ["---", f"title: \"{meta['title']}\"", f"subtitle: \"{meta.get('subtitle', '')}\"", "author:"] + [f"  - {a}" for a in analysis["byline"]] + \
         [f"date: \"{meta['date']}\"", f"version: \"{meta['version']}\"", f"dataset_sha256: \"{{DATASET}}\"", "bibliography: references.bib", "---", ""]
    refs = ["", "## References", ""]
    for i, sid in enumerate(ctx.citations, start=1):
        s = by_id[sid].data
        loc = s.get("url") or (f"https://doi.org/{s['doi']}" if s.get("doi") else "") or (f"https://arxiv.org/abs/{s['arxiv']}" if s.get("arxiv") else "")
        refs.append(f"<a id=\"ref-{sid}\"></a>[{i}] {', '.join(s.get('authors', [])[:6])}{' et al.' if len(s.get('authors', [])) > 6 else ''} ({s['date']}). *{s['name']}*. {s.get('venue', '')} {loc}  ")
    paper = "\n".join(fm) + "\n".join(parts) + "\n".join(refs) + "\n"
    srcs = sorted(ents.get("source", []), key=lambda e: e.id)
    outs["paper/references.bib"] = "\n".join(bibtex(s) for s in srcs)

    # ---- book chapters and episode scripts: same tokens and checks as the paper, one file per chapter or episode
    PAPER_TO_BOOK = {"§5.2": "chapter 3", "§5.4": "chapter 4", "§5.5": "chapter 9", "§5.6": "chapter 5", "§8.2": "chapter 8"}
    for d, out_dir in (("book/src", "book"), ("media/episodes", "media/episodes"), ("media/shorts", "media/shorts"), ("media/mega", "media/mega"),
                       ("media/subtitles/ja", "media/subtitles/ja")):
        for p in sorted((ROOT / d).glob("*.md")):
            ctx.citations = []
            txt, _ = render(p.read_text(encoding="utf-8"), ctx, "paper")
            notes = []
            for i, sid in enumerate(ctx.citations, start=1):
                s = by_id[sid].data
                loc = s.get("url") or (f"https://doi.org/{s['doi']}" if s.get("doi") else "") or (f"https://arxiv.org/abs/{s['arxiv']}" if s.get("arxiv") else "")
                notes.append(f"<a id=\"ref-{sid}\"></a>[{i}] {', '.join(s.get('authors', [])[:6])}{' et al.' if len(s.get('authors', [])) > 6 else ''} ({s['date']}). *{s['name']}*. {s.get('venue', '')} {loc}  ")
            up = "../" if out_dir == "book" else "../../"
            txt = txt.replace("](figures/", f"]({up}paper/figures/")
            for sec, chap in PAPER_TO_BOOK.items():  # figure captions written for the paper cite its sections
                txt = txt.replace(sec, chap)
            if out_dir != "book":
                txt = txt.replace("](../wiki/", "](../../wiki/")
            body = txt.strip() + "\n" + (("\n## Sources\n\n" + "\n".join(notes) + "\n") if notes else "")
            outs[f"{out_dir}/{p.name}"] = body + "\n*Dataset {DATASET}.*\n"

    # ---- subtitles: cues rendered above, timed from the matching episode's scene timings
    import subtitles
    for k in sorted(k for k in outs if k.startswith("media/subtitles/") and k.endswith(".md")):
        script = outs.get("media/episodes/" + k.rsplit("/", 1)[1])
        if script:
            outs[k[:-3] + ".srt"] = subtitles.srt(script, outs[k])

    # ---- manifest (dataset certificate)
    ent_hashes = {}
    for t in data_types:
        for e in ents.get(t, []):
            ent_hashes[e.id] = sha256(canonical_json(e.data))
    dataset = sha256(canonical_json(sorted(ent_hashes.items())))
    paper = paper.replace("{DATASET}", dataset)
    for k in [k for k in outs if k.startswith(("book/", "media/"))]:
        outs[k] = outs[k].replace("{DATASET}", dataset[:12])
    outs["paper/paper.md"] = paper
    manifest = {
        "contract_version": registry["contract_version"],
        "dataset_sha256": dataset,
        "counts": {t: len(ents.get(t, [])) for t in registry["types"]},
        "edges": len(edges),
        "schemas": {p.name: sha256(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "schema").glob("*.json"))},
        "vocab": {p.name: sha256(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "vocab").glob("*.yaml"))},
        "entities": dict(sorted(ent_hashes.items())),
        "generator": "scripts/build.py",
    }
    outs["manifest.json"] = pretty_json(manifest)

    # ---- site bundle
    site = {
        "manifest": {k: manifest[k] for k in ("contract_version", "dataset_sha256", "counts", "edges")},
        "vocab": {n: {str(t["id"]): t.get("label", t["id"]) for t in v.get("terms", [])} for n, v in vocabs.items() if n != "rubrics"},
        "rubrics": vocabs["rubrics"]["scales"],
        "entities": {registry["types"][t]["plural"]: [entity_record(e, derived) for e in sorted(ents.get(t, []), key=lambda e: e.id)] for t in data_types},
        "edges": gedges,
        "stats": analysis["stats"],
        "tables": analysis["tables"],
        "figures": {k: v["caption"] for k, v in analysis["figures"].items()},
        "figure_svgs": {k: v["svg"] for k, v in analysis["figures"].items()},
        "paper": paper,
    }
    outs["site/data.json"] = canonical_json(site) + "\n"

    # ---- visual vocabulary (dist/visual): icons for the video frames, PNG bytes (ADR-0006)
    from visual import icons as visual_icons
    outs.update(visual_icons.outputs())

    # ---- website (dist/web): the paper, the book, a page per record, indexes, data and watch pages; deployed by .github/workflows/pages.yml.
    # It reads the icons, the rendered book chapters and the short scripts from this build.
    figs = {k[len("paper/figures/"):-4]: v for k, v in outs.items() if k.startswith("paper/figures/")}
    outs.update(build_web(ents, edges, analysis, vocabs, registry, schemas, ctx, manifest, meta, paper, outs["paper/references.bib"], figs, built=outs))

    # ---- every element a Frame line draws has an icon (E042): the frames resolve against this build, as the renderer's do
    from visual import check as visual_check
    blank = visual_check.frame_icons(outs)
    if blank:
        raise SystemExit("\n".join(f"E042 frame-icon: {m}" for m in blank) + f"\nbuild aborted: {len(blank)} Frame element(s) would draw as a blank tile")

    docs = {}
    blocks = generated_blocks(ents, analysis, vocabs, registry)
    for name in GENERATED_DOCS:
        p = ROOT / name
        if p.exists():
            new, unknown = replace_generated_blocks(p.read_text(encoding="utf-8"), blocks)
            if unknown:
                raise SystemExit(f"{name}: unknown GENERATED block(s): {unknown}")
            for req in REQUIRED_BLOCKS.get(name, []):
                if f"<!-- BEGIN GENERATED: {req} -->" not in new or f"<!-- END GENERATED: {req} -->" not in new:
                    raise SystemExit(f"E023 build: {name} is missing the required GENERATED block '{req}'; restore the BEGIN/END markers")
            docs[name] = new
    return outs, docs


def write_sqlite(path: Path):
    registry = load_registry()
    ents, _ = load_entities(registry)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    for t, spec in registry["types"].items():
        con.execute(f"CREATE TABLE {spec['plural']} (id TEXT PRIMARY KEY, json TEXT)")
        con.executemany(f"INSERT INTO {spec['plural']} VALUES (?, ?)", [(e.id, json.dumps(e.data, ensure_ascii=False)) for e in ents.get(t, [])])
    import csv
    with (path.parent / "tables" / "edges.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    con.execute("CREATE TABLE edges (source TEXT, source_type TEXT, type TEXT, target TEXT, target_type TEXT, role TEXT, effect TEXT, note TEXT)")
    con.executemany("INSERT INTO edges VALUES (?,?,?,?,?,?,?,?)", [tuple(r[k] for k in ["source", "source_type", "type", "target", "target_type", "role", "effect", "note"]) for r in rows])
    con.commit()
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--sqlite", action="store_true")
    ap.add_argument("--out", type=Path, default=DIST, help="output directory (default dist/)")
    args = ap.parse_args()
    F = validate.run(data_only=True)
    if F.errors:
        for f in F.errors:
            print(f"{f['rule']} {f['name']}: {f['file']}: {f['message']}")
        raise SystemExit("build aborted: fix validation errors first")
    outs, docs = build()
    doc_changed = sorted(k for k, v in docs.items() if (ROOT / k).read_text(encoding="utf-8") != v)
    if args.check:
        if doc_changed:
            for k in doc_changed:
                print(f"E023 build: {k} GENERATED block out of date; run `make build` and commit it")
            raise SystemExit(1)
        print(f"build --check OK ({len(outs)} files built in memory; GENERATED blocks fresh)")
        return
    out = args.out.resolve()
    existing = {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file() and p.suffix != ".sqlite"} if out.exists() else set()
    stale = sorted(existing - set(outs))
    def same(k, v):
        p = out / k
        return p.exists() and (p.read_bytes() == v if isinstance(v, bytes) else p.read_text(encoding="utf-8") == v)

    changed = sorted(k for k, v in outs.items() if not same(k, v))
    for k in stale:
        (out / k).unlink()
    for k in changed:
        p = out / k
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(outs[k], bytes):
            p.write_bytes(outs[k])
        else:
            p.write_text(outs[k], encoding="utf-8")
    for k in doc_changed:
        (ROOT / k).write_text(docs[k], encoding="utf-8")
    for d in sorted(out.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    if args.sqlite:
        write_sqlite(out / "simgrammar.sqlite")
    print(f"build OK: {len(changed)} written, {len(stale)} removed, {len(doc_changed)} docs refreshed, {len(outs)} total -> {out}")


if __name__ == "__main__":
    main()
