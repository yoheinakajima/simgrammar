"""What the website publishes for programs and agents, beside its pages. scripts/web.py calls files(w) with its Web `w`.

  llms.txt                                        the site for a language model: what the atlas is for, and a link to every file
  developers/index.html                           the same files for a person: what each holds, the schemas, examples, versions
  openapi.json                                    the files as a read-only HTTP API (OpenAPI 3.1)
  schema/*.schema.json, schema/vocab.json         the record schemas as committed, and every closed vocabulary with the rubrics
  .well-known/api-catalog                         an RFC 9727 linkset naming openapi.json and the developers page
  .well-known/ard.json, .well-known/ai-catalog.json   an Agentic Resource Discovery catalog, and the same at the AI Catalog path
  .well-known/agent-skills/index.json             an Agent Skills discovery index (v0.2.0) carrying the sha256 of
  .well-known/agent-skills/simgrammar/SKILL.md    the skill: when to reach for the atlas, and how to look up, query, and cite it

One list, endpoints(), names every file, so the API description, the page, the skill, and llms.txt cannot disagree. GitHub
Pages serves the site, so there is no server to answer a query and no response header to set: every endpoint is a static
file, fetched whole and filtered by the caller. Like every projection, all of this is a deterministic function of the
build's inputs. The home page's JSON-LD (jsonld) is here too, since it describes the same dataset and files.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from lib import ROOT

SKILL = "simgrammar"
SKILL_PATH = f".well-known/agent-skills/{SKILL}/SKILL.md"
# The skill's description is what an agent reads to decide whether to load it, so it leads with when to use the atlas.
SKILL_DESCRIPTION = ("Look up, query, and cite SimGrammar, an open dataset of simulation games broken into the mechanics they are built from, "
                     "the mathematical, AI, ML, and LLM results that change those mechanics, and dated design bets. Use when asked which games "
                     "use a mechanic, how a simulation game's systems work, which AI technique could change a game system, which combinations "
                     "no catalogued game has tried, or how to cite this atlas.")
# What the atlas answers, and what it does not, for llms.txt and the skill
WHEN = ["Which simulation games use a mechanic, and whether it is a core part of the game or a supporting one.",
        "What a mechanic is: the state it owns, its update rule, its design levers, how it fails, and which mechanics it requires, specializes, "
        "reinforces, or pulls against.",
        "Which mathematical, AI, ML, and LLM results change a mechanic, how, how far each has reached shipped games, and whether it breaks exact replay.",
        "Which design bets the atlas makes: combinations of mechanics and techniques, each with a validation experiment and a dated, falsifiable prediction.",
        "Citing the atlas, a finding, or a single record, pinned to the exact version of the data."]
NOT_FOR = ("It is not a sales, review, or player-count database, and it admits simulation games only: games whose core loop is driven "
           "by a model of some system whose state changes without the player scripting each change.")
JSON, CSV, MD = "application/json", "text/csv", "text/markdown"


def camel(s: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[-_]", s))


def endpoints(w) -> list[dict]:
    """Every file the site publishes for programs, in the order a reader meets them. `path` is from the site root;
    `served` is the Content-Type GitHub Pages sends for it, which is not always the format's own type."""
    reg = w.registry["types"]
    plural = {t: reg[t]["plural"] for t in w.types}
    label = {t: reg[t]["label"].lower() for t in w.types}
    ep = lambda path, op, group, what, fmt, served=None, schema=None, params=None: dict(
        path=path, op=op, group=group, what=what, fmt=fmt, served=served or fmt, schema=schema, params=params or {})
    out = [ep("/llms.txt", "getLlmsTxt", "start", "What the atlas is for and a link to every file, for a language model", MD, "text/plain"),
           ep("/manifest.json", "getManifest", "start", "The contract version, the dataset_sha256 that pins the exact data, counts by type, "
              "and the hash of every record, schema, and vocabulary", JSON, schema="Manifest"),
           ep("/openapi.json", "getOpenApi", "start", "This list of files as an OpenAPI 3.1 description", JSON)]
    out += [ep(f"/dist/entities/{plural[t]}.json", f"list{camel(plural[t])}", "records",
               f"Every {label[t]} record in full, as schema/{t}.schema.json defines it, with the build's computed fields under _derived",
               JSON, schema="Records") for t in w.types]
    out += [ep(f"/dist/tables/{plural[t]}.csv", f"get{camel(plural[t])}Table", "tables",
               f"One row per {label[t]} record, with list fields joined by semicolons", CSV) for t in w.types]
    out += [ep("/dist/tables/edges.csv", "getEdgesTable", "tables", "One row per stored edge: source, its type, edge type, target, its type, "
               "and the edge's role, effect, and note", CSV),
            ep("/dist/tables/game_mechanic_matrix.csv", "getGameMechanicMatrix", "tables",
               "One row per game, one column per mechanic: 2 when the game uses it as a core part, 1 as a supporting part, 0 not at all", CSV),
            ep("/dist/graph/nodes.jsonl", "getGraphNodes", "graph", "One JSON object a line per record: id, type, name, summary, and computed "
               "fields such as cluster, prevalence, and technique exposure", "application/jsonl", "application/octet-stream", "GraphNode"),
            ep("/dist/graph/edges.jsonl", "getGraphEdges", "graph", "One JSON object a line per edge: source, target, edge type, and its attributes",
               "application/jsonl", "application/octet-stream", "GraphEdge"),
            ep("/dist/analysis/stats.json", "getStats", "analysis", "Every statistic the paper cites, by the name its text uses", JSON),
            ep("/paper.md", "getPaperMarkdown", "text", "The paper as markdown, its record links pointing at the record pages", MD),
            ep("/references.bib", "getReferences", "text", "Every source the paper cites, as BibTeX", "application/x-bibtex", "application/octet-stream"),
            ep("/dist/wiki/{type}/{id}.md", "getRecordMarkdown", "text", "One record as markdown, with its sources and its backlinks", MD,
               params={"type": list(w.types), "id": None}),
            ep("/schema/{name}.schema.json", "getSchema", "schemas", "The JSON Schema (draft 2020-12) a record type's files validate against", JSON,
               params={"name": sorted(p.name[:-len(".schema.json")] for p in (ROOT / "schema").glob("*.schema.json"))}),
            ep("/schema/vocab.json", "getVocabularies", "schemas", "Every closed vocabulary with its terms and definitions, and the rubric "
               "anchors behind every ordinal score", JSON),
            ep("/dist/simgrammar-dist.zip", "getArchive", "archive", "Every projection under /dist/ in one archive", "application/zip",
               "application/x-zip-compressed")]
    return out


def abs_url(w, path: str) -> str:
    return w.site["url"].rstrip("/") + path


def example_mechanic(w) -> str:
    """The examples' mechanic: of those some technique affects, the one the most games use, so that every example
    returns something today."""
    live = [e for e in w.ents.get("mechanic", []) if not e.data.get("deprecated") and any(ed.type == "affects" for ed in w.edges_in[e.id])]
    return min(live, key=lambda e: (-w.derived.get(e.id, {}).get("prevalence", 0), e.id)).id


def citation(w) -> list[str]:
    """How to cite the atlas, in sentences for llms.txt, the skill, and the developers page."""
    m, doi = w.meta, w.meta.get("doi")
    return ([f"Cite the paper and dataset as {', '.join(w.analysis['byline'])} ({m['date'][:4]}), {m['title']}, version {m['version']}"
             + (f", doi:{doi} (https://doi.org/{doi})" if doi else "") + ", with the dataset_sha256 from manifest.json for the data you used."]
            + [f"BibTeX is on {w.site['url']}paper/#cite; CITATION.cff in the repository holds the same."])


# ---------------------------------------------------------------- llms.txt

def llms_txt(w) -> str:
    m, man = w.meta, w.manifest
    link = lambda path, text, what="": f"- [{text}]({abs_url(w, path)})" + (f": {what}" if what else "")
    eps = endpoints(w)
    data = [link(e["path"], e["path"].lstrip("/"), e["what"]) for e in eps if "{" not in e["path"] and e["group"] != "start" and e["path"] != "/paper.md"]
    data += [link(f"/schema/{t}.schema.json", f"schema/{t}.schema.json", f"the schema of {t} records") for t in w.types]
    lines = [f"# simgrammar · {m['title']}", "", f"> {m['subtitle']}. A versioned dataset of simulation game mechanics with provenance, and the paper projected from it.", "",
             f"dataset sha256: {man['dataset_sha256']}",
             f"contract: {man['contract_version']} · paper v{m['version']} ({m['date']})" + (f" · doi {m['doi']}" if m.get("doi") else ""), "",
             "## When to use this", ""] + [f"- {s}" for s in WHEN] + ["", NOT_FOR, "",
             "Every file below is static, public, and needs no key or account: fetch it whole and filter it yourself. Record ids are kebab-case and "
             "never change once merged, and each record has a page at /<type>/<id>/ and a markdown twin at /dist/wiki/<type>/<id>.md. "
             "The developers page explains every file, openapi.json describes them, and the agent skill below says how to use them.", "",
             "## Start", "",
             link("/developers/", "Data files for programs and agents", "what each file holds, the schemas, examples, versions, and limits"),
             link("/openapi.json", "openapi.json", "every file as an OpenAPI 3.1 description"),
             link("/manifest.json", "manifest.json", "contract version, dataset_sha256, counts, and hashes"),
             link("/" + SKILL_PATH, "SKILL.md", "an agent skill for looking up, querying, and citing the atlas"), "",
             "## Read", "",
             link("/paper/", "The paper", "every finding with its method and statistics"),
             link("/paper.md", "The paper as markdown"),
             link("/book/", "The book", "one chapter a page"),
             link("/watch/", "Watch", "the episodes and shorts, with transcripts"),
             link("/find/", "Find", "every page of the site in one list"),
             link("/about/", "About", "how the atlas is made, every download, the research log, the vocabularies"), "",
             "## Data", ""] + data + ["", "## Agents", "",
             link("/.well-known/agent-skills/index.json", "Agent Skills index", "the skills this site publishes (Agent Skills discovery v0.2.0)"),
             link("/.well-known/ard.json", "Agentic Resource Discovery catalog", "the same files as ARD entries"),
             link("/.well-known/api-catalog", "API catalog", "an RFC 9727 linkset naming openapi.json"), "",
             "## Cite", ""] + [f"- {s}" for s in citation(w)] + ["", "## Contribute", "",
             f"- [AGENTS.md]({w.gh('AGENTS.md')}): procedure for humans and agents",
             f"- [CONTRACT.md]({w.gh('CONTRACT.md')}): invariants and validator rules",
             f"- [CITATION.cff]({w.gh('CITATION.cff')}): citation metadata", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- the agent skill

def skill_md(w) -> str:
    root, mech = w.site["url"], example_mechanic(w)
    eps = endpoints(w)
    rows = [f"| `{e['path']}` | {e['what']} |" for e in eps]
    status = {t["id"]: t.get("definition", "").strip() for t in w.vocabs.get("status", {}).get("terms", [])}
    lines = ["---", f"name: {SKILL}", f"description: {json.dumps(SKILL_DESCRIPTION)}", "---", "",
             "# SimGrammar", "",
             f"{w.meta['subtitle']}. Every game, mechanic, technique, design bet (record type `opportunity`), and source is one record with a "
             "stable id, and the paper, the book, and the website are all built from those records, so they agree with the files below.", "",
             "## When to use it", ""] + [f"- {s}" for s in WHEN] + ["", NOT_FOR, "",
             "## Read", "",
             f"- {root}llms.txt: an index of the site.",
             f"- {root}paper.md: the paper as markdown, every finding with its method and statistics.",
             f"- {root}<type>/<id>/: one page per record (types: {', '.join(w.types)}); {root}dist/wiki/<type>/<id>.md is the same record as markdown.", "",
             "## Query", "",
             f"Every file is static, public, and needs no key: fetch it whole and filter it yourself. Paths are from {root.rstrip('/')}; "
             f"{root}openapi.json describes each one and {root}developers/ explains them.", "",
             "| Path | What it holds |", "|---|---|"] + rows + ["",
             "Record ids are kebab-case and never change once merged; a replaced record carries `deprecated.superseded_by`. Categorical fields take "
             "terms from closed vocabularies and ordinal scores are anchor levels of the rubrics, both in schema/vocab.json. Edges are stored on one "
             "side only (a game lists the mechanics it `uses`, a technique the mechanics it `affects`); the graph files and the `_derived` fields "
             "carry the reverse direction.", "",
             "```python",
             "import json, urllib.request",
             f'games = json.load(urllib.request.urlopen("{root}dist/entities/games.json"))',
             f'uses = sorted(g["name"] for g in games if any(m["id"] == "{mech}" for m in g.get("mechanics", [])))',
             "```", "",
             "## Weigh the evidence before you repeat a claim", ""]
    lines += [f"- `status: {k}`: {v}" for k, v in status.items()] if status else []
    lines += ["- A claim names the sources that support it and may carry a verbatim quote from the first; a source records the date it was read and may carry an archived snapshot.",
              "- Ordinal scores (emergence, legibility, and the rest) are one rater's reading of the rubric anchors unless the record lists `ratings`.",
              "- Counts, prevalence, clusters, and exposure are computed by the build, never stored; they sit under `_derived` and change as the catalog "
              "grows, so quote them with the dataset_sha256 from manifest.json.", "",
              "## Cite", ""] + [f"- {s}" for s in citation(w)] + ["", "## Contribute", "",
              f"To add or correct a record, follow {w.gh('AGENTS.md')} (the procedure) and {w.gh('CONTRACT.md')} (the rules): every change is a "
              "pull request carrying one run record, and the validator checks it.", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- OpenAPI

def openapi(w) -> dict:
    root, m, man = w.site["url"], w.meta, w.manifest
    eps = endpoints(w)
    rec_props = {"id": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$", "description": "Kebab-case id, unique across all types; never changes once merged"},
                 "type": {"type": "string", "enum": list(w.types)}, "name": {"type": "string"}, "summary": {"type": "string"},
                 "status": {"type": "string", "enum": [t["id"] for t in w.vocabs.get("status", {}).get("terms", [])]},
                 "deprecated": {"type": "object", "description": "Present when the record was replaced: superseded_by and reason"},
                 "_derived": {"type": "object", "description": "Values the build computes (counts, prevalence, clusters, exposure, backlinks); never stored in the record files"}}
    schemas = {
        "Record": {"type": "object", "required": ["id", "type", "name"], "properties": rec_props, "additionalProperties": True,
                   "description": f"A record as {root}schema/<type>.schema.json defines it, plus _derived. Those schemas are closed, so every other field is one they define."},
        "Records": {"type": "array", "items": {"$ref": "#/components/schemas/Record"}},
        "Manifest": {"type": "object", "required": ["contract_version", "dataset_sha256", "counts"], "properties": {
            "contract_version": {"type": "string", "description": "The CONTRACT.md version; a change to any record's shape bumps it"},
            "dataset_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$", "description": "Hash of every record file; cite it to pin the data"},
            "counts": {"type": "object", "additionalProperties": {"type": "integer"}, "description": "Record files by type, deprecated ones included"},
            "edges": {"type": "integer"}, "entities": {"type": "object", "description": "The sha256 of each record file, by id"},
            "schemas": {"type": "object"}, "vocab": {"type": "object"}, "generator": {"type": "string"}}},
        "GraphNode": {"type": "object", "required": ["id", "type", "name"], "properties": {
            "id": {"type": "string"}, "type": {"type": "string", "enum": list(w.types)}, "name": {"type": "string"}, "summary": {"type": ["string", "null"]},
            "group": {"type": "string"}, "cluster": {"type": ["string", "null"]}, "prevalence": {"type": ["number", "null"]},
            "priority": {"type": ["number", "null"]}, "technique_exposure": {"type": ["number", "null"]}}},
        "GraphEdge": {"type": "object", "required": ["source", "target", "type"], "properties": {
            "source": {"type": "string"}, "target": {"type": "string"},
            "type": {"type": "string", "enum": [t["id"] for t in w.vocabs["edge_types"]["terms"]]},
            "attrs": {"type": "object", "description": "The edge's role, effect, and note, where its type has them"}}},
        "Text": {"type": "string"},
    }
    paths = {}
    for e in eps:
        params = [{"name": k, "in": "path", "required": True, "schema": {"type": "string", **({"enum": v} if v else {})}} for k, v in e["params"].items()]
        body = {"schema": {"$ref": f"#/components/schemas/{e['schema']}"}} if e["schema"] else {"schema": {"type": "object"} if e["fmt"] == JSON else {"$ref": "#/components/schemas/Text"}}
        if e["fmt"] == "application/jsonl":
            body["x-line-schema"] = body.pop("schema")
            body["schema"] = {"$ref": "#/components/schemas/Text"}
        op = {"operationId": e["op"], "summary": e["what"], "description": e["what"] + (f". GitHub Pages serves it as {e['served']}." if e["served"] != e["fmt"] else "."),
              "tags": [e["group"]], "responses": {"200": {"description": e["what"], "content": {e["fmt"]: body}},
                                                  "404": {"description": "No such file. GitHub Pages answers with its HTML not-found page; there is no JSON error body.",
                                                          "content": {"text/html": {"schema": {"$ref": "#/components/schemas/Text"}}}}}}
        if params:
            op["parameters"] = params
        paths[e["path"]] = {"get": op}
    return {
        "openapi": "3.1.0",
        "info": {"title": "SimGrammar data files", "version": str(man["contract_version"]),
                 "summary": "The SimGrammar atlas of simulation game mechanics as static files: records, tables, graph, schemas, and vocabularies.",
                 "description": ("Every endpoint is a static file served by GitHub Pages: a GET returns it whole, there are no query parameters, "
                                 "and filtering happens on your side. No key, account, or authentication is needed, and responses carry "
                                 "Access-Control-Allow-Origin: *. The project sets no rate limit of its own; GitHub Pages' limits apply. "
                                 f"info.version is the contract version (CONTRACT.md), which changes when a record's shape changes; the "
                                 f"dataset_sha256 in /manifest.json changes with any record and pins the exact data. Paper v{m['version']} ({m['date']}). "
                                 f"Explained for people at {root}developers/."),
                 "license": {"name": "CC BY 4.0 (data and text); Apache-2.0 (code)", "identifier": "CC-BY-4.0"},
                 "contact": {"name": "SimGrammar on GitHub", "url": w.site["repo"] + "/issues"}},
        "externalDocs": {"description": "The data files explained", "url": f"{root}developers/"},
        "servers": [{"url": root.rstrip("/")}],
        "security": [],
        "tags": [{"name": g} for g in dict.fromkeys(e["group"] for e in eps)],
        "paths": paths,
        "components": {"schemas": schemas},
    }


# ---------------------------------------------------------------- discovery catalogs

def ard(w) -> dict:
    """The Agentic Resource Discovery catalog (https://agenticresourcediscovery.org/): one entry per resource an agent can use,
    each with a domain-anchored urn:air id, a media type, and a url. The same document serves /.well-known/ai-catalog.json."""
    root, dom = w.site["url"], w.site["domain"]
    trust = {"identity": f"https://{dom}", "identityType": "https"}
    entry = lambda ns, name, display, typ, path, desc, tags, extra=None: dict(
        identifier=f"urn:air:{dom}:{ns}:{name}", displayName=display, type=typ, url=abs_url(w, path), description=desc, tags=tags,
        auth={"status": "none"}, trustManifest=trust, **(extra or {}))
    queries = ["which simulation games use a given mechanic", "what are the parts a colony sim is built from",
               "which AI techniques change how NPC needs work", "which mechanic combinations has no game tried", "how do I cite the SimGrammar dataset"]
    entries = [
        entry("api", "data-files", "SimGrammar data files", "application/vnd.oai.openapi+json", "/openapi.json",
              "Static JSON, CSV, and JSON-lines files holding every simulation game, mechanic, AI technique, design bet, and source in the atlas, "
              "with their schemas and vocabularies. No key needed.", ["dataset", "simulation-games", "game-mechanics", "openapi"],
              {"capabilities": [e["op"] for e in endpoints(w)], "representativeQueries": queries}),
        entry("skill", SKILL, "SimGrammar agent skill", MD, "/" + SKILL_PATH, SKILL_DESCRIPTION, ["skill", "dataset", "citation"],
              {"representativeQueries": queries[:3]}),
        entry("docs", "llms-txt", "SimGrammar llms.txt", MD, "/llms.txt", "What the atlas is for and a link to every file, for a language model.",
              ["llms.txt", "docs"]),
        entry("docs", "paper", "The Grammar of Simulation (paper, markdown)", MD, "/paper.md",
              "The paper built from the dataset: every finding with its method, statistics, and citations.", ["paper", "docs"]),
        entry("dataset", "archive", "SimGrammar dataset archive", "application/zip", "/dist/simgrammar-dist.zip",
              "Every projection of the dataset in one zip: tables, records, graph, analysis, wiki, and paper.", ["dataset", "download"]),
    ]
    return {"specVersion": "1.0", "host": {"displayName": "SimGrammar", "documentationUrl": f"{root}developers/"}, "entries": entries}


def api_catalog(w) -> dict:
    """RFC 9727: the catalog names the one API, and the API's entry links its description, documentation, and metadata."""
    root = w.site["url"]
    return {"linkset": [
        {"anchor": f"{root}.well-known/api-catalog", "item": [{"href": f"{root}developers/"}]},
        {"anchor": f"{root}developers/",
         "service-desc": [{"href": f"{root}openapi.json", "type": "application/vnd.oai.openapi+json"}],
         "service-doc": [{"href": f"{root}developers/", "type": "text/html"}],
         "service-meta": [{"href": f"{root}manifest.json", "type": JSON}]}]}


def jsonld(w) -> str:
    """The home page's structured data: the site, the dataset with its downloads, the paper, and the byline. Its twin is the page
    itself, which says each of these in text."""
    from web import LEAD
    root, m, eps = w.site["url"], w.meta, endpoints(w)
    rows = {r["contributor"]: r for r in w.analysis["tables"]["contributors"]["rows"]}

    def person(a):
        r = rows.get(a)
        if not r:   # "SimGrammar contributors", once the byline runs past byline_names
            return {"@type": "Organization", "name": a, "url": f"{root}paper/#appendix-d-contributors"}
        gh = f"https://github.com/{r['github']}"
        return {"@type": "Person", "name": a, "url": next((u for u in r["links"] if "x.com" not in u and "linkedin" not in u), gh), "sameAs": [gh] + list(r["links"])}

    people = [person(a) for a in w.analysis["byline"]]
    doi = f"https://doi.org/{m['doi']}" if m.get("doi") else None
    dl = [{"@type": "DataDownload", "contentUrl": abs_url(w, e["path"]), "encodingFormat": e["fmt"], "description": e["what"]}
          for e in eps if e["group"] in ("records", "tables", "graph", "archive") and "{" not in e["path"]]
    dataset = {"@type": "Dataset", "@id": f"{root}#dataset", "name": f"SimGrammar: {m['title']}", "alternateName": "SimGrammar",
               "description": f"{m['subtitle']}. {LEAD}", "url": root, "version": str(m["version"]), "datePublished": str(m["date"]),
               "inLanguage": "en", "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
               "creator": people, "keywords": ["simulation games", "game mechanics", "game design", "AI techniques", "machine-readable dataset"],
               "sameAs": [w.site["repo"]] + ([doi] if doi else []), "distribution": dl,
               "subjectOf": {"@id": f"{root}paper/#article"}}
    if doi:
        dataset["identifier"] = doi
    graph = [{"@type": "WebSite", "@id": f"{root}#website", "url": root, "name": "simgrammar", "alternateName": "SimGrammar",
              "description": LEAD, "inLanguage": "en", "about": {"@id": f"{root}#dataset"}},
             dataset,
             {"@type": "ScholarlyArticle", "@id": f"{root}paper/#article", "url": f"{root}paper/", "headline": m["title"], "name": f"{m['title']}: {m['subtitle']}",
              "author": people, "datePublished": str(m["date"]), "version": str(m["version"]), "inLanguage": "en",
              "license": "https://creativecommons.org/licenses/by/4.0/", "isBasedOn": {"@id": f"{root}#dataset"},
              "encoding": {"@type": "MediaObject", "contentUrl": f"{root}paper.md", "encodingFormat": MD}}]
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f'<script type="application/ld+json">{data.replace("</", "<" + chr(92) + "/")}</script>'


# ---------------------------------------------------------------- the page

def page(w) -> str:
    from web import esc
    base, man, root = "../", w.manifest, w.site["url"]
    eps, mech = endpoints(w), example_mechanic(w)

    def href(path):
        return base + path.lstrip("/") if "{" not in path else None

    def ep_row(e):
        h = href(e["path"])
        ext = e["path"].rsplit(".", 1)[-1]
        end = f'<a href="{esc(h)}" data-internal>{esc(ext)}</a>' if h else f'<span>{esc(ext)}</span>'
        return (f'<div class="row"><div class="id">{esc(e["group"])}</div><div><code>{esc(e["path"])}</code><p>{esc(e["what"])}</p></div>'
                f'<div class="end">{end}</div></div>')

    files = "".join(ep_row(e) for e in eps)
    reg = w.registry["types"]
    srows = "".join(f'<div class="row"><div class="id">{esc(t)}</div><div><code>/schema/{esc(t)}.schema.json</code><p>{esc(w.schemas[Path(reg[t]["schema"]).name]["description"])}</p></div>'
                    f'<div class="end"><a href="{base}schema/{esc(t)}.schema.json" data-internal>schema</a> <a href="{base}dist/entities/{esc(reg[t]["plural"])}.json" data-internal>records</a></div></div>'
                    for t in w.types)
    srows += (f'<div class="row"><div class="id">vocab</div><div><code>/schema/vocab.json</code><p>Every closed vocabulary a categorical field draws from, each term with its '
              f'label and definition, and the rubric anchors an ordinal score is read against.</p></div><div class="end"><a href="{base}schema/vocab.json" data-internal>json</a></div></div>')
    cmds = [(f"curl -s {root}manifest.json", "the contract version and the dataset_sha256 to cite"),
            (f"curl -s {root}dist/entities/games.json | jq '[.[] | select(any(.mechanics[]; .id == \"{mech}\")) | .name]'", f"the games that use {mech}"),
            (f"curl -s {root}dist/graph/edges.jsonl | jq -c 'select(.type == \"affects\" and .target == \"{mech}\")'", f"the techniques that change {mech}"),
            ("git clone " + w.site["repo"] + " && make sqlite", "every record in SQLite, to query with SQL")]
    crows = "".join(f'<div class="row"><div class="id"></div><div><code>{esc(c)}</code><span class="why">{esc(wy)}</span></div></div>' for c, wy in cmds)
    vrows = [("contract", f"Version {man['contract_version']}. It changes when the shape of a record changes, and openapi.json carries it as info.version.",
              (w.gh("CONTRACT.md"), "CONTRACT.md")),
             ("dataset", f"sha256 {man['dataset_sha256']}. It changes when any record changes; cite it to pin the exact data.", (f"{base}manifest.json", "manifest.json")),
             ("updates", "The site and every file rebuild on each merge to the main branch, so a file's address stays the same while its contents follow the data.",
              (f"{base}about/#research-log", "research log"))]
    vrows_h = "".join(f'<div class="row"><div class="id">{esc(k)}</div><div><p>{esc(t)}</p></div><div class="end"><a href="{esc(u)}"{" data-internal" if u.startswith(base) else ""}>{esc(n)}</a></div></div>'
                      for k, t, (u, n) in vrows)
    lim = [("no key", "No key, account, or sign-in: every file is public. Responses carry Access-Control-Allow-Origin: *, so a page in a browser can fetch them."),
           ("static", "GitHub Pages serves every file whole and caches it for about ten minutes. There are no query parameters; filter after you fetch, or use SQLite."),
           ("errors", "A missing file returns 404 with an HTML page, not a JSON error body."),
           ("ids", "Record ids are kebab-case and never change once merged. A replaced record stays, with deprecated.superseded_by naming its successor.")]
    lrows = "".join(f'<div class="row"><div class="id">{esc(k)}</div><div><p>{esc(t)}</p></div></div>' for k, t in lim)
    doi = w.meta.get("doi")
    cite = (f'<p>Cite the paper and the dataset together, with the dataset_sha256 from <a href="{base}manifest.json" data-internal>manifest.json</a> for the data you used'
            + (f', by its DOI <a href="https://doi.org/{esc(doi)}">{esc(doi)}</a>' if doi else "") + '. The same BibTeX is in the paper\'s '
            f'<a href="{base}paper/#cite" data-internal>cite</a> section, and <a href="{esc(w.gh("CITATION.cff"))}">CITATION.cff</a> in the repository holds the metadata.</p>'
            f'<div class="prompt"><div class="copy-row"><span>bibtex</span><span>{esc(w.meta["title"].lower())} · v{esc(w.meta["version"])}</span></div>'
            f'<pre data-style="citation">{esc(w.bibtex())}</pre></div>')
    body = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol><li><a href="../" data-internal>simgrammar</a></li><li>developers</li></ol></nav>'
            f'<div class="page-header"><p class="eyebrow"><span class="id">developers</span> <span>dataset <b>{w.short}</b></span> <span>contract {esc(man["contract_version"])}</span></p>'
            f'<h1>Every record in the atlas is a file you can fetch</h1><p class="dek">The games, mechanics, techniques, bets, and sources are published as static files at '
            f'stable addresses: full records as JSON, flat tables as CSV, the graph as JSON lines, and the schemas and vocabularies that define them. An HTTP GET is the whole interface.</p>'
            f'<div class="twins"><b>for programs</b><a href="{base}openapi.json" data-internal>openapi.json</a><a href="{base}llms.txt" data-internal>llms.txt</a>'
            f'<a href="{base}{SKILL_PATH}" data-internal>SKILL.md</a><a href="{base}.well-known/ard.json" data-internal>ard.json</a><a href="{base}manifest.json" data-internal>manifest.json</a></div></div>'
            + w.section("files", f'<div class="register" data-size="wide">{files}</div>', "paths from the site root")
            + w.section("schemas", f'<div class="register" data-size="wide">{srows}</div>', "JSON Schema draft 2020-12, closed")
            + w.section("examples", f'<div class="register" data-kind="cmds">{crows}</div>', "curl and jq, or the repository")
            + w.section("versions", f'<div class="register" data-size="wide">{vrows_h}</div>')
            + w.section("limits", f'<div class="register" data-size="wide">{lrows}</div>')
            + w.section("cite", cite, "bibtex"))
    return w.page(title="Developers · simgrammar", desc="The SimGrammar atlas as static files for programs and agents: records as JSON, tables as CSV, the graph, schemas, vocabularies, and how to cite them.",
                  body=body, depth=1, nav="developers", path="developers/")


# ---------------------------------------------------------------- everything

def files(w) -> dict[str, str]:
    dump = lambda d: json.dumps(d, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    skill = skill_md(w)
    cat = dump(ard(w))
    outs = {"web/llms.txt": llms_txt(w), "web/developers/index.html": page(w), "web/openapi.json": dump(openapi(w)),
            "web/schema/vocab.json": dump(w.vocabs), "web/.well-known/api-catalog": dump(api_catalog(w)),
            "web/.well-known/ard.json": cat, "web/.well-known/ai-catalog.json": cat, f"web/{SKILL_PATH}": skill,
            "web/.well-known/agent-skills/index.json": dump({
                "$schema": "https://schemas.agentskills.io/discovery/0.2.0/schema.json",
                "skills": [{"name": SKILL, "type": "skill-md", "description": SKILL_DESCRIPTION, "url": "/" + SKILL_PATH,
                            "digest": "sha256:" + hashlib.sha256(skill.encode("utf-8")).hexdigest()}]})}
    for p in sorted((ROOT / "schema").glob("*.schema.json")):   # byte for byte as committed
        outs[f"web/schema/{p.name}"] = p.read_text(encoding="utf-8")
    return outs
