"""Checks for the visual vocabulary and the Frame lines that use it (ADR-0006), called by scripts/validate.py.

E040 frame-line   every **Frame.** line in media scripts parses, sits under a Picture line in its scene, names ids that
                  resolve (icons in media/visual/vocab.yaml, live games and mechanics, families, rubric fields), finds its
                  at="..." phrase in the scene's narration, and states no number that the record it cites lacks.
E041 visual-icon  every vocab.yaml entry has a valid icon file in the SVG subset and every icon file has an entry; ids are
                  unique and of a known kind; dataset-kind ids exist; no id, label, or alias is a game's id, name, or alias.
W108 visual-coverage  mechanics, families, subgenres, and technique categories with no icon yet (warning until phase 4).
E042 frame-icon   every element a Frame line draws, once resolved against the build as the renderer resolves it (a game's
                  parts, a tally's vocab terms, a subject's subgenre), has an icon; templates.js draws one without as a
                  blank tile. Run by scripts/build.py through frame_icons(), since it needs the built entities and stats.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import frames as FR
from . import raster

ROOT = Path(__file__).resolve().parents[2]
VISUAL = ROOT / "media" / "visual"
SCRIPT_DIRS = ("media/episodes", "media/shorts", "media/mega", "media/intro")
KINDS = ("mechanic", "family", "subgenre", "technique", "technique-category", "noun", "term")
SCENE = re.compile(r"^## (\d+)\. (.+?)(?: \((.+?)\))?\s*$|^## (\d+:\d\d) to (\d+:\d\d)\. (.+?)\s*$")
TOKEN = re.compile(r"\{\{[^}]*\}\}")
CITE = re.compile(r"\s?\[@src-[^\]]+\]")
LINK = re.compile(r"\[\[[a-z0-9-]+\|([^\]]+)\]\]|\[\[([a-z0-9-]+)\]\]")


def plain(s: str) -> str:
    s = TOKEN.sub("", s)
    s = CITE.sub("", s)
    s = LINK.sub(lambda m: m.group(1) or m.group(2).replace("-", " "), s)
    return re.sub(r"\s+", " ", s.replace("**", "").replace("*", "")).strip()


def scenes(path: Path) -> list[dict]:
    """Scenes of a source script: [{n, line, blocks: [(kind, text, line)]}]; stops at the film's Film wording section."""
    out, cur = [], None
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("## ") and not SCENE.match(line):
            cur = None
            continue
        if SCENE.match(line):
            cur = {"n": len(out) + 1, "line": no, "blocks": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        for kind, lab in (("picture", "**Picture.**"), ("voice", "**Voice.**"), ("onscreen", "**On screen.**"), ("frame", FR.LABEL)):
            if line.startswith(lab):
                cur["blocks"].append((kind, line[len(lab):].strip(), no))
    return out


def record_text(game: dict | None, mechanic: dict | None, gid: str, mid: str) -> str:
    """The text a Frame may draw numbers from: the game's note on its use of the mechanic, and the mechanic's own text."""
    parts = []
    if game:
        parts += [u.get("note") or "" for u in game.get("mechanics", []) if u.get("id") == mid]
        parts.append(game.get("design_notes") or "")
    if mechanic:
        for k in ("definition", "summary"):
            parts.append(str(mechanic.get(k) or ""))
        parts += [str(x) for x in mechanic.get("failure_modes") or []]
    return " ".join(parts)


def check(F, ents: dict, vocabs: dict) -> None:
    import yaml

    vpath = VISUAL / "vocab.yaml"
    if not vpath.exists():
        return
    voc = yaml.safe_load(vpath.read_text(encoding="utf-8")) or {}
    games = {e.id: e.data for e in ents.get("game", []) if not e.data.get("deprecated")}
    mechs = {e.id: e.data for e in ents.get("mechanic", []) if not e.data.get("deprecated")}
    runs = {e.id for e in ents.get("run", [])}
    dataset_ids = {e.id for lst in ents.values() for e in lst}
    terms = {name: {str(t["id"]) for t in v.get("terms", [])} for name, v in vocabs.items() if name != "rubrics"}
    game_names = set()
    for g in games.values():
        game_names.add(g["id"].lower())
        game_names.add(str(g.get("name", "")).lower())
        game_names.update(str(a).lower() for a in g.get("aliases") or [])
    icons = {}

    # ---- E041: the icon set
    if voc.get("run") and voc["run"] not in runs:
        F.add("E041", vpath, f"run '{voc['run']}' is not in log/runs/")
    for e in voc.get("icons") or []:
        i = str(e.get("id", ""))
        if i in icons:
            F.add("E041", vpath, f"icon '{i}' is listed twice")
            continue
        icons[i] = e
        kind = e.get("kind")
        if kind not in KINDS:
            F.add("E041", vpath, f"icon '{i}': kind '{kind}' is not one of {', '.join(KINDS)}")
        if kind == "mechanic" and i not in mechs:
            F.add("E041", vpath, f"icon '{i}': no live mechanic has this id")
        if kind == "family" and i not in terms.get("mechanic_family", set()):
            F.add("E041", vpath, f"icon '{i}': not a mechanic_family term")
        if kind == "subgenre" and i not in terms.get("subgenre", set()):
            F.add("E041", vpath, f"icon '{i}': not a subgenre term")
        if kind == "technique-category" and i not in terms.get("technique_category", set()):
            F.add("E041", vpath, f"icon '{i}': not a technique_category term")
        if kind == "technique" and i not in {x.id for x in ents.get("technique", [])}:
            F.add("E041", vpath, f"icon '{i}': no technique has this id")
        if kind in ("noun", "term"):
            if not e.get("label"):
                F.add("E041", vpath, f"icon '{i}': a {kind} needs a label")
            if i in dataset_ids:
                F.add("E041", vpath, f"icon '{i}': a {kind} id cannot reuse a dataset id")
        if e.get("run") and e["run"] not in runs:
            F.add("E041", vpath, f"icon '{i}': run '{e['run']}' is not in log/runs/")
        for name in [i, str(e.get("label") or "")] + [str(a) for a in e.get("aliases") or []]:
            if name and name.lower() in game_names:
                F.add("E041", vpath, f"icon '{i}': '{name}' names a game; icons draw generic subjects only")
        src = VISUAL / "icons" / f"{i}.svg"
        if not src.exists():
            F.add("E041", vpath, f"icon '{i}' has no file media/visual/icons/{i}.svg")
            continue
        try:
            raster.parse(src)
        except raster.IconError as err:
            F.add("E041", src, str(err))
    for p in sorted((VISUAL / "icons").glob("*")):
        if p.suffix != ".svg" or p.stem not in icons:
            F.add("E041", p, "file has no entry in media/visual/vocab.yaml" if p.suffix == ".svg" else "only .svg icon sources belong here")

    # ---- W108: coverage
    have = set(icons)
    gaps = {"mechanics": sorted(set(mechs) - have), "families": sorted(terms.get("mechanic_family", set()) - have),
            "subgenres": sorted(terms.get("subgenre", set()) - have), "technique categories": sorted(terms.get("technique_category", set()) - have)}
    missing = [f"{len(v)} {k}" for k, v in gaps.items() if v]
    if missing:
        F.add("W108", vpath, "no icon yet for " + ", ".join(missing))

    # ---- E040: Frame lines
    rubric_fields = set((vocabs.get("rubrics") or {}).get("scales", {}))
    techs = {e.id: e.data for e in ents.get("technique", []) if not e.data.get("deprecated")}
    bets = {e.id: e.data for e in ents.get("opportunity", []) if not e.data.get("deprecated")}
    sources = {e.id: e.data for e in ents.get("source", [])}
    run_data = {e.id: e.data for e in ents.get("run", [])}
    TALLY = {"technique": {"maturity", "determinism_impact", "risks", "runtime", "category"}, "opportunity": {"horizon", "opportunity_type"},
             "record": {"status"}, "link": {"effect"}}
    for d in SCRIPT_DIRS:
        for path in sorted((ROOT / d).glob("*.md")):
            for sc in scenes(path):
                voice = " ".join(plain(t) for k, t, _ in sc["blocks"] if k == "voice")
                seen_picture = False
                for kind, text, line in sc["blocks"]:
                    if kind == "picture":
                        seen_picture = True
                    if kind != "frame":
                        continue
                    if not seen_picture:
                        F.add("E040", path, f"line {line}: a Frame line must follow a Picture line in its scene")
                    try:
                        t, args = FR.parse(text)
                    except FR.FrameError as err:
                        F.add("E040", path, f"line {line}: {err}")
                        continue
                    bad = lambda msg: F.add("E040", path, f"line {line}: {msg}")
                    # elements: an icon, or a live mechanic or technique (drawn as its category icon or a type tile until it has one)
                    for ref in FR.icon_refs(t, args):
                        if ref not in icons and ref not in mechs and ref not in techs:
                            bad(f"'{ref}' has no icon in media/visual/vocab.yaml and is no live mechanic or technique")
                    for k in ("game",):
                        if k in args and args[k] not in games:
                            bad(f"no live game '{args[k]}'")
                    if "games" in args:
                        gs = [i for i, _ in FR.items(args["games"])]
                        if len(gs) != 2:
                            bad("games= names two games")
                        for g in gs:
                            if g not in games:
                                bad(f"no live game '{g}'")
                    if t == "chain" and "from" in args and args["from"] not in games:
                        bad(f"no live game '{args['from']}'")
                    if t == "timeline" and args.get("kind") == "games":
                        for i, _ in FR.items(args.get("ids", "")):
                            if i not in games:
                                bad(f"no live game '{i}'")
                    elif t in ("timeline", "scale") and "ids" in args or (t == "count" and args.get("kind") in ("bars",)):
                        for i, _ in FR.items(args.get("ids", "")):
                            if i not in mechs:
                                bad(f"no live mechanic '{i}'")
                    if "with" in args:
                        ids = [i for i, _ in FR.items(args.get("ids", ""))]
                        rows_ = args["with"].split("|")
                        if t != "count" or args.get("kind") != "bars" or len(rows_) != len(ids):
                            bad("with= goes on count kind=bars, one row of games per id")
                        for mid, r in zip(ids, rows_):
                            for g, _ in FR.items(r):
                                if g not in games:
                                    bad(f"no live game '{g}' in with=")
                                elif mid not in [u.get("id") for u in games[g].get("mechanics", [])]:
                                    bad(f"'{g}' does not use '{mid}' (with=)")
                    if "cues" in args:
                        groups = {"totals": {"game", "mechanic", "technique", "prediction"}, "icons": set(KINDS)}.get(args.get("kind"), set())
                        for g, word in FR.items(args["cues"]):
                            if g not in groups or not word:
                                bad(f"cues= pairs one of {', '.join(sorted(groups)) or 'nothing (count kind=totals or icons only)'} with a narration word, not '{g}:{word}'")
                            elif word not in voice:
                                bad(f"cue word \"{word}\" is not in this scene's narration")
                    if t == "count" and args.get("kind") == "venn":
                        for k in ("a", "b"):
                            if args[k] not in mechs:
                                bad(f"no live mechanic '{args[k]}' ({k}=)")
                    if t == "count" and args.get("kind") == "packages":
                        for r in FR.rows(args["rows"]):
                            for i, _ in r:
                                if i not in mechs:
                                    bad(f"no live mechanic '{i}' in rows=")
                    for k in ("a_ids", "b_ids"):
                        for i, _ in FR.items(args.get(k, "")):
                            if i not in techs:
                                bad(f"no live technique '{i}' ({k}=)")
                    for k in ("mechanic", "id"):
                        if k in args and args[k] not in mechs:
                            bad(f"no live mechanic '{args[k]}'")
                    if "technique" in args and args["technique"] not in techs:
                        bad(f"no live technique '{args['technique']}'")
                    for b in ([args["bet"]] if "bet" in args else []) + [i for i, _ in FR.items(args.get("bets", ""))]:
                        if b not in bets:
                            bad(f"no live bet (opportunity) '{b}'")
                    if "run" in args and args["run"] not in runs:
                        bad(f"no run '{args['run']}' in log/runs/")
                    if "family" in args and args["family"] not in terms.get("mechanic_family", set()):
                        bad(f"'{args['family']}' is not a mechanic_family term")
                    if t == "scale" and "field" in args:
                        mid, _, fld = args["field"].partition(".")
                        if mid not in mechs or fld not in rubric_fields or fld not in mechs.get(mid, {}):
                            bad(f"'{args['field']}' is not a rubric-scored field of a live mechanic")
                    if t == "scale" and "fields" in args:
                        for fld, _ in FR.items(args["fields"]):
                            if fld not in rubric_fields:
                                bad(f"'{fld}' is not a rubric scale")
                    if t == "count" and args.get("kind") == "tally" and args["field"] not in TALLY.get(args["of"], set()):
                        bad(f"tally of={args['of']} counts one of {', '.join(sorted(TALLY.get(args['of'], set())))}, not '{args['field']}'")
                    if t == "timeline" and args.get("kind") == "due" and "date" in args:
                        dues = {str((b.get("falsifiable_signal") or {}).get("resolve_by")) for b in bets.values()}
                        if args["date"] not in dues:
                            bad(f"no bet resolves on {args['date']}")
                    if t == "script" or "script" in args:
                        sp = ROOT / "media" / args["script"]
                        if not sp.exists():
                            bad(f"no script media/{args['script']}")
                        elif args.get("find", "") not in sp.read_text(encoding="utf-8"):
                            bad(f"find=\"{args.get('find')}\" is not in media/{args['script']}")
                    # numbers: each must be in the text of what `from` names
                    text_, cited = "", args.get("from", "")
                    if "from" in args and t != "chain":
                        srcs = [x for x, _ in FR.items(cited)] if t == "count" and args.get("kind") == "figures" else [cited]
                        for src in srcs:
                            gid, _, mid = src.partition(":")
                            if gid in games:
                                if mid and mid not in [u.get("id") for u in games[gid].get("mechanics", [])]:
                                    bad(f"'{gid}' does not use '{mid}' (from={src})")
                                text_ += " " + record_text(games.get(gid), mechs.get(mid), gid, mid)
                            elif gid in techs and not mid:
                                tq = techs[gid]
                                text_ += " " + " ".join(str(x) for x in [tq.get("name"), tq.get("summary"), tq.get("mechanism")] + list(tq.get("limitations") or []) + [k.get("quote", "") for k in tq.get("key_results") or []])
                            elif gid in mechs and not mid:
                                text_ += " " + record_text(None, mechs[gid], "", gid)
                            elif gid in sources and not mid:
                                sd = sources[gid]
                                text_ += " " + " ".join(str(sd.get(k) or "") for k in ("name", "date", "notes", "venue"))
                            elif gid in bets and not mid:
                                text_ += " " + str(bets[gid])
                            else:
                                bad(f"from={src} names no live game, mechanic, technique, bet, or source")
                    for n in FR.constants(t, args):
                        if not FR.has_number(n, text_):
                            bad(f"the number {n} is not in the text of what it cites (from={cited or 'nothing'})")
                    if "at" in args and args["at"] not in voice:
                        bad(f"at=\"{args['at']}\" is not in this scene's narration")


def blank_tiles(f: dict) -> list[str]:
    """What a resolved frame (scripts/video/framedata.py) would draw with no icon: templates.js ic() draws an element whose
    icon is empty, an anatomy subject that is missing, or a game side with no emblem as a blank type tile."""
    found: list[str] = []

    def walk(x):
        if isinstance(x, dict):
            if "icon" in x and not x["icon"]:
                found.append(str(x.get("id") or x.get("family") or x.get("label") or "an element"))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk({k: v for k, v in f.items() if not (f.get("t") == "moment" and k == "subject")})   # a moment strip does not draw its subject
    if f.get("t") == "anatomy" and not f.get("subject"):
        found.append(f"the subject of {f.get('name')} (its subgenre emblem)")
    for side in ("a", "b"):
        g = f.get(side)
        if isinstance(g, dict) and "emblem" in g and not g["emblem"]:
            found.append(f"the subgenre emblem of {g.get('name')}")
    return list(dict.fromkeys(found))


def frame_icons(outs: dict) -> list[str]:
    """E042: resolve every Frame line in the built scripts as the renderer does and list each element with no icon.

    outs is scripts/build.py's in-memory output (rendered scripts, entities, stats, visual/icons.json), so the check
    needs no dist/ on disk and sees exactly the data the next render will draw from.
    """
    import sys

    video = str(ROOT / "scripts" / "video")
    if video not in sys.path:
        sys.path.append(video)
    import framedata
    from parse import parse_text

    framedata.use_build(outs)
    out = []
    for key in sorted(k for k in outs if k.startswith(tuple(d + "/" for d in SCRIPT_DIRS)) and k.endswith(".md")):
        for sc in parse_text(outs[key], key)["scenes"]:
            onscreen = " ".join(b["text"] for b in sc["blocks"] if b["kind"] == "onscreen")
            for b in sc["blocks"]:
                if b["kind"] != "frame":
                    continue
                where = f"{key} scene {sc['n']}, Frame '{b['text'][:48]}{'...' if len(b['text']) > 48 else ''}'"
                try:
                    f = framedata.resolve(b["text"], onscreen, None)
                except Exception as err:  # a frame the renderer could not draw at all
                    out.append(f"{where}: does not resolve ({type(err).__name__}: {err})")
                    continue
                for what in blank_tiles(f):
                    out.append(f"{where}: draws '{what}' with no icon, as a blank tile; draw media/visual/icons/<id>.svg and list it in media/visual/vocab.yaml")
    return out
