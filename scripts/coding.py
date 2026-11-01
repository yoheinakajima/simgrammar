#!/usr/bin/env python3
"""A second coder for three coding decisions: the family of a mechanic, the mechanic admission tests, and the effect type
on an `affects` edge (review findings D3, D6, D4). Each was made by the run that created the record, so agreement on
them is unmeasured until someone else codes a sample (tasks/second-coding.md).

  python scripts/coding.py draw [--check]           draw the stratified sample from the seed in report/analysis.yaml
  python scripts/coding.py packet --run <run-id>    write the three coding sheets to coding-out/ (gitignored; --out DIR)
  python scripts/coding.py sheet admission          one sheet to stdout: admission, family, or effect
  (fill every null from the sheets alone, the admission sheet first)
  python scripts/coding.py record SHEET... --run <run-id>   check the codes and write report/coding/<run-id>.yaml

With --run, the sheets leave out the items that run may not code. Writing the sheets renders the paper's rules, so it
runs the analysis first (about ten seconds).

A codes file holds one coder's codes, entry by entry as a record's `ratings` hold rubric scores, and is never edited
after merge (a later coder adds a file of their own):

  run: <run-id>              a verification run in log/runs/; the independence check reads its operator and model
  operator: <handle>         that run's operator
  sample: second-coding-v1   the sample coded
  codes:
  - {decision: family, item: <mechanic>, value: <mechanic_family term>, rationale: <the rule that decided it>}
  - {decision: effect, item: <technique>/<mechanic>, value: <effect term>, rationale: <the clause that decided it>}
  - {decision: admission, item: <mechanic or candidate>, value: {nameable: pass, atomic: fail, tunable: pass,
     removable: pass}, rationale: <the test that decided it>}

The sheets give the written rules and each item's own description, never its current code: the rules come from §2.1
and §8.1 of the paper as the build renders them, and the sample leaves out the mechanics those rules use as examples.
The sample is drawn once and its ids are recorded in report/analysis.yaml (`second_coding.sample`), so a later data
change does not move it; `draw --check` says whether the current data still give the recorded draw.

The build reads report/coding/ (scripts/analyze.py) and reports Cohen's kappa and Krippendorff's alpha for each
decision when codes exist. It fails on a codes file whose run is not independent of every run that created or reviewed
a coded record, or proposed a coded mechanic or candidate: a different operator, and a different model when both runs
are agents, as E035 requires of ratings. One coder codes once (one file per operator and model).

Limits, stated plainly: the records and the current codes are public, so only the coder's procedure keeps the coding
blind, as with calibration (CONTRACT.md I14). The admitted mechanics were all coded as passing, and the dataset holds no
recorded judgment on the candidates it left as proposals (no run took them up), so agreement on admission compares a
coder with the dataset's current boundary, not with a second set of reasons.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import ID_RE, ROOT, dump_yaml, independent, load_entities, load_registry, load_vocabs, normalize_model, read_yaml, vocab_terms  # noqa: E402

DECISIONS = ("admission", "family", "effect")
TESTS = ("nameable", "atomic", "tunable", "removable")
CODING_DIR = ROOT / "report" / "coding"
METHOD = ROOT / "report" / "src" / "02-method.md"
IMPACT = ROOT / "report" / "src" / "08-impact.md"
LINK_RE = re.compile(r"\[\[([a-z0-9-]+)(?:\|([^\]]+))?\]\]")
# An edge whose note names its own effect gives the code away, so it is left out of the draw. One pattern per effect
# term; a term missing here stops the draw, so a vocabulary change has to say how to recognize the new term.
EFFECT_WORDS = {
    "replaces-substrate": r"\bsubstrate",
    "deepens": r"\bdeepen",
    "enables-new": r"\bnew form",
    "cuts-authoring-cost": r"\bauthoring cost",
    "explains": r"\bexplain",
    "tunes": r"\btun(?:e|es|ed|ing)\b|\bbalanc",
    "accelerates": r"\baccelerat",
}


def config() -> dict:
    return (read_yaml(ROOT / "report" / "analysis.yaml") or {}).get("second_coding") or {}


def _rank(seed, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def _plain(s) -> str:
    return " ".join(str(s or "").split())


def _live(ents, t):
    return sorted((e for e in ents.get(t, []) if not e.data.get("deprecated")), key=lambda e: e.id)


def _stem(s: str) -> str:
    """An id with each word's plural s dropped, so aspirations-wants and aspiration-wants compare equal."""
    return "-".join(w[:-1] if w.endswith("s") and len(w) > 3 else w for w in s.split("-"))


def open_candidates(ents) -> dict[str, dict]:
    """New-mechanic proposals in the run log that the vocabulary has not taken up, by target id, keeping the earliest
    proposal of each: {target: {"run": proposing run, "detail": its text}}. A proposal is taken up when a live mechanic
    has its id (up to plurals) or a taxonomy or bootstrap run names it outside its own proposals (renamed or merged when
    it was created)."""
    taken = {_stem(m.id) for m in _live(ents, "mechanic")}
    runs = sorted(ents.get("run", []), key=lambda r: r.id)  # ids begin with the date, so the earliest proposal comes first
    tax = " ".join(dump_yaml({k: v for k, v in r.data.items() if k != "proposals"}) for r in runs if r.data.get("kind") in ("taxonomy", "bootstrap"))
    out: dict[str, dict] = {}
    for r in runs:
        for p in r.data.get("proposals") or []:
            t = str(p.get("target") or "")
            if p.get("kind") != "new-mechanic" or not ID_RE.match(t) or t in out or _stem(t) in taken:
                continue
            if re.search(rf"(?<![a-z0-9-]){re.escape(t)}(?![a-z0-9-])", tax):
                continue
            out[t] = {"run": r.id, "detail": _plain(p.get("detail"))}
    return out


def _blocks(path: Path, start: str, end: str) -> list[str]:
    """The paragraphs of a report section, from the heading line starting with `start` to the one starting with `end`."""
    text = path.read_text(encoding="utf-8")
    i = text.index("\n" + start) + 1
    j = text.index("\n" + end, i)
    return [b.strip() for b in text[i:j].split("\n\n") if b.strip()][1:]


def rule_examples() -> set[str]:
    """Records §2.1 names. Its rules use them as worked examples, so their families are given away."""
    return {m.group(1) for b in _blocks(METHOD, "### 2.1", "### 2.2") for m in LINK_RE.finditer(b)}


def draw(ents, vocabs, cfg: dict) -> dict:
    """The stratified sample, from the data and the seed and sizes in `cfg` (report/analysis.yaml second_coding)."""
    seed, sp = cfg["seed"], cfg["sample"]
    fams = list(vocab_terms(vocabs, "mechanic_family"))
    effs = list(vocab_terms(vocabs, "effect"))
    missing = [e for e in effs if e not in EFFECT_WORDS]
    if missing:
        raise SystemExit(f"scripts/coding.py: EFFECT_WORDS has no pattern for {missing}")
    fam_terms = vocab_terms(vocabs, "mechanic_family")
    skip = rule_examples()
    mechs = []
    for f in fams:
        names = [f, fam_terms[f]["label"].lower(), fam_terms[f]["label"].lower().replace("&", "and")]
        ok = [m for m in _live(ents, "mechanic") if m.data.get("family") == f and m.id not in skip
              and not any(n in _plain(f"{m.data.get('summary')} {m.data.get('definition')}").lower() for n in names)]
        mechs += [m.id for m in sorted(ok, key=lambda m: _rank(seed, m.id))[: sp["per_family"]]]
    live_m = {m.id for m in _live(ents, "mechanic")}
    by_eff: dict[str, list[tuple[str, str]]] = {e: [] for e in effs}
    for t in _live(ents, "technique"):
        for a in t.data.get("affects") or []:
            if a.get("id") in live_m and not re.search(EFFECT_WORDS[a["effect"]], a.get("note") or "", re.I):
                by_eff[a["effect"]].append((t.id, a["id"]))
    # the smallest strata draw first, so the rare effects keep their few techniques; within a stratum, edges of
    # techniques not yet drawn come first, so the sample spreads across techniques
    edges, used = [], set()
    for e in sorted(effs, key=lambda e: (len(by_eff[e]), effs.index(e))):
        order = sorted(by_eff[e], key=lambda x: _rank(seed, f"{x[0]}/{x[1]}"))
        pick = [x for x in order if x[0] not in used][: sp["per_effect"]]
        pick += [x for x in order if x not in pick][: sp["per_effect"] - len(pick)]
        used |= {x[0] for x in pick}
        edges += [x for x in order if x in pick]
    cands = sorted(open_candidates(ents), key=lambda t: _rank(seed, t))[: sp["n_candidates"]]
    return {"mechanics": sorted(mechs), "candidates": sorted(cands), "edges": sorted(f"{t}/{m}" for t, m in edges)}


def sample_items(ents, cfg: dict | None = None) -> dict[str, dict[str, str]]:
    """The recorded sample's items that still resolve, with their current code: {decision: {item: code}}. A mechanic's
    family, an edge's effect, and for admission `admit` for a live mechanic or a candidate the vocabulary has since taken
    up, `reject` for one still left as a proposal. An item that no longer resolves (a deprecated mechanic, a removed
    edge) drops out."""
    cfg = config() if cfg is None else cfg
    sp = cfg.get("sample") or {}
    mech = {m.id: m for m in _live(ents, "mechanic")}
    eff = {f"{t.id}/{a['id']}": a["effect"] for t in _live(ents, "technique") for a in t.data.get("affects") or [] if a.get("id") in mech}
    still_open = open_candidates(ents)
    out = {"family": {i: mech[i].data["family"] for i in sp.get("mechanics") or [] if i in mech},
           "effect": {i: eff[i] for i in sp.get("edges") or [] if i in eff}}
    out["admission"] = {i: "admit" for i in out["family"]}
    out["admission"].update({i: "reject" if i in still_open else "admit" for i in sp.get("candidates") or []})
    return out


def coder_runs(ents, decision: str, item: str) -> list[str]:
    """The runs a coder of this item must be independent of: those that created or reviewed the record holding its
    code, and for a mechanic or candidate any run that proposed it (a proposal argues for admission and may name a
    family)."""
    by_id = {e.id: e for t, lst in ents.items() if t != "run" for e in lst}
    rec = by_id.get(item.split("/")[0] if decision == "effect" else item)
    out = []
    if rec is not None:
        pv = rec.data.get("provenance") or {}
        out += [pv.get("created")] + list(pv.get("reviewed") or [])
    if decision != "effect":
        for r in ents.get("run", []):
            if any(p.get("kind") == "new-mechanic" and p.get("target") == item for p in r.data.get("proposals") or []):
                out.append(r.id)
    return sorted({r for r in out if r})


def _check_value(decision: str, value, vocabs) -> str | None:
    if decision == "admission":
        if not isinstance(value, dict) or set(value) != set(TESTS) or any(v not in ("pass", "fail") for v in value.values()):
            return f"must give each of {', '.join(TESTS)} as pass or fail"
        return None
    terms = vocab_terms(vocabs, "mechanic_family" if decision == "family" else "effect")
    return None if value in terms else f"{value!r} is not a term of vocab/{'mechanic_family' if decision == 'family' else 'effect'}.yaml"


def check_coding(path: Path, data: dict, ents, vocabs, cfg: dict, items: dict) -> dict:
    """One codes file, checked. Returns {"run", "operator", "codes": {decision: {item: value}}}; raises ValueError."""
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    runs = {r.id: r for r in ents.get("run", [])}
    rid = str(data.get("run") or "")
    run = runs.get(rid)
    if path.stem != rid:
        raise ValueError(f"{rel}: the file is named after its run, so it must be {rid}.yaml")
    if run is None:
        raise ValueError(f"{rel}: run '{rid}' is not in log/runs/")
    if run.data.get("kind") != "verification":
        raise ValueError(f"{rel}: run '{rid}' is a {run.data.get('kind')} run; codes come from a verification run, as second ratings do")
    if str(data.get("operator", "")).strip().lower() != str(run.data.get("operator", "")).strip().lower():
        raise ValueError(f"{rel}: operator '{data.get('operator')}' is not the operator of run '{rid}'")
    if data.get("sample") != (cfg.get("sample") or {}).get("id"):
        raise ValueError(f"{rel}: sample '{data.get('sample')}' is not the recorded sample '{(cfg.get('sample') or {}).get('id')}'")
    codes: dict[str, dict] = {d: {} for d in DECISIONS}
    for i, c in enumerate(data.get("codes") or []):
        d, item = c.get("decision"), c.get("item")
        if d not in DECISIONS:
            raise ValueError(f"{rel}: codes[{i}] decision {d!r} is not one of {', '.join(DECISIONS)}")
        if item not in items[d]:
            raise ValueError(f"{rel}: codes[{i}] item '{item}' is not in the {d} sample")
        if item in codes[d]:
            raise ValueError(f"{rel}: codes[{i}] codes {d} of '{item}' a second time; one coder, one code")
        bad = _check_value(d, c.get("value"), vocabs)
        if bad:
            raise ValueError(f"{rel}: codes[{i}] ({d}, {item}) {bad}")
        if not _plain(c.get("rationale")) or re.search(r"\b(todo|tbd|fixme)\b", str(c.get("rationale")), re.I):
            raise ValueError(f"{rel}: codes[{i}] ({d}, {item}) needs a rationale naming the rule or test that decided it")
        for other in coder_runs(ents, d, item):
            if not independent(run, runs.get(other)):
                raise ValueError(f"{rel}: run '{rid}' codes {d} of '{item}' but is not independent of run '{other}', which created, reviewed, "
                                 "or proposed it: a coder has a different operator, and a different model when both runs are agents (E035, as for ratings)")
        codes[d][item] = c["value"]
    if not any(codes.values()):
        raise ValueError(f"{rel}: no codes")
    return {"run": rid, "operator": run.data.get("operator"), "model": normalize_model((run.data.get("agent") or {}).get("model")) if run.data.get("actor") == "agent" else "", "codes": codes}


def load_codings(ents, vocabs, cfg: dict | None = None) -> list[dict]:
    """Every codes file in report/coding/, checked (check_coding), in run order. Raises ValueError on the first problem,
    and when two files come from the same operator and model: one coder codes once."""
    cfg = config() if cfg is None else cfg
    items = sample_items(ents, cfg)
    out, seen = [], {}
    for p in sorted(CODING_DIR.glob("*.yaml")) if CODING_DIR.exists() else []:
        c = check_coding(p, read_yaml(p) or {}, ents, vocabs, cfg, items)
        who = (str(c["operator"]).strip().lower(), c["model"])
        if who in seen:
            raise ValueError(f"{p.relative_to(ROOT)}: runs {seen[who]} and {c['run']} share an operator and model; one coder, one set of codes")
        seen[who] = c["run"]
        out.append(c)
    return out


# ---------------------------------------------------------------- sheets

def _rendered(blocks: list[str], ctx) -> str:
    """Report paragraphs as the paper renders them, with links reduced to their text."""
    from report_render import render
    out, errs = render("\n\n".join(blocks), ctx, "paper")
    if errs:
        raise SystemExit(f"scripts/coding.py: the rules do not render: {errs[:3]}")
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", out).strip()


def _context():
    import analyze
    from lib import extract_edges, load_schemas
    from report_render import Context
    reg, vocabs, schemas = load_registry(), load_vocabs(), load_schemas()
    ents, _ = load_entities(reg)
    types = [t for t, s in reg["types"].items() if not s.get("meta")]
    edges = [ed for t in types for e in ents.get(t, []) for ed in extract_edges(e, schemas, reg)]
    return Context(ents, edges, analyze.compute(ents, edges, vocabs), vocabs, reg), ents, vocabs


NO_PEEKING = ("Read only this sheet. Do not open data/, log/, report/, the paper, the book, or the website until all three sheets "
              "are coded: they hold the current codes. Code the admission sheet first, since the family sheet lists only "
              "admitted mechanics. Fill every null, then return the sheets to `python scripts/coding.py record`.")


def sheets(ctx, ents, vocabs, cfg: dict | None = None, run: str | None = None) -> dict[str, dict]:
    """The three sheets. With `run`, the coder's run, the items it may not code (those created, reviewed, or proposed by
    a run it is not independent of) are left out and named on stderr, so a coder never codes what `record` refuses."""
    cfg = config() if cfg is None else cfg
    sp, seed = cfg["sample"], cfg["seed"]
    items = sample_items(ents, cfg)
    if run is not None:
        runs = {r.id: r for r in ents.get("run", [])}
        if run not in runs:
            raise SystemExit(f"run '{run}' is not in log/runs/; open it first: python scripts/new.py run <slug> --kind verification ...")
        barred = sorted({(d, i) for d in DECISIONS for i in items[d] if not all(independent(runs[run], runs.get(o)) for o in coder_runs(ents, d, i))})
        if len(barred) == sum(len(v) for v in items.values()):
            raise SystemExit(f"run '{run}' is not independent of the runs that made the sampled records, so it cannot code any of them")
        if barred:
            print(f"left out {len(barred)} item(s) run '{run}' may not code: " + ", ".join(f"{d} {i}" for d, i in barred), file=sys.stderr)
        items = {d: {i: v for i, v in items[d].items() if (d, i) not in barred} for d in DECISIONS}
    by_id = {e.id: e for t, lst in ents.items() if t != "run" for e in lst}
    proposal = {}  # a candidate's text: its earliest new-mechanic proposal, whether or not it has since been taken up
    for r in sorted(ents.get("run", []), key=lambda r: r.id):
        for p in r.data.get("proposals") or []:
            if p.get("kind") == "new-mechanic":
                proposal.setdefault(p.get("target"), _plain(p.get("detail")))
    order = lambda ids: sorted(ids, key=lambda i: _rank(seed, f"order:{i}"))  # noqa: E731
    sec21 = _blocks(METHOD, "### 2.1", "### 2.2")
    k = next(i for i, b in enumerate(sec21) if b.startswith("Each mechanic belongs to one of"))

    def mech_row(m):
        d = by_id[m].data
        return {"name": d["name"], "summary": _plain(d["summary"]), "definition": _plain(d["definition"]), "design_levers": d.get("design_levers") or []}

    adm = {}
    for i in order(items["admission"]):
        if i in by_id and by_id[i].type == "mechanic":
            row = mech_row(i)
            row = {"name": row["name"], "description": f"{row['summary']} {row['definition']}", "design_levers": row["design_levers"]}
        else:
            row = {"name": i.replace("-", " ").capitalize(), "description": proposal.get(i, "")}
        adm[i] = {**row, **{t: None for t in TESTS}, "rationale": None}
    out = {"admission": {
        "sample": sp["id"], "decision": "admission",
        "instructions": ("Code each item on the four admission tests below: pass or fail for each test. Items are in a fixed random "
                         "order. Some are mechanics in the vocabulary, described by their summary, definition, and design levers; "
                         "the rest are mechanics that a research run proposed and the vocabulary has not taken up, described by "
                         "the proposal's own text, which may argue for or against admitting them. Apply the same tests to both. "
                         "Where a test needs knowledge of other games, use your own and say so. In rationale, name the test that "
                         "decided the item. " + NO_PEEKING),
        "tests": _rendered(sec21[:k], ctx),
        "items": adm}}
    fam = vocab_terms(vocabs, "mechanic_family")
    out["family"] = {
        "sample": sp["id"], "decision": "family",
        "instructions": ("Assign each mechanic one family with the rules below, which apply in order (the first that fits decides), "
                         "and the family definitions. Write the family id in code and, in rationale, the number of the rule that "
                         "decided it and the variable it turned on. " + NO_PEEKING),
        "rules": _rendered(sec21[k:k + 2], ctx),
        "families": {f: f"{t['label']}: {t['definition']}" for f, t in fam.items()},
        "items": {m: {**mech_row(m), "code": None, "rationale": None} for m in order(items["family"])}}
    eff = vocab_terms(vocabs, "effect")
    rt = vocab_terms(vocabs, "runtime")
    para = next(b for b in _blocks(IMPACT, "### 8.1", "### 8.2") if b.startswith("**Coding rule.**"))
    rule = para[: para.index(" The order was written down")]
    pairs = [i.split("/") for i in order(items["effect"])]
    out["effect"] = {
        "sample": sp["id"], "decision": "effect",
        "instructions": ("Label each edge with one effect, using the coding rule below and the effect definitions. An edge is a "
                         "technique (under techniques) changing a mechanic (under mechanics), and its note says what changes. "
                         "Write the effect id in code and, in rationale, the clause of the rule that decided it. " + NO_PEEKING),
        "rule": _rendered([rule], ctx),
        "effects": {e: f"{t['label']}: {t['definition']}" for e, t in eff.items()},
        "techniques": {t: {"name": by_id[t].data["name"], "summary": _plain(by_id[t].data["summary"]), "mechanism": _plain(by_id[t].data.get("mechanism")),
                           "runtime": [rt.get(r, {}).get("label", r) for r in by_id[t].data.get("runtime") or []]}
                       for t in sorted({t for t, _ in pairs})},
        "mechanics": {m: {"name": by_id[m].data["name"], "summary": _plain(by_id[m].data["summary"])} for m in sorted({m for _, m in pairs})},
        "items": {f"{t}/{m}": {"technique": t, "mechanic": m,
                               "note": _plain(next(a.get("note") for a in by_id[t].data.get("affects") or [] if a["id"] == m)),
                               "code": None, "rationale": None} for t, m in pairs}}
    return out


def record(paths: list[Path], rid: str) -> int:
    reg, vocabs = load_registry(), load_vocabs()
    ents, _ = load_entities(reg)
    cfg = config()
    run = next((r for r in ents.get("run", []) if r.id == rid), None)
    if run is None:
        raise SystemExit(f"run '{rid}' is not in log/runs/; open it first: python scripts/new.py run <slug> --kind verification ...")
    codes, problems = [], []
    for p in paths:
        sh = read_yaml(p) or {}
        d = sh.get("decision")
        for item, row in (sh.get("items") or {}).items():
            value = {t: row.get(t) for t in TESTS} if d == "admission" else row.get("code")
            if value is None or (d == "admission" and None in value.values()) or row.get("rationale") is None:
                problems.append(f"{p}: {item} is not fully coded")
                continue
            codes.append({"decision": d, "item": item, "value": value, "rationale": _plain(row.get("rationale"))})
    if problems:
        raise SystemExit("\n".join(problems[:20]) + "\nfill every null first")
    codes.sort(key=lambda c: (DECISIONS.index(c["decision"]) if c["decision"] in DECISIONS else 9, c["item"]))
    data = {"run": rid, "operator": run.data.get("operator"), "sample": (cfg.get("sample") or {}).get("id"), "codes": codes}
    out = CODING_DIR / f"{rid}.yaml"
    if out.exists():
        raise SystemExit(f"{out.relative_to(ROOT)} exists; one coder, one set of codes")
    check_coding(out, data, ents, vocabs, cfg, sample_items(ents, cfg))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Codes from one second coder, written by `python scripts/coding.py record`. Never edited after merge.\n" + dump_yaml(data), encoding="utf-8")
    print(f"wrote {len(codes)} codes to {out.relative_to(ROOT)}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    dp = sub.add_parser("draw")
    dp.add_argument("--check", action="store_true", help="compare a fresh draw with the sample recorded in report/analysis.yaml")
    pp = sub.add_parser("packet")
    pp.add_argument("--out", type=Path, default=ROOT / "coding-out")
    sp = sub.add_parser("sheet")
    sp.add_argument("decision", choices=DECISIONS)
    for p in (pp, sp):
        p.add_argument("--run", help="the coder's run: leave out the items it may not code")
    rp = sub.add_parser("record")
    rp.add_argument("paths", type=Path, nargs="+")
    rp.add_argument("--run", required=True)
    args = ap.parse_args()
    if args.cmd == "draw":
        reg, vocabs = load_registry(), load_vocabs()
        ents, _ = load_entities(reg)
        cfg = config()
        new = draw(ents, vocabs, cfg)
        if not args.check:
            sys.stdout.write(dump_yaml(new))
            return
        rec = {k: sorted(cfg["sample"].get(k) or []) for k in new}
        diff = {k: (sorted(set(rec[k]) - set(new[k])), sorted(set(new[k]) - set(rec[k]))) for k in new}
        for k, (gone, added) in diff.items():
            print(f"{k}: {len(rec[k])} recorded, {len(new[k])} drawn now" + (f"; recorded only {gone}; drawn only {added}" if gone or added else ", same"))
        sys.exit(1 if any(g or a for g, a in diff.values()) else 0)
    if args.cmd == "record":
        sys.exit(record(args.paths, args.run))
    ctx, ents, vocabs = _context()
    out = sheets(ctx, ents, vocabs, run=args.run)
    if args.cmd == "sheet":
        sys.stdout.write(dump_yaml(out[args.decision]))
        return
    if args.cmd == "packet":
        args.out.mkdir(parents=True, exist_ok=True)
        for d in DECISIONS:
            (args.out / f"{d}.yaml").write_text(dump_yaml(out[d]), encoding="utf-8")
        print(f"wrote {', '.join(f'{d}.yaml' for d in DECISIONS)} to {args.out}")


if __name__ == "__main__":
    main()
