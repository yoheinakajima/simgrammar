#!/usr/bin/env python3
"""The panel: a blind second reading of every single-rater judgment the paper rests on, as sheets a coder fills from
the sheets alone (review findings D3, D4, D6, D8, E2, E17, E31; tasks/second-rating.md).

  python scripts/panel.py draw [--check]          draw the panel samples from the seed in report/analysis.yaml (panel)
  python scripts/panel.py packet --run <run-id> [--cross-model] [--out DIR]
                                                  write every sheet, INSTRUCTIONS.md and manifest.yaml to panel-out/
                                                  (gitignored); a coder with no repository and no web access fills
                                                  them from those files alone
  python scripts/panel.py sheet <kind>            one kind's files to stdout, every item included
  python scripts/panel.py record DIR --run <run-id> [--cross-model] [--kinds a,b] [--dry-run]
                                                  check the filled sheets in DIR and record them

The sheets, in the order a coder fills them (each later sheet shows something an earlier one asks for):

  admission, family, effect   scripts/coding.py's three sheets on the second-coding-v1 sample (§2.1, §8.1)
  state                       each sampled mechanic's state class (D6): simulation state, control, meta-structure, or
                              presentation, by the rules of report/state-class.yaml quoted word for word
  recall                     for a random sample of mechanics, which techniques change each one and how (E2): the
                              mechanic's description and every live technique's, never an `affects` list
  maturity                    every live technique's maturity, TRL and horizon in games (E17), from its own text
  rubric                      the calibration set first (calibrate.py's sheet, E036), then a random sample of mechanics
                              on the six mechanic scales (D8)
  opportunity                 every live opportunity's novelty, feasibility and impact (E31)

Recall comes before effect because the effect sheet shows edges, and opportunity comes last because it pairs mechanics
with techniques. No sheet shows a stored code or score, a field that restates one, or another sheet's answer.

Two ways to record, never pooled:

  --cross-model   a run of kind `maintenance` whose model differs from the model of every agent run that created,
                  reviewed, rated, or proposed a coded item; its operator may be the records' own. Everything goes to
                  report/cross-model/<run-id>.yaml, and no record changes. The build reports it as a cross-model check
                  (analyze.py _cross_model, stats xm_*), never as independent agreement: the operator who made the
                  records chose the model and ran it.
  (default)       an independent verification run (E035: a different operator, and a different model when both runs
                  are agents). Codes go to report/coding/: admission, family and effect in scripts/coding.py's file
                  (report/coding/<run-id>.yaml), the other sheets' codes in report/coding/<kind>/<run-id>.yaml. Scores
                  go into the records as `ratings` (I14, E037): the creator's original score as a rating, the new one,
                  the lower median stored, and the run appended to provenance.reviewed. The calibration goes into the
                  run file, and mechanic ratings are written only when it passes (E036).

A codes file in report/coding/<kind>/ holds one coder's codes, as coding.py's does, and is never edited after merge:

  run: <run-id>          a verification run in log/runs/
  operator: <handle>     that run's operator
  sample: <sample id>    the sample coded (report/analysis.yaml panel)
  codes:
  - {decision: recall, item: <mechanic>, value: [{technique: <id>, effect: <effect term>, rationale: ...}], rationale: ...}
  - {decision: maturity, item: <technique>, value: <technique_maturity term>, rationale: ...}
  - {decision: horizon, item: <technique>, value: <horizon term>, rationale: ...}
  - {decision: state, item: <mechanic>, value: <class id of report/state-class.yaml>, rationale: ...}

A cross-model file holds the same codes for every sheet, `ratings` as {field, item, value, rationale}, and the
calibration scores, under the run, operator and model that made them.

To add a sheet kind (as `state` was added for report/state-class.yaml): write a Kind (its items with their
current codes, the runs a coder must be independent of, its sheet files, a reader for the filled rows, a check for one
recorded value, and its categories' labels), add it to KINDS in fill order, give it a sample under `panel` in
report/analysis.yaml (and SAMPLE_KEY, with a pool in draw()), and the rest follows from KINDS: the packet, the recorder
in both modes, report/coding/<kind>/ for independent codes, and analyze.py's agreement on every nominal code decision
(<p>kappa_<decision>, <p>alpha_<decision>, with intervals; a ratings field needs a rubric scale).

Limits, stated plainly: the records and the current codes are public, so only the coder's procedure keeps the work
blind, as with calibration (CONTRACT.md I14). A cross-model run by the records' operator shows whether another model
reading the same rules reaches the same codes; it cannot show that a different person would.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coding  # noqa: E402
from lib import (  # noqa: E402
    CALIBRATION_SCALES,
    ROOT,
    calibration_agreement,
    dump_yaml,
    independent,
    load_calibration,
    load_calibration_sets,
    load_entities,
    load_registry,
    load_vocabs,
    lower_median,
    normalize_model,
    read_yaml,
    vocab_terms,
)

CROSS_DIR = ROOT / "report" / "cross-model"
CODING_DIR = coding.CODING_DIR
TECHNIQUES_MD = ROOT / "report" / "src" / "07-techniques.md"
MECH_SCALES = tuple(CALIBRATION_SCALES)
OPP_SCALES = ("novelty", "feasibility", "impact")
PLACEHOLDER = re.compile(r"\b(todo|tbd|fixme)\b", re.I)
CROSS_KIND = "maintenance"   # a cross-model run verifies and rates nothing, so it is not a verification run

BLIND = ("Use only the files of this packet. Do not open or search for the SimGrammar repository, paper, book, or website, "
         "and do not search the web: they show the current codes and scores. Fill the sheets in the order of their file "
         "numbers, each once, and do not go back to change a sheet after reading a later one. Replace every null and change "
         "nothing else.")


def config() -> dict:
    return (read_yaml(ROOT / "report" / "analysis.yaml") or {}).get("panel") or {}


def _rank(seed, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode()).hexdigest()


def _plain(s) -> str:
    return " ".join(str(s or "").split())


def _live(ents, t):
    return sorted((e for e in ents.get(t, []) if not e.data.get("deprecated")), key=lambda e: e.id)


def _by_id(ents):
    return {e.id: e for t, lst in ents.items() if t != "run" for e in lst}


def original(rec, field):
    """A record's original score on a field: the creating run's rating when the field has ratings, else the stored value."""
    created = (rec.data.get("provenance") or {}).get("created")
    for r in rec.data.get("ratings") or []:
        if r.get("field") == field and r.get("run") == created:
            return r.get("value")
    return rec.data.get(field)


def record_runs(rec) -> list[str]:
    """Every run that made or re-read a record's codes and scores: its creator, its reviewers, and its raters."""
    if rec is None:
        return []
    pv = rec.data.get("provenance") or {}
    out = [pv.get("created")] + list(pv.get("reviewed") or []) + [r.get("run") for r in rec.data.get("ratings") or []]
    return sorted({r for r in out if r})


def record_ratable(vocabs, field: str) -> bool:
    """Whether a record's `ratings` can hold a field's scores: a rating's value is schema/common.schema.json $defs.score,
    which stops at 5, so the nine-level trl scale cannot be rated in a record until the schema allows it. An independent
    TRL reading stays in its codes file meanwhile (report/coding/maturity/), and moves into the records unchanged once the
    schema's limit reaches the scale."""
    import json
    top = json.loads((ROOT / "schema" / "common.schema.json").read_text(encoding="utf-8"))["$defs"]["score"].get("maximum", 5)
    return max(int(k) for k in vocabs["rubrics"]["scales"][field]["levels"]) <= int(top)


def _model(run) -> str:
    return normalize_model((run.data.get("agent") or {}).get("model")) if run is not None and run.data.get("actor") == "agent" else ""


def admits(mode: str, run, other) -> bool:
    """Whether `run` may code an item that `other` made or re-read. Independent: a different operator, and a different
    model when both are agent runs (E035). Cross-model: a different model from every agent run, whatever the operator."""
    if other is None:
        return False
    if other.id == run.id:   # the coder's own run, once it has rated the record too
        return True
    if mode == "independent":
        return independent(run, other)
    if other.data.get("actor") != "agent":
        return True
    return bool(_model(run)) and _model(run) != _model(other)


# ---------------------------------------------------------------- samples

def draw(ents, vocabs, cfg: dict, sc: dict) -> dict:
    """The panel samples from the data and the seed and sizes in `cfg` (report/analysis.yaml panel). Recall leaves out
    the mechanics the effect sheet shows an edge of (sc: second_coding), so that sheet cannot give a recall answer away;
    the rubric sample leaves out the calibration set, which the rubric sheet scores first. Each ranks its candidates by
    sha256(seed:kind:id) and takes the first n, so a larger n keeps the earlier draw."""
    seed = cfg["seed"]
    mechs = [m.id for m in _live(ents, "mechanic")]
    shown = {e.split("/")[1] for e in (sc.get("sample") or {}).get("edges") or []}
    cal = set((load_calibration(load_registry()) or {}).get("mechanics") or {})
    out = {}
    for kind, pool in (("recall", [m for m in mechs if m not in shown]), ("rubric", [m for m in mechs if m not in cal])):
        n = int(cfg[kind]["n"])
        out[kind] = sorted(sorted(pool, key=lambda i: _rank(seed, f"{kind}:{i}"))[:n])
        out[f"{kind}_pool"] = len(pool)
    out["maturity"] = [t.id for t in _live(ents, "technique")]
    out["opportunity"] = [o.id for o in _live(ents, "opportunity")]
    # state: stratified by the current class with equal allocation, as second_coding draws families: per_class mechanics
    # from each class, or all that remain in a smaller one, leaving out the worked examples and every mechanic the rules
    # name, since the sheet quotes the rules
    sf = state_file()
    cls = state_classes(sf)
    skip = state_examples(sf) | state_named(ents, sf)
    per = int(cfg["state"]["per_class"])
    picked, pools = [], {}
    for c in (c["id"] for c in sf.get("classes") or []):
        pool = [m for m in mechs if cls.get(m) == c and m not in skip]
        pools[c] = len(pool)
        picked += sorted(pool, key=lambda i: _rank(seed, f"state:{i}"))[:per]
    out["state"] = sorted(picked)
    out["state_pool"] = pools
    out["state_left_out"] = sorted(skip)
    return out


SAMPLE_KEY = {"recall": "mechanics", "rubric": "mechanics", "maturity": "techniques", "opportunity": "opportunities", "state": "mechanics"}
STATE_FILE = ROOT / "report" / "state-class.yaml"


def state_file() -> dict:
    """report/state-class.yaml: each live mechanic's state class, the rules that decide it, and their worked examples."""
    return (read_yaml(STATE_FILE) if STATE_FILE.exists() else None) or {}


def state_classes(sf: dict) -> dict[str, str]:
    return {e["id"]: e["class"] for e in sf.get("mechanics") or []}


def state_examples(sf: dict) -> set[str]:
    return {x["mechanic"] for c in sf.get("classes") or [] for x in c.get("examples") or []}


def state_rules_text(sf: dict) -> str:
    """The text the state sheet quotes: the procedure, each class's definition, and the worked examples' reasons."""
    parts = [sf.get("procedure") or ""] + [c.get("definition") or "" for c in sf.get("classes") or []]
    parts += [x.get("why") or "" for c in sf.get("classes") or [] for x in c.get("examples") or []]
    return _plain(" ".join(parts))


def state_named(ents, sf: dict) -> set[str]:
    """Live mechanics the state rules name, by name, id read as words, or alias (weather, say, or "queues" for service
    queues): the sheet quotes the rules, so these would come with a hint, and the draw leaves them out."""
    txt = state_rules_text(sf).lower()
    out = set()
    for m in _live(ents, "mechanic"):
        names = {m.data["name"].lower(), m.id.replace("-", " ")} | {str(a).lower() for a in m.data.get("aliases") or []}
        if any(re.search(r"(?<![a-z])" + re.escape(n) + r"(?![a-z])", txt) for n in names):
            out.add(m.id)
    return out


def sample_ids(cfg: dict, kind: str) -> list[str]:
    return list((cfg.get(kind) or {}).get(SAMPLE_KEY[kind]) or [])


# ---------------------------------------------------------------- kinds

@dataclass(frozen=True)
class Kind:
    """One sheet kind. `codes` are vocabulary decisions and `ratings` rubric fields the sheet asks for; `first` gives the
    dataset's current code or original score of every sampled item that still resolves ({decision: {item: value}});
    `owners` the runs a coder of an item must be independent of; `build` the sheet files in fill order, as (stem, sheet)
    pairs, a sheet with no `items` being a reference file; `read` turns one filled item into answers or problems; `check`
    says what is wrong with one recorded code value (None when nothing is); `labels` gives each nominal code decision's
    categories in order with their labels, which the build's agreement tables use ({decision: {code: label}});
    `stratified` says the sample was drawn within strata of the current code, so its intervals resample within them."""
    name: str
    codes: tuple[str, ...]
    ratings: tuple[str, ...]
    sample_id: Callable[[dict, dict], str]
    first: Callable
    owners: Callable
    build: Callable
    read: Callable
    check: Callable | None = None
    labels: Callable | None = None
    stratified: bool = False


def _sc() -> dict:
    return coding.config()


def _first_coding(decision):
    def f(ents, vocabs, cfg, sc):
        return {decision: coding.sample_items(ents, sc)[decision]}
    return f


def _owners_coding(decision):
    def f(ents, item):
        return coding.coder_runs(ents, decision, item)
    return f


def _first_recall(ents, vocabs, cfg, sc):
    live_m = {m.id for m in _live(ents, "mechanic")}
    rec = {m: {} for m in sample_ids(cfg, "recall") if m in live_m}
    for t in _live(ents, "technique"):
        for a in t.data.get("affects") or []:
            if a.get("id") in rec:
                rec[a["id"]][t.id] = a["effect"]
    return {"recall": rec}


def _owners_recall(ents, item):
    """The mechanic's runs and every live technique's: the recorded edges of a mechanic live on the technique records."""
    by = _by_id(ents)
    out = set(record_runs(by.get(item)))
    for t in _live(ents, "technique"):
        out |= set(record_runs(t))
    return sorted(out)


def _first_state(ents, vocabs, cfg, sc):
    live_m = {m.id for m in _live(ents, "mechanic")}
    cls = state_classes(state_file())
    return {"state": {m: cls[m] for m in sample_ids(cfg, "state") if m in live_m and m in cls}}


def _owners_state(ents, item):
    """The run that made report/state-class.yaml (its made_by) and the mechanic's own runs."""
    made = (state_file().get("made_by") or {}).get("run")
    return sorted({r for r in [made] + record_runs(_by_id(ents).get(item)) if r})


def _first_maturity(ents, vocabs, cfg, sc):
    by = _by_id(ents)
    ids = [t for t in sample_ids(cfg, "maturity") if t in by and not by[t].data.get("deprecated")]
    return {"maturity": {t: by[t].data.get("maturity") for t in ids}, "horizon": {t: by[t].data.get("horizon") for t in ids},
            "trl": {t: original(by[t], "trl") for t in ids}}


def _first_rated(kind, fields):
    def f(ents, vocabs, cfg, sc):
        by = _by_id(ents)
        ids = [i for i in sample_ids(cfg, kind) if i in by and not by[i].data.get("deprecated")]
        return {fld: {i: original(by[i], fld) for i in ids} for fld in fields}
    return f


def _owners_record(ents, item):
    return record_runs(_by_id(ents).get(item))


def _first_calibration(ents):
    cal = load_calibration(load_registry()) or {}
    return cal.get("id"), cal.get("mechanics") or {}


# -------- sheet text

def _blocks(path: Path, start: str, end: str) -> list[str]:
    return coding._blocks(path, start, end)


def maturity_rule(ctx) -> str:
    """§7.1's paragraph on how maturity is judged, as the paper renders it: it maps the maturity levels to evidence and
    to TRL, and names no technique."""
    para = [b for b in _blocks(TECHNIQUES_MD, "### 7.1", "### 7.2") if b.startswith("**How maturity is judged.**")]
    if not para:
        raise SystemExit("scripts/panel.py: §7.1 has no paragraph starting '**How maturity is judged.**'; the maturity sheet gives that rule")
    return coding._rendered(para[:1], ctx)


def _anchors(vocabs, scales) -> dict:
    rub = vocabs["rubrics"]["scales"]
    return {s: {"question": rub[s]["question"], "levels": {int(k): v for k, v in rub[s]["levels"].items()}} for s in scales}


def _terms(vocabs, name) -> dict:
    return {k: f"{t['label']}: {t['definition']}" for k, t in vocab_terms(vocabs, name).items()}


def _order(seed, ids):
    return sorted(ids, key=lambda i: _rank(seed, f"order:{i}"))


def _chunks(ids: list, size: int) -> list[list]:
    size = max(int(size or len(ids) or 1), 1)
    return [ids[i:i + size] for i in range(0, len(ids), size)] or [[]]


def _parts(kind: str, header: dict, rows: dict, ids: list, size: int) -> list[tuple[str, dict]]:
    out = []
    chunks = _chunks(ids, size)
    for n, ch in enumerate(chunks, 1):
        stem = kind if len(chunks) == 1 else f"{kind}-{n}"
        sheet = {"sheet": kind, **header}
        if len(chunks) > 1:
            sheet["part"] = f"{n} of {len(chunks)}"
        sheet["items"] = {i: rows[i] for i in ch}
        out.append((stem, sheet))
    return out


def _technique_text(t, vocabs, by) -> dict:
    rt = vocab_terms(vocabs, "runtime")
    return {"name": t.data["name"], "year": t.data.get("year"), "runtime": [rt.get(r, {}).get("label", r) for r in t.data.get("runtime") or []],
            "summary": _plain(t.data.get("summary")), "mechanism": _plain(t.data.get("mechanism"))}


def _build_coding(decision):
    def f(ctx, ents, vocabs, cfg, sc, ids):
        sh = coding.sheets(ctx, ents, vocabs, sc)[decision]
        sh = {"sheet": decision, **{k: v for k, v in sh.items() if k != "decision"}}
        sh["instructions"] = sh["instructions"].replace(coding.NO_PEEKING, BLIND)
        keep = set(ids)
        sh["items"] = {i: row for i, row in sh["items"].items() if i in keep}
        if decision == "effect":   # the technique and mechanic texts of the edges kept
            sh["techniques"] = {t: v for t, v in sh["techniques"].items() if any(i.split("/")[0] == t for i in keep)}
            sh["mechanics"] = {m: v for m, v in sh["mechanics"].items() if any(i.split("/")[1] == m for i in keep)}
        return [(decision, sh)]
    return f


def _build_state(ctx, ents, vocabs, cfg, sc, ids):
    """The rules of report/state-class.yaml word for word (its procedure, each class's definition, and its worked
    examples' reasons) and each mechanic's own text; never a sampled mechanic's class."""
    by = _by_id(ents)
    sf = state_file()
    header = {"sample": cfg["state"]["id"],
              "instructions": ("Assign each mechanic one class with the procedure below and the class definitions; the worked examples "
                               "show the procedure applied. Write the class id in code and, in rationale, the counted variable that decided "
                               "the class and why it belongs there. " + BLIND),
              "procedure": _plain(sf.get("procedure")),
              "classes": {c["id"]: {"label": c["label"], "definition": _plain(c["definition"]),
                                    "examples": [{"mechanic": by[x["mechanic"]].data["name"] if x["mechanic"] in by else x["mechanic"], "why": _plain(x["why"])}
                                                 for x in c.get("examples") or []]}
                          for c in sf.get("classes") or []}}
    rows = {m: {"name": by[m].data["name"], "summary": _plain(by[m].data["summary"]), "definition": _plain(by[m].data["definition"]),
                "design_levers": by[m].data.get("design_levers") or [], "code": None, "rationale": None} for m in ids}
    return _parts("state", header, rows, _order(cfg["seed"], ids), (cfg.get("chunk") or {}).get("state"))


def _check_state(d, value, vocabs, ents):
    ok = {c["id"] for c in state_file().get("classes") or []}
    return None if isinstance(value, str) and value in ok else f"{value!r} is not a class of report/state-class.yaml ({', '.join(sorted(ok))})"


def _read_state(item, row, vocabs, ents):
    value = row.get("code")
    if value is None:
        return [], [f"{item}: not coded"]
    bad = _check_state("state", value, vocabs, ents) or _rationale(row.get("rationale"))
    if bad:
        return [], [f"{item}: {bad}"]
    return [{"decision": "state", "item": item, "value": value, "rationale": _plain(row.get("rationale"))}], []


def _state_labels(vocabs):
    return {"state": {c["id"]: c["label"] for c in state_file().get("classes") or []}}


RECALL_RULE = ("A technique changes a mechanic when its result, as described, changes what the mechanic can be in a "
               "simulation game. Every recorded change carries exactly one of the seven effects below, so a technique "
               "changes a mechanic exactly when one of them applies: it swaps how the mechanic computes its state, makes a "
               "new form of it possible, explains its state or causes to the player, gives it more fidelity, scale, or "
               "variety at runtime, runs it at lower compute, or, at design time, makes the content it consumes or sets "
               "and tests its parameters. List a technique only when its own description supports that change to this "
               "mechanic, not because it could touch any system. One entry per technique, carrying its primary effect.")


def _build_recall(ctx, ents, vocabs, cfg, sc, ids):
    by = _by_id(ents)
    techs = _live(ents, "technique")
    ref_name = "recall-techniques"
    ref = {"sheet": ref_name, "reference": True,
           "instructions": ("Reference file for the recall sheet: every technique in the dataset, by id, with its own description. "
                            "Nothing here is filled in. " + BLIND),
           "techniques": {t.id: _technique_text(t, vocabs, by) for t in techs}}
    header = {"sample": cfg["recall"]["id"],
              "instructions": ("For each mechanic below, list every technique in the reference file named in techniques_file that "
                               "changes it, under the rule below. For each, give the technique id, one effect id chosen by the coding rule, and a "
                               "rationale saying what changes. Write changed_by: [] when no technique changes the mechanic. In the "
                               "item's rationale, say in a sentence how you searched the reference file and why the list is complete. "
                               + BLIND),
              "rule": RECALL_RULE,
              "coding_rule": coding._rendered(coding.effect_rule(), ctx),
              "effects": _terms(vocabs, "effect"),
              "techniques_file": ref_name,   # build_files puts the file's name here
              "technique_ids": [t.id for t in techs]}
    rows = {m: {"name": by[m].data["name"], "summary": _plain(by[m].data["summary"]), "definition": _plain(by[m].data["definition"]),
                "changed_by": None, "rationale": None} for m in ids}
    return [(ref_name, ref)] + _parts("recall", header, rows, _order(cfg["seed"], ids), (cfg.get("chunk") or {}).get("recall"))


def _source_line(s) -> str:
    """A cited source as title (first author, venue, date, kind): what a rater without the web can read from a citation."""
    d = s.data
    au = d.get("authors") or []
    who = (au[0] + (" et al." if len(au) > 1 else "")) if au else ""
    bits = [str(b) for b in (who, d.get("venue"), d.get("date"), d.get("kind")) if b]
    return f"{_plain(d.get('name'))} ({'; '.join(bits)})"


def _build_maturity(ctx, ents, vocabs, cfg, sc, ids):
    by = _by_id(ents)
    cats = vocab_terms(vocabs, "technique_category")
    header = {"sample": cfg["maturity"]["id"],
              "as_of": str(cfg["maturity"].get("drawn")),
              "instructions": ("For each technique, judge its use in simulation games specifically, not in AI or software generally, "
                               "as of the as_of date: its maturity (one id from maturity), its TRL (one anchor level from trl), and its "
                               "horizon (one id from horizon). Use the technique's own text: its key results, claims, limitations, "
                               "sources, and the catalog games recorded as deploying it (deployed_in; an empty list means no catalog game "
                               "is recorded, not that none exists). Between two TRL anchors, take the lower. For each of the three, the "
                               "rationale names the definition or anchor that matched, the evidence, and for TRL why the neighbouring "
                               "anchors did not. " + BLIND),
              "rule": maturity_rule(ctx),
              "maturity": _terms(vocabs, "technique_maturity"),
              "trl": _anchors(vocabs, ["trl"])["trl"],
              "horizon": {"question": vocabs["horizon"]["description"], "terms": _terms(vocabs, "horizon")}}
    games = {g.id: g for g in _live(ents, "game")}
    rows = {}
    for t in ids:
        d = by[t].data
        row = {"name": d["name"], "year": d.get("year"), "category": cats.get(d.get("category"), {}).get("label", d.get("category")),
               **{k: v for k, v in _technique_text(by[t], vocabs, by).items() if k not in ("name", "year")},
               "key_results": [_plain(k.get("text")) for k in d.get("key_results") or []],
               "claims": [_plain(c.get("text")) for c in d.get("claims") or []],
               "limitations": [_plain(x) for x in d.get("limitations") or []],
               "deployed_in": [f"{games[g].data['name']} ({games[g].data.get('year')})" for g in d.get("deployed_in") or [] if g in games],
               "sources": [_source_line(by[s]) for s in d.get("sources") or [] if s in by],
               "maturity": None, "trl": None, "horizon": None, "rationale": {"maturity": None, "trl": None, "horizon": None}}
        if not row["claims"]:
            del row["claims"]
        rows[t] = row
    return _parts("maturity", header, rows, _order(cfg["seed"], ids), (cfg.get("chunk") or {}).get("maturity"))


def _build_rubric(ctx, ents, vocabs, cfg, sc, ids):
    import calibrate
    by = _by_id(ents)
    cal = read_yaml_text(calibrate.sheet())
    cal_sheet = {"sheet": "calibration", **cal,
                 "instructions": ("Calibration, before the rubric sheet: score each mechanic on each scale by matching the anchor text; "
                                  "between two anchors take the lower. These mechanics are a fixed reference set every rater scores, "
                                  "so your scores here are compared with the set's. Fill every null under scores with an anchor level. "
                                  + BLIND)}
    header = {"sample": cfg["rubric"]["id"],
              "instructions": ("Score each mechanic on each of the six scales by matching the anchor text below; between two anchors take "
                               "the lower. Score from the mechanic's own text and your knowledge of the games it appears in. For each "
                               "scale, the rationale names the anchor text that matched and why the neighbouring anchors did not. "
                               + BLIND),
              "anchors": _anchors(vocabs, MECH_SCALES)}
    rows = {}
    for m in ids:
        d = by[m].data
        rows[m] = {"name": d["name"], "summary": _plain(d["summary"]), "definition": _plain(d["definition"]),
                   "player_experience": _plain(d.get("player_experience")), "design_levers": d.get("design_levers") or [],
                   "failure_modes": [_plain(x) for x in d.get("failure_modes") or []], "dynamics": [_plain(x) for x in d.get("dynamics") or []],
                   "scores": {s: None for s in MECH_SCALES}, "rationale": {s: None for s in MECH_SCALES}}
    return [("calibration", cal_sheet)] + _parts("rubric", header, rows, _order(cfg["seed"], ids), (cfg.get("chunk") or {}).get("rubric"))


OPP_RULES = ("Feasibility asks whether a small team could ship the opportunity within two years with techniques at their current "
             "maturity in games; judge that maturity from the techniques' descriptions and your reading of them on the maturity "
             "sheet. An open problem holds feasibility below 4 when the opportunity's own validation experiment cannot succeed "
             "without solving it. Novelty asks how far the idea is from shipped practice: the precedents are catalog games recorded "
             "as partly demonstrating it, and anything else you know of counts; say so in the rationale. Impact asks what changes if "
             "it works, for players or the market.")


def _build_opportunity(ctx, ents, vocabs, cfg, sc, ids):
    by = _by_id(ents)
    types = vocab_terms(vocabs, "opportunity_type")
    header = {"sample": cfg["opportunity"]["id"],
              "instructions": ("Score each opportunity on novelty, feasibility, and impact by matching the anchor text; between two anchors "
                               "take the lower. Use the rules below. For each score, the rationale names the anchor that matched and why "
                               "the neighbouring anchors did not. " + BLIND),
              "rules": OPP_RULES,
              "anchors": _anchors(vocabs, OPP_SCALES)}
    rows = {}
    for o in ids:
        d = by[o].data
        sig = d.get("falsifiable_signal") or {}
        rows[o] = {"name": d["name"], "type": f"{types.get(d.get('opportunity_type'), {}).get('label', '')}: {types.get(d.get('opportunity_type'), {}).get('definition', '')}",
                   "summary": _plain(d.get("summary")), "thesis": _plain(d.get("thesis")), "design_sketch": _plain(d.get("design_sketch")),
                   "involves": [m for m in d.get("involves") or []], "applies": [t for t in d.get("applies") or []],
                   "precedent": [f"{by[g].data['name']} ({by[g].data.get('year')})" for g in d.get("precedent") or [] if g in by],
                   "key_risks": [_plain(x) for x in d.get("key_risks") or []], "validation_experiment": _plain(d.get("validation_experiment")),
                   "prediction": _plain(sig.get("prediction")), "resolve_by": str(sig.get("resolve_by") or ""), "criteria": _plain(sig.get("criteria")),
                   "scores": {s: None for s in OPP_SCALES}, "rationale": {s: None for s in OPP_SCALES}}
        if d.get("claims"):
            rows[o]["claims"] = [_plain(c.get("text")) for c in d["claims"]]
    parts = _parts("opportunity", header, rows, _order(cfg["seed"], ids), (cfg.get("chunk") or {}).get("opportunity"))
    for _, sh in parts:   # each part carries the texts of the mechanics and techniques its opportunities name, nothing more
        ms = sorted({m for r in sh["items"].values() for m in r["involves"] if m in by})
        ts = sorted({t for r in sh["items"].values() for t in r["applies"] if t in by})
        items = sh.pop("items")
        sh["mechanics"] = {m: {"name": by[m].data["name"], "summary": _plain(by[m].data["summary"])} for m in ms}
        sh["techniques"] = {t: {"name": by[t].data["name"], "summary": _plain(by[t].data["summary"])} for t in ts}
        sh["items"] = items
    return parts


def read_yaml_text(text: str):
    import yaml
    return yaml.safe_load(text)


# -------- reading filled rows

def _rationale(v) -> str | None:
    s = _plain(v)
    if len(s) < 10:
        return "needs a rationale of at least 10 characters"
    if len(s) > 600:
        return "rationale is longer than 600 characters (a record's rating allows 600)"
    if PLACEHOLDER.search(s):
        return "rationale holds a placeholder word"
    return None


def _term(vocabs, name, v) -> str | None:
    return None if isinstance(v, str) and v in vocab_terms(vocabs, name) else f"{v!r} is not a term of vocab/{name}.yaml"


def _anchor(vocabs, scale, v) -> str | None:
    levels = vocabs["rubrics"]["scales"][scale]["levels"]
    ok = isinstance(v, int) and not isinstance(v, bool) and (v in levels or str(v) in levels)
    return None if ok else f"{v!r} is not an anchor level of {scale} ({', '.join(str(k) for k in levels)})"


def _read_coding(decision):
    def f(item, row, vocabs, ents):
        value = {t: row.get(t) for t in coding.TESTS} if decision == "admission" else row.get("code")
        if value is None or (decision == "admission" and None in value.values()):
            return [], [f"{item}: not coded"]
        bad = coding._check_value(decision, value, vocabs) or _rationale(row.get("rationale"))
        if bad:
            return [], [f"{item}: {bad}"]
        return [{"decision": decision, "item": item, "value": value, "rationale": _plain(row.get("rationale"))}], []
    return f


def _read_recall(item, row, vocabs, ents):
    v = row.get("changed_by")
    if v is None:
        return [], [f"{item}: changed_by is null; write a list, or [] when no technique changes it"]
    if not isinstance(v, list):
        return [], [f"{item}: changed_by must be a list of {{technique, effect, rationale}}, or []"]
    live_t = {t.id for t in _live(ents, "technique")}
    edges, probs, seen = [], [], set()
    for k, e in enumerate(v):
        if not isinstance(e, dict) or set(e) - {"technique", "effect", "rationale"}:
            probs.append(f"{item}: changed_by[{k}] must have exactly technique, effect, rationale")
            continue
        t = e.get("technique")
        bad = (None if t in live_t else f"technique {t!r} is not in the reference file") or _term(vocabs, "effect", e.get("effect")) or _rationale(e.get("rationale"))
        if not bad and t in seen:
            bad = f"technique {t!r} listed twice; one entry per technique"
        if bad:
            probs.append(f"{item}: changed_by[{k}] {bad}")
            continue
        seen.add(t)
        edges.append({"technique": t, "effect": e["effect"], "rationale": _plain(e["rationale"])})
    bad = _rationale(row.get("rationale"))
    if bad:
        probs.append(f"{item}: {bad}")
    if probs:
        return [], probs
    return [{"decision": "recall", "item": item, "value": sorted(edges, key=lambda e: e["technique"]), "rationale": _plain(row["rationale"])}], []


def _rat(row, field):
    r = row.get("rationale")
    return r.get(field) if isinstance(r, dict) else None


def _read_maturity(item, row, vocabs, ents):
    out, probs = [], []
    for fld, check, cls in (("maturity", lambda v: _term(vocabs, "technique_maturity", v), "code"),
                            ("trl", lambda v: _anchor(vocabs, "trl", v), "rating"),
                            ("horizon", lambda v: _term(vocabs, "horizon", v), "code")):
        v = row.get(fld)
        bad = ("is null" if v is None else check(v)) or _rationale(_rat(row, fld))
        if bad:
            probs.append(f"{item}: {fld} {bad}")
            continue
        key = "decision" if cls == "code" else "field"
        out.append({key: fld, "item": item, "value": v, "rationale": _plain(_rat(row, fld))})
    return ([], probs) if probs else (out, [])


def _read_scores(scales):
    def f(item, row, vocabs, ents):
        sc = row.get("scores") if isinstance(row.get("scores"), dict) else {}
        out, probs = [], []
        for s in scales:
            v = sc.get(s)
            bad = ("is null" if v is None else _anchor(vocabs, s, v)) or _rationale(_rat(row, s))
            if bad:
                probs.append(f"{item}: {s} {bad}")
                continue
            out.append({"field": s, "item": item, "value": v, "rationale": _plain(_rat(row, s))})
        return ([], probs) if probs else (out, [])
    return f


def _check_coding(d, value, vocabs, ents):
    return coding._check_value(d, value, vocabs)


def _check_recall(d, value, vocabs, ents):
    _, bad = _read_recall("item", {"changed_by": value, "rationale": "checked with the code, not here"}, vocabs, ents)
    return bad[0].split(": ", 1)[1] if bad else None


def _check_maturity(d, value, vocabs, ents):
    return _term(vocabs, "technique_maturity" if d == "maturity" else "horizon", value)


def _vocab_labels(pairs):
    def f(vocabs):
        return {d: {k: t["label"] for k, t in vocab_terms(vocabs, v).items()} for d, v in pairs}
    return f


KINDS: dict[str, Kind] = {k.name: k for k in (
    Kind("admission", ("admission",), (), lambda cfg, sc: sc["sample"]["id"], _first_coding("admission"), _owners_coding("admission"), _build_coding("admission"),
         _read_coding("admission"), _check_coding, lambda vocabs: {"admission": {"admit": "admitted", "reject": "left as a proposal"}}, True),
    Kind("family", ("family",), (), lambda cfg, sc: sc["sample"]["id"], _first_coding("family"), _owners_coding("family"), _build_coding("family"),
         _read_coding("family"), _check_coding, _vocab_labels((("family", "mechanic_family"),)), True),
    Kind("state", ("state",), (), lambda cfg, sc: cfg["state"]["id"], _first_state, _owners_state, _build_state, _read_state, _check_state,
         _state_labels, True),
    Kind("recall", ("recall",), (), lambda cfg, sc: cfg["recall"]["id"], _first_recall, _owners_recall, _build_recall, _read_recall, _check_recall),
    Kind("effect", ("effect",), (), lambda cfg, sc: sc["sample"]["id"], _first_coding("effect"), _owners_coding("effect"), _build_coding("effect"),
         _read_coding("effect"), _check_coding, _vocab_labels((("effect", "effect"),)), True),
    Kind("maturity", ("maturity", "horizon"), ("trl",), lambda cfg, sc: cfg["maturity"]["id"], _first_maturity, _owners_record, _build_maturity,
         _read_maturity, _check_maturity, _vocab_labels((("maturity", "technique_maturity"), ("horizon", "horizon")))),
    Kind("rubric", (), MECH_SCALES, lambda cfg, sc: cfg["rubric"]["id"], _first_rated("rubric", MECH_SCALES), _owners_record, _build_rubric, _read_scores(MECH_SCALES)),
    Kind("opportunity", (), OPP_SCALES, lambda cfg, sc: cfg["opportunity"]["id"], _first_rated("opportunity", OPP_SCALES), _owners_record, _build_opportunity, _read_scores(OPP_SCALES)),
)}


def code_labels(vocabs) -> dict[str, dict[str, str]]:
    """Every nominal code decision's categories, in order, with their labels (recall, a list of edges, has none)."""
    out = {}
    for k in KINDS.values():
        if k.labels:
            out.update(k.labels(vocabs))
    return out
DECISION_KIND = {d: k.name for k in KINDS.values() for d in k.codes}
FIELD_KIND = {f: k.name for k in KINDS.values() for f in k.ratings}
CODING_KINDS = tuple(coding.DECISIONS)   # recorded independently in coding.py's own file


def first_values(ents, vocabs, cfg: dict | None = None, sc: dict | None = None) -> dict[str, dict]:
    """{decision or field: {item: the dataset's code or the original score}} over every kind's sample."""
    cfg = config() if cfg is None else cfg
    sc = _sc() if sc is None else sc
    out = {}
    for k in KINDS.values():
        out.update(k.first(ents, vocabs, cfg, sc))
    return out


def kind_items(ents, vocabs, kind: str, cfg: dict | None = None, sc: dict | None = None) -> list[str]:
    cfg = config() if cfg is None else cfg
    sc = _sc() if sc is None else sc
    k = KINDS[kind]
    f = k.first(ents, vocabs, cfg, sc)
    return sorted(next(iter(f.values())).keys())


def barred_items(ents, vocabs, run, mode: str, cfg=None, sc=None) -> dict[str, list[str]]:
    """Per kind, the sampled items `run` may not code under `mode`: some run that made or re-read the item fails admits()."""
    runs = {r.id: r for r in ents.get("run", [])}
    out = {}
    for name, k in KINDS.items():
        out[name] = [i for i in kind_items(ents, vocabs, name, cfg, sc) if not all(admits(mode, run, runs.get(o)) for o in k.owners(ents, i))]
    return out


def calibration_barred(ents, run, mode: str) -> bool:
    """Whether `run` may not take the calibration: the set's frozen scores are its mechanics' original scores."""
    runs = {r.id: r for r in ents.get("run", [])}
    by = _by_id(ents)
    _, gold = _first_calibration(ents)
    made = {((by[m].data.get("provenance") or {}).get("created")) for m in gold if m in by}
    return any(not admits(mode, run, runs.get(o)) for o in sorted(made))


# ---------------------------------------------------------------- packet

def _context():
    return coding._context()


def build_files(ctx, ents, vocabs, kinds=None, run=None, mode="independent", cfg=None, sc=None) -> tuple[list[tuple[str, str, dict]], list[str]]:
    """Every sheet file in fill order as (file name, kind, sheet), and notes on what was left out."""
    cfg = config() if cfg is None else cfg
    sc = _sc() if sc is None else sc
    kinds = list(KINDS) if kinds is None else kinds
    barred = barred_items(ents, vocabs, run, mode, cfg, sc) if run is not None else {k: [] for k in KINDS}
    notes, files = [], []
    n = 0
    for name in KINDS:
        if name not in kinds:
            continue
        ids = [i for i in kind_items(ents, vocabs, name, cfg, sc) if i not in set(barred[name])]
        if barred[name]:
            shown = ", ".join(barred[name][:8]) + (f", and {len(barred[name]) - 8} more" if len(barred[name]) > 8 else "")
            notes.append(f"{name}: left out {len(barred[name])} item(s) run '{run.id}' may not code ({mode}): {shown}")
        if not ids:
            notes.append(f"{name}: no item left to code; the sheet is not written")
            continue
        n += 1
        parts = KINDS[name].build(ctx, ents, vocabs, cfg, sc, ids)
        if name == "rubric" and run is not None and calibration_barred(ents, run, mode):
            parts = [p for p in parts if p[0] != "calibration"]
            notes.append(f"rubric: the calibration set is left out; run '{run.id}' is not {mode} of its mechanics' creators")
        names = {stem: f"{n:02d}-{stem}.yaml" for stem, _ in parts}
        for stem, sh in parts:
            if sh.get("techniques_file") in names:
                sh["techniques_file"] = names[sh["techniques_file"]]
            files.append((names[stem], name, sh))
    return files, notes


def _fill_rows(sh: dict) -> dict | None:
    """The rows a coder fills in a sheet (the calibration sheet keeps calibrate.py's `mechanics`), or None for a reference file."""
    return sh.get("mechanics") if sh["sheet"] == "calibration" else sh.get("items")


def instructions_md(files, mode: str, run_id: str | None) -> str:
    rows = "\n".join(f"| `{f}` | {sh['sheet']}{' (' + sh['part'] + ')' if sh.get('part') else ''} | "
                     f"{'reference, nothing to fill' if _fill_rows(sh) is None else str(len(_fill_rows(sh))) + ' items'} |" for f, _, sh in files)
    return f"""# Instructions for a blind coder

You are coding and rating parts of a research dataset on simulation game design a second time. Each judgment you are asked
for was made once, by one rater, from written rules; your answers measure how far a second reading of the same rules
agrees. There are no right answers to find, only the rules and each item's own text.

{BLIND}

Work only from this directory. Every rule, anchor, and definition you need is inside the sheets. Where a judgment needs
knowledge of games or research beyond an item's text, use what you already know and say so in the rationale; do not
look anything up.

## The files, in the order to fill them

| File | Sheet | What to fill |
|---|---|---|
{rows}

Fill them in this order. A later sheet can show something an earlier one asks for: the family sheet lists only admitted
mechanics, the effect sheet shows recorded technique-mechanic links that the recall sheet asks you to find, and the
opportunity sheet pairs mechanics with techniques. Score the calibration file before the rubric sheet. Fill each sheet
once and keep what you wrote.

## How to fill a sheet

Each sheet is YAML. Its top part gives the instructions and rules; its `items` hold the things to judge, each with its
own text and one or more `null` fields. Replace every `null` under every item, and change nothing else: not the ids, not
the text, not the order. The files must still parse as YAML when you finish.

- Write every rationale as one double-quoted string on one line, for example `rationale: "Rule 2 decides: it owns the stock of goods."`.
  Inside it, write a double quote as `\\"`. Keep each rationale between 10 and 600 characters.
- Ids (families, effects, maturity levels, horizons, techniques) are written exactly as the sheet lists them, without quotes.
- Scores are whole numbers that are anchor levels of their scale. Between two anchors, take the lower.

What each sheet asks for:

- **admission**: each of `nameable`, `atomic`, `tunable`, `removable` as `pass` or `fail`, and `rationale` naming the test that decided it.
- **family**, **state**, **effect**: `code` (one id from the sheet's list) and `rationale` (the rule, clause, or counted variable that decided it).
- **recall**: `changed_by` as a list, one entry per technique that changes the mechanic, and `rationale` for the item:

  ```yaml
      changed_by:
      - technique: some-technique-id
        effect: deepens
        rationale: "What changes in this mechanic, and why this effect comes first."
      rationale: "Read every technique in the reference file; two change this mechanic."
  ```

  Write `changed_by: []` when no technique changes it, and say why in `rationale`.
- **maturity**: `maturity`, `trl`, and `horizon`, and under `rationale` one string for each of the three.
- **calibration**: every `null` under `scores` (no rationale).
- **rubric**, **opportunity**: every `null` under `scores`, and under `rationale` one string per scale.

## When you finish

Check that every file still parses as YAML and that no `null` is left under any item (the reference file has none to
fill). Return the directory with the filled files under their own names. A recorder checks every answer against the
sheet's vocabulary and anchors and refuses the whole packet if a file does not parse, an item is missing, or a value
is not on the sheet's list, so fix exactly what it names and change nothing else.

{f"Packet for run {run_id}." if run_id else "Packet written without a run: every sampled item is included."}
"""


def write_packet(out: Path, files, notes, mode: str, run_id: str | None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"packet": "simgrammar-panel", "mode": mode, "run": run_id, "notes": notes, "files": []}
    for f, kind, sh in files:
        text = dump_yaml(sh)
        (out / f).write_text(text, encoding="utf-8")
        rows = _fill_rows(sh)
        manifest["files"].append({"file": f, "kind": kind, "sheet": sh["sheet"], "sample": sh.get("sample") or sh.get("set"),
                                  "fill": rows is not None, "items": sorted(rows or {}), "bytes": len(text.encode())})
    (out / "manifest.yaml").write_text("# Written by `python scripts/panel.py packet`; the recorder reads it. Do not edit.\n" + dump_yaml(manifest), encoding="utf-8")
    (out / "INSTRUCTIONS.md").write_text(instructions_md(files, mode, run_id), encoding="utf-8")


# ---------------------------------------------------------------- recording

def read_packet(path: Path, ents, vocabs, kinds=None) -> tuple[dict, list[str]]:
    """The filled sheets in a packet directory: {"codes": [...], "ratings": [...], "calibration": {mech: {scale: v}} or None,
    "kinds": [kinds read], "items": {kind: [items]}}, and every problem found. Every file the manifest lists for the
    kinds read must be there, complete, and hold exactly its items."""
    man = read_yaml(path / "manifest.yaml") if (path / "manifest.yaml").exists() else None
    if not man:
        return {}, [f"{path}: no manifest.yaml; record a directory written by `python scripts/panel.py packet`"]
    import yaml
    out = {"codes": [], "ratings": [], "calibration": None, "kinds": [], "items": {}}
    probs = []
    for f in man.get("files") or []:
        if not f.get("fill") or (kinds and f["kind"] not in kinds):
            continue
        p = path / f["file"]
        if not p.exists():
            probs.append(f"{f['file']}: missing")
            continue
        try:
            sh = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            probs.append(f"{f['file']}: does not parse as YAML: {str(e).splitlines()[0]} ({getattr(e, 'problem_mark', '')})")
            continue
        if sh.get("sheet") != f["sheet"]:
            probs.append(f"{f['file']}: sheet is {sh.get('sheet')!r}, expected {f['sheet']!r}")
            continue
        if f["kind"] not in out["kinds"]:
            out["kinds"].append(f["kind"])
        if f["sheet"] == "calibration":
            rows = sh.get("mechanics") or {}
            if sorted(rows) != f["items"]:
                probs.append(f"{f['file']}: the mechanics differ from the sheet's")
                continue
            scores = {}
            for m, row in sorted(rows.items()):
                sc = (row or {}).get("scores") or {}
                for s in CALIBRATION_SCALES:
                    bad = "is null" if sc.get(s) is None else _anchor(vocabs, s, sc.get(s))
                    if bad:
                        probs.append(f"{f['file']}: {m}: {s} {bad}")
                scores[m] = {s: sc.get(s) for s in CALIBRATION_SCALES}
            out["calibration"] = {"set": sh.get("set"), "scores": scores}
            continue
        rows = sh.get("items") or {}
        if sorted(rows) != f["items"]:
            gone, extra = sorted(set(f["items"]) - set(rows)), sorted(set(rows) - set(f["items"]))
            probs.append(f"{f['file']}: items differ from the sheet's (missing {gone[:5]}, unexpected {extra[:5]})")
            continue
        out["items"].setdefault(f["kind"], []).extend(sorted(rows))
        for item, row in sorted(rows.items()):
            ans, bad = KINDS[f["kind"]].read(item, row or {}, vocabs, ents)
            probs += [f"{f['file']}: {b}" for b in bad]
            for a in ans:
                out["codes" if "decision" in a else "ratings"].append(a)
    return out, probs


def _sort_codes(codes):
    order = list(DECISION_KIND)
    return sorted(codes, key=lambda c: (order.index(c["decision"]), c["item"]))


def _sort_ratings(rs):
    order = list(FIELD_KIND)
    return sorted(rs, key=lambda r: (order.index(r["field"]), r["item"]))


def check_cross_model(path: Path, data: dict, ents, vocabs, cfg=None, sc=None) -> dict:
    """One cross-model file, checked. Returns a rater: {"run", "operator", "model", "codes": {decision: {item: value}},
    "ratings": {field: {item: value}}, "calibration": {mech: {scale: v}} or None}; raises ValueError."""
    cfg = config() if cfg is None else cfg
    sc = _sc() if sc is None else sc
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    runs = {r.id: r for r in ents.get("run", [])}
    rid = str(data.get("run") or "")
    run = runs.get(rid)
    if path.stem != rid:
        raise ValueError(f"{rel}: the file is named after its run, so it must be {rid}.yaml")
    if run is None:
        raise ValueError(f"{rel}: run '{rid}' is not in log/runs/")
    if run.data.get("kind") != CROSS_KIND:
        raise ValueError(f"{rel}: run '{rid}' is a {run.data.get('kind')} run; a cross-model run is a `{CROSS_KIND}` run, since it verifies and rates nothing")
    if run.data.get("actor") != "agent" or not _model(run):
        raise ValueError(f"{rel}: run '{rid}' is not an agent run with a model; a cross-model check compares models")
    if str(data.get("operator", "")).strip().lower() != str(run.data.get("operator", "")).strip().lower():
        raise ValueError(f"{rel}: operator '{data.get('operator')}' is not the operator of run '{rid}'")
    if normalize_model(data.get("model")) != _model(run):
        raise ValueError(f"{rel}: model '{data.get('model')}' is not the model of run '{rid}'")
    samples = data.get("samples") or {}
    for k in KINDS:
        if k in samples and samples[k] != KINDS[k].sample_id(cfg, sc):
            raise ValueError(f"{rel}: sample '{samples[k]}' for {k} is not the recorded sample '{KINDS[k].sample_id(cfg, sc)}'")
    first = first_values(ents, vocabs, cfg, sc)
    owners_cache: dict[tuple[str, str], list] = {}
    rater = {"run": rid, "operator": run.data.get("operator"), "model": _model(run), "model_id": (run.data.get("agent") or {}).get("model"),
             "codes": {}, "ratings": {}, "calibration": None}

    def owned(kind, item):
        if (kind, item) not in owners_cache:
            owners_cache[(kind, item)] = KINDS[kind].owners(ents, item)
        for o in owners_cache[(kind, item)]:
            if not admits("cross-model", run, runs.get(o)):
                raise ValueError(f"{rel}: run '{rid}' codes {kind} item '{item}', which run '{o}' made or re-read with the same model; "
                                 "a cross-model coder uses a different model from every run that made or reviewed what it codes")

    for i, c in enumerate(data.get("codes") or []):
        d, item = c.get("decision"), c.get("item")
        if d not in DECISION_KIND or DECISION_KIND[d] not in samples:
            raise ValueError(f"{rel}: codes[{i}] decision {d!r} is not a panel decision with a recorded sample")
        if item not in first[d]:
            raise ValueError(f"{rel}: codes[{i}] item '{item}' is not in the {d} sample")
        if item in rater["codes"].setdefault(d, {}):
            raise ValueError(f"{rel}: codes[{i}] codes {d} of '{item}' a second time")
        bad = KINDS[DECISION_KIND[d]].check(d, c.get("value"), vocabs, ents) or _rationale(c.get("rationale"))
        if bad:
            raise ValueError(f"{rel}: codes[{i}] ({d}, {item}) {bad}")
        owned(DECISION_KIND[d], item)
        rater["codes"][d][item] = c["value"]
    for i, r in enumerate(data.get("ratings") or []):
        fld, item = r.get("field"), r.get("item")
        if fld not in FIELD_KIND or FIELD_KIND[fld] not in samples:
            raise ValueError(f"{rel}: ratings[{i}] field {fld!r} is not a panel rating with a recorded sample")
        if item not in first[fld]:
            raise ValueError(f"{rel}: ratings[{i}] item '{item}' is not in the {fld} sample")
        if item in rater["ratings"].setdefault(fld, {}):
            raise ValueError(f"{rel}: ratings[{i}] rates {fld} of '{item}' a second time")
        bad = _anchor(vocabs, fld, r.get("value")) or _rationale(r.get("rationale"))
        if bad:
            raise ValueError(f"{rel}: ratings[{i}] ({fld}, {item}) {bad}")
        owned(FIELD_KIND[fld], item)
        rater["ratings"][fld][item] = r["value"]
    cal = data.get("calibration")
    if cal:
        sets = load_calibration_sets()
        gold = (sets.get(str(cal.get("set"))) or {}).get("mechanics")
        if gold is None:
            raise ValueError(f"{rel}: calibration names set '{cal.get('set')}', which is not in calibration/")
        scs = cal.get("scores") or {}
        if sorted(scs) != sorted(gold) or any(_anchor(vocabs, s, (scs[m] or {}).get(s)) for m in scs for s in CALIBRATION_SCALES):
            raise ValueError(f"{rel}: calibration must score every mechanic of set '{cal.get('set')}' on all six scales with anchor levels")
        if calibration_barred(ents, run, "cross-model"):
            raise ValueError(f"{rel}: run '{rid}' shares a model with the runs that made the calibration set's scores")
        rater["calibration"] = {"set": cal["set"], "scores": scs}
    if not any(rater["codes"].values()) and not any(rater["ratings"].values()) and not rater["calibration"]:
        raise ValueError(f"{rel}: no codes, ratings, or calibration")
    return rater


def load_cross_model(ents, vocabs, cfg=None, sc=None) -> list[dict]:
    """Every file in report/cross-model/, checked, in run order. One model, one cross-model file."""
    out, seen = [], {}
    for p in sorted(CROSS_DIR.glob("*.yaml")) if CROSS_DIR.exists() else []:
        r = check_cross_model(p, read_yaml(p) or {}, ents, vocabs, cfg, sc)
        if r["model"] in seen:
            raise ValueError(f"{p.relative_to(ROOT)}: runs {seen[r['model']]} and {r['run']} use the same model; one model, one cross-model run")
        seen[r["model"]] = r["run"]
        out.append(r)
    return out


def check_panel_coding(path: Path, data: dict, ents, vocabs, cfg=None, sc=None) -> dict:
    """One independent codes file in report/coding/<kind>/, checked as coding.check_coding checks its own: a verification
    run, its operator, the recorded sample, every value on the sheet's list, and independence (E035) from every run that
    made or re-read a coded item. Returns {"run", "operator", "model", "codes": {decision: {item: value}}}."""
    cfg = config() if cfg is None else cfg
    sc = _sc() if sc is None else sc
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    kind = path.parent.name
    if kind not in KINDS or not KINDS[kind].codes or kind in CODING_KINDS:
        raise ValueError(f"{rel}: report/coding/{kind}/ is not a panel kind with codes ({', '.join(k for k in KINDS if KINDS[k].codes and k not in CODING_KINDS)})")
    runs = {r.id: r for r in ents.get("run", [])}
    rid = str(data.get("run") or "")
    run = runs.get(rid)
    if path.stem != rid:
        raise ValueError(f"{rel}: the file is named after its run, so it must be {rid}.yaml")
    if run is None:
        raise ValueError(f"{rel}: run '{rid}' is not in log/runs/")
    if run.data.get("kind") != "verification":
        raise ValueError(f"{rel}: run '{rid}' is a {run.data.get('kind')} run; independent codes come from a verification run (a cross-model run records in report/cross-model/)")
    if str(data.get("operator", "")).strip().lower() != str(run.data.get("operator", "")).strip().lower():
        raise ValueError(f"{rel}: operator '{data.get('operator')}' is not the operator of run '{rid}'")
    if data.get("sample") != KINDS[kind].sample_id(cfg, sc):
        raise ValueError(f"{rel}: sample '{data.get('sample')}' is not the recorded sample '{KINDS[kind].sample_id(cfg, sc)}'")
    first = KINDS[kind].first(ents, vocabs, cfg, sc)
    codes: dict[str, dict] = {d: {} for d in KINDS[kind].codes}
    for i, c in enumerate(data.get("codes") or []):
        d, item = c.get("decision"), c.get("item")
        if d not in codes:
            raise ValueError(f"{rel}: codes[{i}] decision {d!r} is not one of {', '.join(codes)}")
        if item not in first[d]:
            raise ValueError(f"{rel}: codes[{i}] item '{item}' is not in the {d} sample")
        if item in codes[d]:
            raise ValueError(f"{rel}: codes[{i}] codes {d} of '{item}' a second time; one coder, one code")
        bad = KINDS[kind].check(d, c.get("value"), vocabs, ents) or _rationale(c.get("rationale"))
        if bad:
            raise ValueError(f"{rel}: codes[{i}] ({d}, {item}) {bad}")
        for o in KINDS[kind].owners(ents, item):
            if not admits("independent", run, runs.get(o)):
                raise ValueError(f"{rel}: run '{rid}' codes {d} of '{item}' but is not independent of run '{o}', which made or re-read it (E035, as for ratings)")
        codes[d][item] = c["value"]
    ratings: dict[str, dict] = {}
    for i, r in enumerate(data.get("ratings") or []):   # only scores a record's ratings cannot hold (record_ratable)
        fld, item = r.get("field"), r.get("item")
        if fld not in KINDS[kind].ratings or record_ratable(vocabs, fld):
            raise ValueError(f"{rel}: ratings[{i}] field {fld!r} belongs in the records' ratings, not in a codes file")
        if item not in first[fld]:
            raise ValueError(f"{rel}: ratings[{i}] item '{item}' is not in the {fld} sample")
        if item in ratings.setdefault(fld, {}):
            raise ValueError(f"{rel}: ratings[{i}] rates {fld} of '{item}' a second time; one rater, one rating")
        bad = _anchor(vocabs, fld, r.get("value")) or _rationale(r.get("rationale"))
        if bad:
            raise ValueError(f"{rel}: ratings[{i}] ({fld}, {item}) {bad}")
        for o in KINDS[kind].owners(ents, item):
            if not admits("independent", run, runs.get(o)):
                raise ValueError(f"{rel}: run '{rid}' rates {fld} of '{item}' but is not independent of run '{o}', which made or re-read it (E035)")
        ratings[fld][item] = r["value"]
    if not any(codes.values()) and not any(ratings.values()):
        raise ValueError(f"{rel}: no codes")
    return {"run": rid, "operator": run.data.get("operator"), "model": _model(run), "model_id": (run.data.get("agent") or {}).get("model") or "",
            "codes": codes, "ratings": ratings}


def load_panel_codings(ents, vocabs, cfg=None, sc=None) -> list[dict]:
    """Every independent codes file under report/coding/<kind>/, checked, merged per run: [{"run", "operator", "model",
    "codes": {decision: {item: value}}}]. One coder codes once (per kind, one file per operator and model)."""
    per_run: dict[str, dict] = {}
    for kdir in sorted(p for p in CODING_DIR.iterdir() if p.is_dir()) if CODING_DIR.exists() else []:
        seen = {}
        for p in sorted(kdir.glob("*.yaml")):
            c = check_panel_coding(p, read_yaml(p) or {}, ents, vocabs, cfg, sc)
            who = (str(c["operator"]).strip().lower(), c["model"])
            if who in seen:
                raise ValueError(f"{p.relative_to(ROOT)}: runs {seen[who]} and {c['run']} share an operator and model; one coder, one set of codes")
            seen[who] = c["run"]
            r = per_run.setdefault(c["run"], {"run": c["run"], "operator": c["operator"], "model": c["model"], "model_id": c["model_id"], "codes": {}, "ratings": {}})
            r["codes"].update(c["codes"])
            r["ratings"].update(c["ratings"])
    return [per_run[k] for k in sorted(per_run)]


def record_cross_model(read: dict, run, ents, vocabs, dry: bool) -> Path:
    cfg, sc = config(), _sc()
    data = {"run": run.id, "operator": run.data.get("operator"), "model": (run.data.get("agent") or {}).get("model"),
            "samples": {k: KINDS[k].sample_id(cfg, sc) for k in KINDS if k in read["kinds"]},
            "codes": _sort_codes(read["codes"]), "ratings": _sort_ratings(read["ratings"])}
    if read["calibration"]:
        data["calibration"] = read["calibration"]
    out = CROSS_DIR / f"{run.id}.yaml"
    if out.exists():
        raise SystemExit(f"{out.relative_to(ROOT)} exists; one run, one cross-model file")
    try:
        check_cross_model(out, data, ents, vocabs, cfg, sc)
        load_cross_model(ents, vocabs, cfg, sc)   # the files already there, so a second run on one model is refused now
    except ValueError as e:
        raise SystemExit(str(e))
    if any(normalize_model((read_yaml(p) or {}).get("model")) == _model(run) for p in sorted(CROSS_DIR.glob("*.yaml")) if CROSS_DIR.exists()):
        raise SystemExit(f"report/cross-model/ already holds a run on model '{(run.data.get('agent') or {}).get('model')}'; one model, one cross-model run")
    if not dry:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("# Codes and ratings from one blind coder in a cross-model check, written by `python scripts/panel.py record "
                       "--cross-model`.\n# Its run shares the records' operator, so it is a check across models, not independent "
                       "agreement (CONTRACT.md I14, E035). Never edited after merge.\n" + dump_yaml(data), encoding="utf-8")
    return out


# -------- independent: codes to report/coding/, ratings into records, calibration into the run file

def _insert_ratings(text: str, entries: list[dict]) -> str:
    """The record text with `entries` added to its `ratings` block, each after the last rating of its field (a block is
    added at the end when there is none)."""
    lines = text.splitlines(keepends=True)
    if not text.endswith("\n"):
        lines[-1] += "\n"
    try:
        start = lines.index("ratings:\n")
    except ValueError:
        return "".join(lines) + "ratings:\n" + "".join(dump_yaml([e]) for e in entries)
    end = start + 1
    while end < len(lines) and (lines[end].startswith((" ", "-")) or not lines[end].strip()):
        end += 1
    block = lines[start + 1:end]
    heads = [i for i, ln in enumerate(block) if ln.startswith("- ")]
    chunks = [block[a:b] for a, b in zip(heads, heads[1:] + [len(block)])]
    for e in entries:
        same = [k for k, ch in enumerate(chunks) if ch[0].rstrip("\n") == f"- field: {e['field']}"]
        chunks.insert((same[-1] + 1) if same else len(chunks), dump_yaml([e]).splitlines(keepends=True))
    return "".join(lines[:start + 1] + [ln for ch in chunks for ln in ch] + lines[end:])


def _set_scalar(text: str, field: str, value: int) -> str:
    new, n = re.subn(rf"(?m)^{re.escape(field)}: \S+$", f"{field}: {value}", text)
    if n != 1:
        raise SystemExit(f"cannot find the top-level line `{field}:` once in the record")
    return new


def _add_reviewed(text: str, rid: str) -> str:
    m = re.search(r"(?m)^provenance:\n((?:[ \t]+.*\n?)*)", text)
    if not m:
        raise SystemExit("the record has no provenance block")
    block = m.group(1)
    if re.search(rf"(?m)^  - {re.escape(rid)}$", block):
        return text
    if re.search(r"(?m)^  reviewed:", block):
        lines = block.splitlines(keepends=True)
        i = next(k for k, ln in enumerate(lines) if ln.startswith("  reviewed:"))
        j = i + 1
        while j < len(lines) and lines[j].startswith("  - "):
            j += 1
        if lines[j - 1] and not lines[j - 1].endswith("\n"):
            lines[j - 1] += "\n"
        lines.insert(j, f"  - {rid}\n")
        new_block = "".join(lines)
    else:
        new_block = block if block.endswith("\n") or not block else block + "\n"
        new_block += f"  reviewed:\n  - {rid}\n"
    return text[:m.start(1)] + new_block + text[m.end(1):]


def write_ratings(rec, rid: str, ratings: list[dict], dry: bool) -> str:
    """Add one run's ratings to a record, as tasks/rate-scores.md does by hand: the creator's original score first, when
    the field has no rating from the creating run yet; then the new rating; the stored value set to the lower median of
    all; the run appended to provenance.reviewed. Returns the new text, after checking it parses to exactly that."""
    import copy
    text = rec.path.read_text(encoding="utf-8")
    want = copy.deepcopy(rec.data)
    created = (rec.data.get("provenance") or {}).get("created")
    entries = []
    for r in ratings:
        fld = r["field"]
        have = [x for x in want.get("ratings") or [] if x.get("field") == fld]
        if not any(x.get("run") == created for x in have):
            orig = {"field": fld, "value": rec.data.get(fld), "run": created, "rationale": "original score"}
            entries.append(orig)
            have.append(orig)
        new = {"field": fld, "value": r["value"], "run": rid, "rationale": r["rationale"]}
        entries.append(new)
        have.append(new)
        med = lower_median([x["value"] for x in have])
        want.setdefault("ratings", [])
        want[fld] = med
    for e in entries:
        want["ratings"].append(e)
    text = _insert_ratings(text, entries)
    for fld in {r["field"] for r in ratings}:
        text = _set_scalar(text, fld, want[fld])
    text = _add_reviewed(text, rid)
    want.setdefault("provenance", {}).setdefault("reviewed", [])
    if rid not in want["provenance"]["reviewed"]:
        want["provenance"]["reviewed"].append(rid)
    got = read_yaml_text(text)
    key = lambda rs: sorted((x["field"], x["run"], x["value"], x["rationale"]) for x in rs or [])  # noqa: E731
    if key(got.get("ratings")) != key(want.get("ratings")) or {k: v for k, v in got.items() if k != "ratings"} != {k: v for k, v in want.items() if k != "ratings"}:
        raise SystemExit(f"{rec.path.relative_to(ROOT)}: writing the ratings would change the record beyond them; nothing written")
    if not dry:
        rec.path.write_text(text, encoding="utf-8")
    return text


def record_independent(read: dict, run, ents, vocabs, dry: bool) -> list[str]:
    """Check everything an independent run recorded, then write it: nothing is written when any part fails."""
    cfg, sc = config(), _sc()
    runs = {r.id: r for r in ents.get("run", [])}
    by = _by_id(ents)
    reg = load_registry()
    writes: list[tuple[Path, str]] = []
    done = []
    if run.data.get("kind") != "verification":
        raise SystemExit(f"run '{run.id}' is a {run.data.get('kind')} run; an independent coder or rater opens a verification run "
                         "(a cross-model run records with --cross-model)")
    # 1. admission, family, effect: coding.py's own file and checks
    cc = [c for c in read["codes"] if c["decision"] in CODING_KINDS]
    if cc:
        data = {"run": run.id, "operator": run.data.get("operator"), "sample": sc["sample"]["id"],
                "codes": sorted(cc, key=lambda c: (coding.DECISIONS.index(c["decision"]), c["item"]))}
        out = CODING_DIR / f"{run.id}.yaml"
        if out.exists():
            raise SystemExit(f"{out.relative_to(ROOT)} exists; one coder, one set of codes")
        try:
            coding.check_coding(out, data, ents, vocabs, sc, coding.sample_items(ents, sc))
        except ValueError as e:
            raise SystemExit(str(e))
        writes.append((out, "# Codes from one second coder, written by `python scripts/panel.py record`. Never edited after merge.\n" + dump_yaml(data)))
        done.append(f"{len(cc)} codes to {out.relative_to(ROOT)}")
    # 2. the other kinds' codes, and the scores a record's ratings cannot hold: report/coding/<kind>/<run-id>.yaml
    held = [r for r in read["ratings"] if not record_ratable(vocabs, r["field"])]
    read = {**read, "ratings": [r for r in read["ratings"] if record_ratable(vocabs, r["field"])]}
    for name, k in KINDS.items():
        kc = [c for c in read["codes"] if c["decision"] in k.codes and name not in CODING_KINDS]
        kr = [r for r in held if r["field"] in k.ratings]
        if not kc and not kr:
            continue
        data = {"run": run.id, "operator": run.data.get("operator"), "sample": k.sample_id(cfg, sc), "codes": _sort_codes(kc)}
        if kr:
            data["ratings"] = _sort_ratings(kr)
            done.append(f"{len(kr)} {', '.join(sorted({r['field'] for r in kr}))} ratings kept in the codes file: a record's ratings hold values up to 5 (schema/common.schema.json)")
        out = CODING_DIR / name / f"{run.id}.yaml"
        if out.exists():
            raise SystemExit(f"{out.relative_to(ROOT)} exists; one coder, one set of codes")
        try:
            check_panel_coding(out, data, ents, vocabs, cfg, sc)
        except ValueError as e:
            raise SystemExit(str(e))
        writes.append((out, f"# {name.capitalize()} codes from one second coder, written by `python scripts/panel.py record`. Never edited after merge.\n" + dump_yaml(data)))
        done.append(f"{len(kc)} codes to {out.relative_to(ROOT)}")
    # 3. the calibration, into the run file as calibrate.py score --write-run puts it, before any mechanic rating (E036)
    cal = load_calibration(reg) or {}
    thr = (reg.get("contribution") or {}).get("calibration_min_within_one", 0.8)
    scores = (run.data.get("calibration") or {}).get("scores")
    if read["calibration"] and run.data.get("calibration"):
        done.append(f"calibration not written: {run.path.relative_to(ROOT)} already has one, and a run records one calibration; the gate uses it")
    elif read["calibration"]:
        scores = read["calibration"]["scores"]
        block = {"calibration": {"set": cal.get("id"), "scores": {m: scores[m] for m in sorted(cal.get("mechanics") or {})}}}
        writes.append((run.path, run.path.read_text(encoding="utf-8").rstrip("\n") + "\n" + dump_yaml(block)))
    ag = calibration_agreement(cal.get("mechanics") or {}, scores or {}) if scores else {"within_one": None}
    cal_ok = ag["within_one"] is not None and ag["within_one"] >= thr
    if scores:
        done.append(f"calibration within-one {ag['within_one']} ({'passes' if cal_ok else f'below {thr}'})" + (f", to {run.path.relative_to(ROOT)}" if read["calibration"] and not run.data.get("calibration") else ""))
    # 4. ratings into the records, each checked for independence (E035) and written only if its text change is exact
    per_rec: dict[str, list] = {}
    for r in read["ratings"]:
        per_rec.setdefault(r["item"], []).append(r)
    skipped, n_rec = 0, 0
    for item, rs in sorted(per_rec.items()):
        rec = by[item]
        if rec.type == "mechanic" and not cal_ok:
            skipped += len(rs)
            continue
        for o in record_runs(rec):
            if not admits("independent", run, runs.get(o)):
                raise SystemExit(f"run '{run.id}' rates '{item}' but is not independent of run '{o}', which made or re-read it (E035)")
        writes.append((rec.path, write_ratings(rec, run.id, rs, dry=True)))
        n_rec += 1
    done.append(f"{len(read['ratings']) - skipped} ratings into {n_rec} records" + (" (a PR over 10 records needs the maintainer's `bulk` label, E039)" if n_rec > 10 else ""))
    if skipped:
        done.append(f"{skipped} mechanic ratings not written: no passing calibration (E036); recalibrate in a new run")
    if not dry:
        for p, text in writes:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
    return done


def record(path: Path, rid: str, mode: str, kinds, dry: bool) -> int:
    reg, vocabs = load_registry(), load_vocabs()
    ents, _ = load_entities(reg)
    run = next((r for r in ents.get("run", []) if r.id == rid), None)
    if run is None:
        raise SystemExit(f"run '{rid}' is not in log/runs/; open it first: python scripts/new.py run <slug> --kind "
                         f"{CROSS_KIND if mode == 'cross-model' else 'verification'} ...")
    read, probs = read_packet(path, ents, vocabs, kinds)
    if not probs:
        barred = barred_items(ents, vocabs, run, mode)
        hit = sorted({(DECISION_KIND.get(a.get("decision")) or FIELD_KIND.get(a.get("field")), a["item"]) for a in read["codes"] + read["ratings"]})
        for kind, item in hit:
            if item in barred[kind]:
                probs.append(f"{kind}: run '{rid}' may not code '{item}' ({mode}); write the packet with --run {rid}{' --cross-model' if mode == 'cross-model' else ''}")
        if read["calibration"] and calibration_barred(ents, run, mode):
            probs.append(f"calibration: run '{rid}' may not take it ({mode})")
    if probs:
        raise SystemExit("\n".join(probs[:40]) + (f"\n... and {len(probs) - 40} more" if len(probs) > 40 else "") +
                         f"\n{len(probs)} problem(s); nothing recorded. Fix exactly these and record again.")
    if mode == "cross-model":
        out = record_cross_model(read, run, ents, vocabs, dry)
        print(f"{'checked' if dry else 'wrote'} {len(read['codes'])} codes, {len(read['ratings'])} ratings"
              f"{', and the calibration' if read['calibration'] else ''} {'for' if dry else 'to'} {out.relative_to(ROOT)}")
    else:
        for line in record_independent(read, run, ents, vocabs, dry):
            print(("checked " if dry else "wrote ") + line)
    return 0


# ---------------------------------------------------------------- command line

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    dp = sub.add_parser("draw")
    dp.add_argument("--check", action="store_true", help="compare a fresh draw with the samples recorded in report/analysis.yaml")
    pp = sub.add_parser("packet")
    pp.add_argument("--out", type=Path, default=ROOT / "panel-out")
    sp = sub.add_parser("sheet")
    sp.add_argument("kind", choices=list(KINDS))
    rp = sub.add_parser("record")
    rp.add_argument("path", type=Path)
    rp.add_argument("--dry-run", action="store_true", help="check everything and write nothing")
    for p in (pp, rp):
        p.add_argument("--run", required=p is rp, help="the coder's run" + (": leave out the items it may not code" if p is pp else ""))
        p.add_argument("--cross-model", action="store_true", help="a cross-model run (report/cross-model/), not an independent one")
        p.add_argument("--kinds", help="comma-separated sheet kinds (default: all)")
    args = ap.parse_args()
    if args.cmd == "draw":
        reg, vocabs = load_registry(), load_vocabs()
        ents, _ = load_entities(reg)
        cfg = config()
        new = draw(ents, vocabs, cfg, _sc())
        if not args.check:
            sys.stdout.write(dump_yaml(new))
            return
        bad = False
        for k in SAMPLE_KEY:
            rec, now = sorted(sample_ids(cfg, k)), new[k]
            gone, added = sorted(set(rec) - set(now)), sorted(set(now) - set(rec))
            bad |= bool(gone or added)
            print(f"{k}: {len(rec)} recorded, {len(now)} drawn now" + (f"; recorded only {gone}; drawn only {added}" if gone or added else ", same"))
        sys.exit(1 if bad else 0)
    kinds = [k.strip() for k in args.kinds.split(",")] if getattr(args, "kinds", None) else None
    if kinds and set(kinds) - set(KINDS):
        raise SystemExit(f"unknown kinds {sorted(set(kinds) - set(KINDS))}; known: {', '.join(KINDS)}")
    mode = "cross-model" if getattr(args, "cross_model", False) else "independent"
    if args.cmd == "record":
        sys.exit(record(args.path, args.run, mode, kinds, args.dry_run))
    ctx, ents, vocabs = _context()
    run = None
    if getattr(args, "run", None):
        run = next((r for r in ents.get("run", []) if r.id == args.run), None)
        if run is None:
            raise SystemExit(f"run '{args.run}' is not in log/runs/; open it first")
        if mode == "cross-model" and (run.data.get("kind") != CROSS_KIND or not _model(run)):
            raise SystemExit(f"run '{args.run}' must be an agent run of kind `{CROSS_KIND}` with a model for a cross-model packet")
        if mode == "independent" and run.data.get("kind") != "verification":
            raise SystemExit(f"run '{args.run}' must be a verification run for an independent packet (or pass --cross-model)")
    files, notes = build_files(ctx, ents, vocabs, [args.kind] if args.cmd == "sheet" else kinds, run, mode)
    if args.cmd == "sheet":
        for f, _, sh in files:
            sys.stdout.write(f"# --- {f}\n" + dump_yaml(sh))
        return
    for n in notes:
        print(n, file=sys.stderr)
    if not any(_fill_rows(sh) for _, _, sh in files):
        raise SystemExit(f"run '{run.id if run else ''}' may code none of the sampled items ({mode}); nothing written. A cross-model run "
                         "needs a model no run that made the records used; an independent run, an operator and model of its own (E035).")
    write_packet(args.out, files, notes, mode, run.id if run else None)
    print(f"wrote {len(files)} sheet files, INSTRUCTIONS.md and manifest.yaml to {args.out}")


if __name__ == "__main__":
    main()
