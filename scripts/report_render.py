"""Token, link, and citation rendering for report/src, book/src, media/episodes, and wiki pages.

Syntax (documented in AGENTS.md):
  {{count:<type>}}            number of live entities of a type (game, mechanic, technique, opportunity, source)
  {{count:edge:<edge_type>}}  number of edges of a type
  {{stat:<name>}}             named statistic from scripts/analyze.py
  {{table:<name>}}            table from report/tables.yaml or scripts/analyze.py
  {{figure:<name>}}           SVG figure from scripts/analyze.py
  {{viz:<name>}}              interactive figure from scripts/viz.py (static SVG in the paper, interactive on the site)
  {{vocab:<vocab>:<term>}}    a vocab term's label
  {{assert:<ref> <op> <value|ref>}}  renders nothing; fails E029 when false. <ref> is a stat name,
                              derived.<id>.<field>, field.<id>.<path> (a stored field), rank.<table>.<id>[.<id>] (1-based row of the first
                              row containing every id; 9999 when absent), cooccur.<mechanic>.<mechanic> (games using both), or
                              cocluster.<game>.<game> (share of subsamples clustering the two together). Cluster-membership
                              assertions also need stable co-clustering (see evaluate_assertion).
  [[id]] / [[id|text]]        link to an entity
  [@src-id] / [@src-a; @src-b] citation
"""
from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urlparse

from lib import ROOT, get_path, load_schemas, read_yaml, vocab_terms

# Analysis-table columns whose values are vocabulary terms: every table shows the term's label, as record pages do.
VOCAB_COLUMNS = {"family": "mechanic_family", "family_a": "mechanic_family", "family_b": "mechanic_family", "subgenre": "subgenre",
                 "maturity": "technique_maturity", "category": "technique_category", "effect": "effect", "opportunity_type": "opportunity_type",
                 "horizon": "horizon", "kind": "source_kind"}
TABLE_VOCAB = {"opportunities-ranked": {"type": "opportunity_type"}}   # a column whose name means something else in other tables
RUBRIC_COLUMNS = {"rater-agreement": "field"}                          # a column that holds a rubric field's name


def field_label(name: str) -> str:
    """A rubric field in words, as the prose writes it: ai_leverage → AI leverage, tuning_difficulty → tuning difficulty."""
    return re.sub(r"\bai\b", "AI", str(name).replace("_", " "))


def table_value(ctx, table: str, col: str, v):
    """A generated table's cell as a reader sees it: a vocabulary term's label, a rubric field in words, else the value."""
    if col == RUBRIC_COLUMNS.get(table) and isinstance(v, str):
        return field_label(v)
    vn = TABLE_VOCAB.get(table, {}).get(col) or VOCAB_COLUMNS.get(col)
    if vn and isinstance(v, (str, list)):
        terms = vocab_terms(ctx.vocabs, vn)
        label = lambda x: terms.get(str(x), {}).get("label", x)
        return [label(x) for x in v] if isinstance(v, list) else label(v)
    return v


TOKEN_RE = re.compile(r"\{\{([a-z_]+):([^}]+)\}\}")
LINK_RE = re.compile(r"\[\[([a-z0-9-]+)(?:\|([^\]]+))?\]\]")
CITE_RE = re.compile(r"\[(@src-[a-z0-9-]+(?:\s*;\s*@src-[a-z0-9-]+)*)\]")
NOUNS = r"(games?|titles?|mechanics?|techniques?|opportunit(?:y|ies)|sources?|edges?|entities|entit(?:y)|pairs?|clusters?|predictions?|uses|entries|families|subgenres|runs?)"
LITERAL_STAT_RE = re.compile(
    r"(?<![\w.#])(?!(?:19|20)\d\d\b)(?:\d[\d,]*(?:\.\d+)?\s*(?:%|percent)\s+of|\d[\d,]*(?![\d.]))\s+(?:[A-Za-z-]+\s+)?" + NOUNS + r"\b",
    re.I,
)


class Context:
    def __init__(self, ents, edges, analysis, vocabs, registry):
        self.ents = ents
        self.edges = edges
        self.analysis = analysis
        self.vocabs = vocabs
        self.registry = registry
        self.by_id = {e.id: e for t, lst in ents.items() if t != "run" for e in lst}
        self.edge_counts = Counter(e.type for e in edges)
        spec = read_yaml(ROOT / "report" / "tables.yaml") or {}
        self.decl_tables = {t["name"]: t for t in spec.get("tables", [])}
        self.citations: list[str] = []
        meta = read_yaml(ROOT / "report" / "meta.yaml") or {}
        self.site_url = (meta.get("site") or {}).get("url", "")
        # each type's fields that take a vocabulary term ({type: {field: vocab}}), so a declared table shows labels
        schemas = load_schemas()
        self.field_vocab = {}
        for t, spec in registry["types"].items():
            props = (schemas.get(spec["schema"].rsplit("/", 1)[-1]) or {}).get("properties", {})
            self.field_vocab[t] = {k: p.get("x-vocab") or (p.get("items") or {}).get("x-vocab") for k, p in props.items()
                                   if p.get("x-vocab") or (p.get("items") or {}).get("x-vocab")}

    web_base = ""  # relative prefix from the page being rendered to the web root (mode "web")

    def link_target(self, eid: str, mode: str) -> str:
        e = self.by_id[eid]
        if mode == "wiki":
            return f"../{e.type}/{eid}.md"
        if mode == "site":
            return f"#/{e.type}/{eid}"
        if mode == "web":
            return f"{self.web_base}{e.type}/{eid}/"
        return f"../wiki/{e.type}/{eid}.md"

    def label(self, eid: str) -> str:
        e = self.by_id.get(eid)
        return e.data.get("name", eid) if e else eid


ASSERT_RE = re.compile(r"^([a-z0-9_.-]+)\s*(==|!=|<=|>=|<|>)\s*(.+)$")
CLUSTER_EQ_RE = re.compile(r"^derived\.([a-z0-9-]+)\.cluster$")


def lookup_ref(ref: str, a: dict, by_id: dict):
    """Resolve an assertion reference. Returns (found, value)."""
    if ref in a["stats"]:
        return True, a["stats"][ref]
    if ref.startswith("derived."):
        parts = ref.split(".", 2)
        if len(parts) == 3:
            dv = a["derived"].get(parts[1], {})
            if parts[2] in dv:
                return True, dv[parts[2]]
        return False, None
    if ref.startswith("field."):
        parts = ref.split(".", 2)
        ent = by_id.get(parts[1]) if len(parts) == 3 else None
        if ent is not None and get_path(ent.data, parts[2]) is not None:
            return True, get_path(ent.data, parts[2])
        return False, None
    if ref.startswith("cooccur."):
        parts = ref.split(".")
        mids = a.get("mechanic_ids") or set()
        if len(parts) == 3 and parts[1] in mids and parts[2] in mids:
            return True, (a.get("pair_count") or {}).get(tuple(sorted(parts[1:])), 0)
        return False, None
    if ref.startswith("cocluster."):
        parts = ref.split(".")
        co = a.get("cocluster") or {}
        if len(parts) == 3 and parts[1] in co.get("index", {}) and parts[2] in co.get("index", {}):
            i, j = co["index"][parts[1]], co["index"][parts[2]]
            return True, co["value"](i, j)
        return False, None
    if ref.startswith("rank."):
        parts = ref.split(".")
        tbl = a["tables"].get(parts[1]) if len(parts) >= 3 else None
        if tbl is None or parts[1] in UNRANKABLE:
            return False, None
        ids = set(parts[2:])
        row_vals = []
        for row in tbl["rows"]:
            vals = set()
            for v in row.values():
                vals.update(map(str, v) if isinstance(v, list) else [str(v)])
            row_vals.append(vals)
        mentioned = set().union(*row_vals) if row_vals else set()
        if not ids <= mentioned and not all(i in by_id for i in ids):
            return False, None  # an id that is neither in the table nor a record is a typo, not a rank of 9999
        for i, vals in enumerate(row_vals, start=1):
            if ids <= vals:
                return True, i
        return True, 9999
    return False, None


REF_PREFIXES = ("derived.", "field.", "rank.", "cocluster.", "cooccur.")
# Tables whose row order or labels follow cluster numbering: ranks in them change with k, not with the data's meaning.
UNRANKABLE = {"game-clusters", "cluster-stability"}


def looks_like_ref(raw: str) -> bool:
    return raw.startswith(REF_PREFIXES) or bool(re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)+", raw))


def evaluate_assertion(expr: str, a: dict, by_id: dict) -> tuple[str, str]:
    """Evaluate `<ref> <op> <value|ref>`. Returns (status, message), status in ok | fail | malformed.

    A cluster-membership assertion (derived.x.cluster ==/!= derived.y.cluster) additionally requires the pair's
    co-clustering share across subsamples to clear the stability thresholds in report/analysis.yaml, so a grouping
    that moves when a few games are added or removed cannot be asserted.
    """
    m2 = ASSERT_RE.match(expr.strip())
    if not m2:
        return "malformed", expr
    name, op, raw = m2.group(1), m2.group(2), m2.group(3).strip().strip('"')
    found, val = lookup_ref(name, a, by_id)
    if not found:
        return "malformed", f"unknown reference '{name}'"
    rfound, rval = lookup_ref(raw, a, by_id)
    if not rfound and looks_like_ref(raw):
        return "malformed", f"unknown reference '{raw}' on the right-hand side"
    la, lb = CLUSTER_EQ_RE.match(name), CLUSTER_EQ_RE.match(raw)
    if bool(la) != bool(lb):
        return "malformed", "a cluster label changes whenever k does; compare two games' clusters (derived.a.cluster == derived.b.cluster) or use cocluster.a.b"
    if la and lb and op not in ("==", "!="):
        return "malformed", "cluster labels can only be compared with == or !="
    shown = str(rval) if rfound else raw
    try:
        rhs = float(shown)
        lhs = float(str(val).lstrip("<"))
    except ValueError:
        rhs, lhs = shown, str(val)
    ok = {"==": lhs == rhs, "!=": lhs != rhs, "<": lhs < rhs, ">": lhs > rhs, "<=": lhs <= rhs, ">=": lhs >= rhs}[op]
    if not ok:
        if name.startswith("rank.") and val == 9999:
            return "fail", (f"{name} {op} {raw}: the row is not in the table. Rows leave a table when the data crosses its "
                            "threshold or pushes them past its top rows (the table's description gives both); rewrite the "
                            "sentence or pin it to a reference that states the finding directly, such as cooccur.a.b")
        return "fail", f"{name} {op} {raw} (actual: {val} vs {shown})"
    if la and lb:
        co = a.get("cocluster") or {}
        x, y = la.group(1), lb.group(1)
        if x not in co.get("index", {}) or y not in co.get("index", {}):
            return "malformed", f"no co-clustering for {x}, {y}"
        share = co["value"](co["index"][x], co["index"][y])
        if op == "==" and share < co["together"]:
            return "fail", f"{x} and {y} share a cluster but co-cluster in only {share:.2f} of subsamples (needs >= {co['together']}); the grouping is not stable enough to assert"
        if op == "!=" and share > co["apart"]:
            return "fail", f"{x} and {y} are in different clusters but co-cluster in {share:.2f} of subsamples (needs <= {co['apart']}); the separation is not stable enough to assert"
    return "ok", ""


def _fmt(v):
    if isinstance(v, float):
        s = f"{v:.3f}".rstrip("0").rstrip(".")
        return s
    if isinstance(v, list):
        return ", ".join(_fmt(x) for x in v)
    if v is None:
        return ""
    return str(v)


def _decl_rows(ctx: Context, spec: dict):
    ents = [e for e in ctx.ents.get(spec["entity"], []) if not e.data.get("deprecated")]
    rows = []
    for e in ents:
        rec = dict(e.data)
        rec["_derived"] = ctx.analysis["derived"].get(e.id, {})
        ok = True
        for k, v in (spec.get("filter") or {}).items():
            got = get_path(rec, k)
            allowed = v if isinstance(v, list) else [v]
            if isinstance(got, list):
                if not set(got) & set(allowed):
                    ok = False
            elif got not in allowed:
                ok = False
        if ok:
            rows.append(rec)
    for key in reversed(spec.get("sort") or ["id"]):
        rev = key.startswith("-")
        k = key.lstrip("-")
        rows.sort(key=lambda r: (get_path(r, k) is None, get_path(r, k) if get_path(r, k) is not None else 0), reverse=rev)
    if spec.get("limit"):
        rows = rows[: spec["limit"]]
    return rows


def table_md(ctx: Context, name: str, mode: str) -> str | None:
    if name in ctx.decl_tables:
        spec = ctx.decl_tables[name]
        if spec.get("kind") == "count-by":
            field = spec["field"]
            c = Counter()
            for e in ctx.ents.get(spec["entity"], []):
                if e.data.get("deprecated"):
                    continue
                v = get_path(e.data, field)
                for x in (v if isinstance(v, list) else [v]):
                    if x is not None:
                        c[x] += 1
            terms = vocab_terms(ctx.vocabs, spec.get("vocab", "")) if spec.get("vocab") else {}
            lines = [f"| {spec.get('label', field)} | {ctx.registry['types'][spec['entity']]['plural'].title()} |", "|---|---:|"]
            for k, n in sorted(c.items(), key=lambda x: (-x[1], str(x[0]))):
                lines.append(f"| {terms.get(str(k), {}).get('label', k)} | {n} |")
            return "\n".join(lines) + "\n"
        cols = spec["columns"]
        rows = _decl_rows(ctx, spec)
        headers = [c.get("label") if isinstance(c, dict) else c.split(".")[-1].replace("_", " ") for c in cols]
        paths = [c["path"] if isinstance(c, dict) else c for c in cols]
        lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in cols) + "|"]
        fv = ctx.field_vocab.get(spec["entity"], {})
        for r in rows:
            cells = []
            for p in paths:
                v = get_path(r, p)
                if p in ("name",):
                    cells.append(f"[{_fmt(v)}]({ctx.link_target(r['id'], mode)})")
                else:
                    if p in fv and v is not None:   # a vocabulary field shows its term's label
                        terms = vocab_terms(ctx.vocabs, fv[p])
                        v = [terms.get(str(x), {}).get("label", x) for x in v] if isinstance(v, list) else terms.get(str(v), {}).get("label", v)
                    cells.append(_cell_md(ctx, p, v, mode))
            lines.append("| " + " | ".join(cells) + " |")
        cap = f"\n*{spec['caption']}*\n" if spec.get("caption") else ""
        return "\n".join(lines) + "\n" + cap
    t = ctx.analysis["tables"].get(name)
    if t is None:
        return None
    link_cols = set(t.get("link_columns", []))
    lines = ["| " + " | ".join(c.replace("_", " ") for c in t["columns"]) + " |", "|" + "|".join("---" for _ in t["columns"]) + "|"]
    for r in t["rows"]:
        cells = []
        for c in t["columns"]:
            v = r.get(c)
            if c in link_cols:
                vals = v if isinstance(v, list) else [v]
                cap = t.get("max_links")
                more = len(vals) - cap if cap and len(vals) > cap else 0
                shown = vals[:cap] if more else vals
                cell = ", ".join(f"[{ctx.label(x)}]({ctx.link_target(x, mode)})" if x in ctx.by_id else _fmt(x) for x in shown)
                cells.append(cell + (f", and {more} more" if more else ""))
            else:
                cells.append(_cell_md(ctx, c, table_value(ctx, name, c, v), mode))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + f"\n\n*{t['description']}*\n"


GITHUB_HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")


def link_label(url: str) -> str:
    """A profile link's label: x, linkedin, or the site's host."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    return {"x.com": "x", "twitter.com": "x"}.get(host) or ("linkedin" if host == "linkedin.com" or host.endswith(".linkedin.com") else host)


def _cell_md(ctx, path, v, mode):
    if path == "links" and isinstance(v, list):
        return " · ".join(f"[{link_label(u)}]({u})" for u in v)
    s = _fmt(v)
    if path == "github" and GITHUB_HANDLE_RE.match(s):
        return f"[{s}](https://github.com/{s})"
    return s.replace("|", "\\|").replace("\n", " ")


def render(text: str, ctx: Context, mode: str = "paper") -> tuple[str, list[tuple[str, str]]]:
    errors: list[tuple[str, str]] = []
    a = ctx.analysis

    def tok(m):
        kind, arg = m.group(1), m.group(2).strip()
        if kind == "count":
            if arg.startswith("edge:"):
                et = arg[5:]
                if et not in vocab_terms(ctx.vocabs, "edge_types"):
                    errors.append(("E019", f"unknown edge type in {m.group(0)}"))
                    return m.group(0)
                return str(ctx.edge_counts.get(et, 0))
            if arg not in ctx.registry["types"]:
                errors.append(("E019", f"unknown type in {m.group(0)}"))
                return m.group(0)
            return str(sum(1 for e in ctx.ents.get(arg, []) if not e.data.get("deprecated")))
        if kind == "derived":
            found, val = lookup_ref("derived." + arg, a, ctx.by_id)
            if not found:
                errors.append(("E019", f"unknown derived value {m.group(0)}"))
                return m.group(0)
            return _fmt(val)
        if kind == "stat":
            if arg not in a["stats"]:
                errors.append(("E019", f"unknown stat {m.group(0)}"))
                return m.group(0)
            return _fmt(a["stats"][arg])
        if kind == "table" and mode == "web":
            if table_md(ctx, arg, "paper") is None:
                errors.append(("E019", f"unknown table {m.group(0)}"))
                return m.group(0)
            return f"\n\n<!--TABLE:{arg}-->\n\n"
        if kind in ("figure", "viz") and mode == "web":
            pool = a["figures"] if kind == "figure" else a.get("vizzes", {})
            if arg not in pool:
                errors.append(("E019", f"unknown {kind} {m.group(0)}"))
                return m.group(0)
            return f"\n\n<!--{kind.upper()}:{arg}-->\n\n"
        if kind == "viz":
            v = a.get("vizzes", {}).get(arg)
            if v is None:
                errors.append(("E019", f"unknown viz {m.group(0)}"))
                return m.group(0)
            site = ctx.site_url.rstrip("/") + "/" if ctx.site_url else ""
            more = f" Interactive version: {site}#fig-{arg}" if site else ""
            return f"\n![{v['title']}](figures/viz-{arg}.svg)\n\n*Figure: {v['title']}. {v['caption']}{more}*\n"
        if kind == "table":
            md = table_md(ctx, arg, mode)
            if md is None:
                errors.append(("E019", f"unknown table {m.group(0)}"))
                return m.group(0)
            return "\n" + md
        if kind == "figure":
            f = a["figures"].get(arg)
            if f is None:
                errors.append(("E019", f"unknown figure {m.group(0)}"))
                return m.group(0)
            return f"\n![{f['caption']}](figures/{arg}.svg)\n\n*Figure: {f['caption']}*\n"
        if kind == "assert":
            status, msg = evaluate_assertion(arg, a, ctx.by_id)
            if status == "malformed":
                errors.append(("E019", f"malformed assertion or unknown reference {m.group(0)}: {msg}"))
            elif status == "fail":
                errors.append(("E029", f"report assertion failed: {msg}; the prose next to this assertion no longer matches the data"))
            return ""
        if kind == "vocab":
            vname, _, term = arg.partition(":")
            t = vocab_terms(ctx.vocabs, vname).get(term)
            if not t:
                errors.append(("E019", f"unknown vocab term {m.group(0)}"))
                return m.group(0)
            return t["label"]
        errors.append(("E019", f"unknown token kind {m.group(0)}"))
        return m.group(0)

    def link(m):
        eid, txt = m.group(1), m.group(2)
        if eid not in ctx.by_id:
            errors.append(("E020", f"unresolved link [[{eid}]]"))
            return m.group(0)
        return f"[{txt or ctx.label(eid)}]({ctx.link_target(eid, mode)})"

    def cite(m):
        ids = [x.strip()[1:] for x in m.group(1).split(";")]
        parts = []
        for sid in ids:
            if sid not in ctx.by_id:
                errors.append(("E020", f"unresolved citation @{sid}"))
                parts.append(sid)
                continue
            if sid not in ctx.citations:
                ctx.citations.append(sid)
            n = ctx.citations.index(sid) + 1
            parts.append(f"[{n}](#ref-{sid})" if mode != "wiki" else f"[{n}](../source/{sid}.md)")
        return "[" + ", ".join(parts) + "]"

    out = TOKEN_RE.sub(tok, text)
    out = LINK_RE.sub(link, out)
    out = CITE_RE.sub(cite, out)
    return out, errors


def literal_stats(text: str) -> list[str]:
    """Literal numbers next to dataset nouns. A sentence that carries a citation is an external figure and is exempt."""
    hits = []
    in_code = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.lstrip().startswith(("|", "#")):
            continue
        clean = TOKEN_RE.sub("TOKEN", line)
        for sentence in re.split(r"(?<=[.!?])\s+", clean):
            if "[@src-" in sentence:
                continue
            for m in LITERAL_STAT_RE.finditer(sentence):
                hits.append(m.group(0))
    return hits
