"""Shared loading, schema-walking, and serialization for SimGrammar.

Everything structural is read from schema/registry.yaml, schema/*.json, and vocab/*.yaml.
No entity type, directory, vocab term, or edge type is hardcoded here.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
GEN_BLOCK_RE = re.compile(
    r"(<!-- BEGIN GENERATED: (?P<name>[a-z0-9_.-]+) -->\n)(?P<body>.*?)(<!-- END GENERATED: (?P=name) -->)",
    re.S,
)


# ---------------------------------------------------------------- loading

def read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_registry() -> dict:
    return read_yaml(ROOT / "schema" / "registry.yaml")


def load_vocabs() -> dict[str, dict]:
    vocabs: dict[str, dict] = {}
    for p in sorted((ROOT / "vocab").glob("*.yaml")):
        data = read_yaml(p)
        vocabs[p.stem] = data
    return vocabs


def vocab_terms(vocabs: dict, name: str) -> dict[str, dict]:
    v = vocabs.get(name)
    if not v or "terms" not in v:
        return {}
    return {str(t["id"]): t for t in v["terms"]}


def load_schemas() -> dict[str, dict]:
    out = {}
    for p in sorted((ROOT / "schema").glob("*.schema.json")):
        out[p.name] = json.loads(p.read_text(encoding="utf-8"))
    return out


@dataclass
class Entity:
    type: str
    id: str
    path: Path
    data: dict
    derived: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.data.get("name") or self.data.get("id")


def load_entities(registry: dict | None = None, include_meta: bool = True) -> tuple[dict[str, list[Entity]], list[tuple[Path, str]]]:
    """Return ({type: [Entity]}, parse_errors)."""
    registry = registry or load_registry()
    out: dict[str, list[Entity]] = {}
    errors: list[tuple[Path, str]] = []
    for tname, spec in registry["types"].items():
        if spec.get("meta") and not include_meta:
            continue
        ents = []
        d = ROOT / spec["dir"]
        for p in sorted(d.glob("*.yaml")):
            try:
                data = read_yaml(p)
            except yaml.YAMLError as exc:  # noqa: PERF203
                errors.append((p, f"YAML parse error: {exc}"))
                continue
            if not isinstance(data, dict):
                errors.append((p, "File must contain one YAML mapping (one entity)."))
                continue
            ents.append(Entity(type=tname, id=str(data.get("id", "")), path=p, data=data))
        out[tname] = ents
    return out, errors


# ---------------------------------------------------------------- schema

def schema_registry(schemas: dict[str, dict]) -> Registry:
    resources = []
    for fname, sch in schemas.items():
        res = Resource.from_contents(sch)
        resources.append((sch["$id"], res))
        resources.append((fname, res))
    return Registry().with_resources(resources)


def validator_for(schema: dict, registry: Registry) -> Draft202012Validator:
    return Draft202012Validator(schema, registry=registry)


def _resolve_chain(node: dict, base: str, schemas: dict[str, dict]) -> list[tuple[dict, str]]:
    chain = [(node, base)]
    seen = 0
    while isinstance(node, dict) and "$ref" in node:
        seen += 1
        if seen > 20:
            raise RuntimeError(f"$ref loop at {base}")
        ref = node["$ref"]
        file, _, frag = ref.partition("#")
        newbase = file or base
        target: Any = schemas[newbase]
        for part in [p for p in frag.strip("/").split("/") if p]:
            target = target[part]
        node, base = target, newbase
        chain.append((node, base))
    return chain


def _first(chain, key):
    for node, base in chain:
        if isinstance(node, dict) and key in node:
            return node[key], base
    return None, None


@dataclass
class Annotation:
    kind: str  # vocab | edge | ref | rubric
    name: str  # vocab name, edge type, ref type, rubric scale
    value: Any
    path: tuple
    parent: Any


def walk_annotations(schema_file: str, instance: Any, schemas: dict[str, dict]) -> Iterator[Annotation]:
    """Yield every x-vocab / x-edge / x-ref / x-rubric annotation hit in an instance."""
    root = schemas[schema_file]

    def walk(node, base, inst, path, parent):
        chain = _resolve_chain(node, base, schemas)
        if not isinstance(inst, (dict, list)):
            for key, kind in (("x-vocab", "vocab"), ("x-edge", "edge"), ("x-ref", "ref"), ("x-rubric", "rubric")):
                val, _ = _first(chain, key)
                if val is not None:
                    yield Annotation(kind, val, inst, path, parent)
            return
        if isinstance(inst, dict):
            props, pbase = _first(chain, "properties")
            if props:
                for k, v in inst.items():
                    if k in props:
                        yield from walk(props[k], pbase, v, path + (k,), inst)
        else:
            items, ibase = _first(chain, "items")
            if items is not None:
                for i, v in enumerate(inst):
                    yield from walk(items, ibase, v, path + (i,), inst)

    yield from walk(root, schema_file, instance, (), None)


# ---------------------------------------------------------------- edges

@dataclass(frozen=True)
class Edge:
    source: str
    type: str
    target: str
    attrs: tuple  # sorted (key, value) pairs
    path: tuple

    def attr_dict(self) -> dict:
        return dict(self.attrs)


def extract_edges(ent: Entity, schemas: dict[str, dict], registry: dict) -> list[Edge]:
    sfile = Path(registry["types"][ent.type]["schema"]).name
    edges = []
    for ann in walk_annotations(sfile, ent.data, schemas):
        if ann.kind != "edge":
            continue
        attrs: tuple = ()
        if ann.path and ann.path[-1] == "id" and isinstance(ann.parent, dict):
            attrs = tuple(sorted((k, v) for k, v in ann.parent.items() if k != "id"))
        edges.append(Edge(ent.id, ann.name, str(ann.value), attrs, ann.path))
    return edges


# ---------------------------------------------------------------- serialization

def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def pretty_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def to_csv(rows: list[dict], columns: list[str]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        w.writerow([_cell(r.get(c)) for c in columns])
    return buf.getvalue()


def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.4f}".rstrip("0").rstrip(".")
    if isinstance(v, (list, tuple)):
        return ";".join(_cell(x) for x in v)
    if isinstance(v, dict):
        return canonical_json(v)
    return str(v)


class _Dumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_presenter)


def dump_yaml(obj: Any) -> str:
    return yaml.dump(obj, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=100)


def replace_generated_blocks(text: str, blocks: dict[str, str]) -> tuple[str, list[str]]:
    """Replace every GENERATED block whose name is in `blocks`. Returns (new_text, unknown_names)."""
    unknown = []

    def sub(m):
        name = m.group("name")
        if name not in blocks:
            unknown.append(name)
            return m.group(0)
        body = blocks[name].rstrip("\n") + "\n"
        return m.group(1) + body + m.group(4)

    return GEN_BLOCK_RE.sub(sub, text), unknown


CALIBRATION_SCALES = ("legibility", "emergence_potential", "authoring_cost", "compute_cost", "tuning_difficulty", "ai_leverage")


def load_calibration(registry: dict) -> dict | None:
    """The current calibration set (registry `contribution.calibration_set`)."""
    rel = (registry.get("contribution") or {}).get("calibration_set")
    p = ROOT / rel if rel else None
    return read_yaml(p) if p and p.exists() else None


def load_calibration_sets() -> dict[str, dict]:
    """Every calibration set in calibration/, by id. Retired sets stay so merged runs keep the set they were scored on."""
    out = {}
    for p in sorted((ROOT / "calibration").glob("*.yaml")):
        d = read_yaml(p) or {}
        if d.get("id"):
            d["_path"] = p
            out[str(d["id"])] = d
    return out


def normalize_model(m) -> str:
    """Model ids compared without case, punctuation, or spacing: claude-opus-5.5 and Claude Opus 5-5 are the same model."""
    return re.sub(r"[^a-z0-9]", "", str(m or "").lower())


WIKI_HOST = re.compile(r"(^|\.)(wikipedia\.org|wikimedia\.org|fandom\.com|wikia\.(com|org)|wiki\.gg|wikidot\.com)$|wiki", re.I)


def is_wiki_source(src: dict) -> bool:
    """Encyclopedia kind, or a url whose host is a wiki farm or names a wiki, whatever kind the record claims (E034)."""
    if src.get("kind") == "encyclopedia":
        return True
    url = str(src.get("url") or "")
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    return bool(host and WIKI_HOST.search(host)) or "/wiki/" in url


def archive_target(archived: str) -> str:
    """The url inside a Wayback snapshot url."""
    m = re.match(r"^https://web\.archive\.org/web/[0-9]{8,14}(?:[a-z_]{2,3})?/(.+)$", archived or "")
    return m.group(1) if m else ""


def same_url(a: str, b: str) -> bool:
    def norm(u):
        return re.sub(r"^https?://(www\.)?", "", (u or "").strip()).rstrip("/").lower()
    return norm(a) == norm(b)


def calibration_agreement(gold: dict, scores: dict) -> dict:
    """Agreement of a rater's calibration scores with the frozen set.

    gold and scores map mechanic id -> {scale: 1..5}. Returns n (pairs compared), exact and within_one shares, and
    quadratic-weighted kappa (Cohen 1968) pooled across scales. Missing scores count as disagreements (distance 4).
    """
    pairs = []
    for mid in sorted(gold):
        for sc in CALIBRATION_SCALES:
            g = gold[mid].get(sc)
            if g is None:
                continue
            r = (scores.get(mid) or {}).get(sc)
            pairs.append((g, r))
    n = len(pairs)
    if not n:
        return {"n": 0, "exact": None, "within_one": None, "kappa_quadratic": None, "missing": 0}
    missing = sum(1 for _, r in pairs if r is None)
    exact = sum(1 for g, r in pairs if r == g) / n
    within = sum(1 for g, r in pairs if r is not None and abs(r - g) <= 1) / n
    full = [(g, r) for g, r in pairs if r is not None]
    kappa = None
    if full:
        cats = range(1, 6)
        obs = {(i, j): 0 for i in cats for j in cats}
        for g, r in full:
            obs[(g, r)] += 1
        m = len(full)
        pg = {i: sum(obs[(i, j)] for j in cats) / m for i in cats}
        pr = {j: sum(obs[(i, j)] for i in cats) / m for j in cats}
        w = {(i, j): ((i - j) ** 2) / 16 for i in cats for j in cats}
        do = sum(w[k] * obs[k] / m for k in obs)
        de = sum(w[(i, j)] * pg[i] * pr[j] for i in cats for j in cats)
        kappa = 1 - do / de if de else None
    rnd = lambda x: None if x is None else round(float(x), 3)  # noqa: E731
    return {"n": n, "exact": rnd(exact), "within_one": rnd(within), "kappa_quadratic": rnd(kappa), "missing": missing}


def independent(a, b) -> bool:
    """Two runs (Entity objects) are independent when their operators differ and, if both are agent runs, their models
    differ too. A missing model on an agent run cannot establish independence."""
    if a is None or b is None:
        return False
    if str(a.data.get("operator", "")).strip().lower() == str(b.data.get("operator", "")).strip().lower():
        return False
    if a.data.get("actor") == "agent" and b.data.get("actor") == "agent":
        ma = normalize_model((a.data.get("agent") or {}).get("model"))
        mb = normalize_model((b.data.get("agent") or {}).get("model"))
        if not ma or not mb or ma == mb:
            return False
    return True


def rubric_fields(schema: dict) -> dict[str, str]:
    """Top-level fields of an entity schema scored on a rubric scale: {field: scale}."""
    return {k: v["x-rubric"] for k, v in schema.get("properties", {}).items() if isinstance(v, dict) and v.get("x-rubric")}


def lower_median(values: list) -> int | None:
    vs = sorted(v for v in values if isinstance(v, int) and not isinstance(v, bool))
    return vs[(len(vs) - 1) // 2] if vs else None


def plural(word: str) -> str:
    """The plural of an English noun as the site writes counts: opportunity → opportunities, game → games."""
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


def counted(n, one: str, many: str | None = None) -> str:
    """A count and its noun in the right number: "1 game", "2 games". `many` is for an irregular or multi-word plural."""
    return f"{n} {one if n == 1 else (many or plural(one))}"


def get_path(obj: dict, dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


# Prose that is rendered from the dataset and checked like the paper: tokens resolve (E019), links and citations
# resolve (E020), no literal dataset counts (E021), assertions hold (E029), no placeholders (E027).
PROSE_DIRS = {"report/src": "paper", "book/src": "book", "media/episodes": "episodes", "media/shorts": "shorts", "media/mega": "mega", "media/intro": "intro", "media/subtitles/ja": "subtitles"}


def prose_files() -> list[Path]:
    return [p for d in PROSE_DIRS for p in sorted((ROOT / d).glob("*.md"))]


def narration_digest(text: str) -> str:
    """A short hash of what a narration line says, its words only: links, citations, comments and emphasis dropped.
    scripts/video/publish.py takes it from a render's captions and scripts/web.py from the built script, so a scene whose
    numbers changed after the render is caught."""
    text = re.sub(r"<!--.*?-->", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s*\[\d+(?:,\s*\d+)*\]", "", text)
    return hashlib.sha256(" ".join(re.findall(r"[a-z0-9.%]+", text.lower())).encode()).hexdigest()[:12]
