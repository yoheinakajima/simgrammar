"""Deterministic analysis over the entity graph.

compute() returns:
  derived: {entity_id: {field: value}}      -> attached to entities as `_derived` in projections
  stats:   {name: number|string}            -> {{stat:name}} tokens
  tables:  {name: {"columns": [...], "rows": [...], "description": str}}  -> {{table:name}}
  figures: {name: {"svg": str, "caption": str}}  -> {{figure:name}}
Never stores anything back into data/. Same inputs -> byte-identical outputs.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.special import gammaln
from scipy.stats import spearmanr

from lib import CALIBRATION_SCALES, ROOT, calibration_agreement, independent, load_calibration, load_registry, read_yaml, vocab_terms

MATURITY_ORDER = ["research", "prototype", "shipped-niche", "shipped-mainstream"]
# links a contributor profile may carry (report/meta.yaml), in display order, with the hosts each must point at
PROFILE_LINKS = {"x": ("x.com", "twitter.com"), "linkedin": ("linkedin.com",), "website": (), "orcid": ("orcid.org",)}


def contributor_profiles(meta: dict) -> dict:
    """Profiles from report/meta.yaml `contributors`, keyed by lowercase GitHub handle; a bare string is a display name.
    Links must be https, and an x or linkedin link must point at its site, since contributors edit their own."""
    out = {}
    for h, p in (meta.get("contributors") or {}).items():
        p = {"name": p} if isinstance(p, str) else dict(p or {})
        extra = sorted(set(p) - {"name", *PROFILE_LINKS})
        if extra:
            raise ValueError(f"report/meta.yaml: contributors.{h} has unknown keys {extra}; allowed: name, {', '.join(PROFILE_LINKS)}")
        for k, hosts in PROFILE_LINKS.items():
            if p.get(k) is None:
                continue
            u = urlparse(str(p[k]))
            host = (u.hostname or "").lower().removeprefix("www.")
            if u.scheme != "https" or not host or (hosts and not any(host == d or host.endswith("." + d) for d in hosts)):
                raise ValueError(f"report/meta.yaml: contributors.{h}.{k} must be an https link{' to ' + ' or '.join(hosts) if hosts else ''}: {p[k]}")
        out[str(h).lower()] = p
    return out



def written_dates(iso) -> tuple[str, str]:
    """An ISO date written out for prose (31 December 2027) and for narration (December 31, 2027)."""
    d = date.fromisoformat(str(iso))
    return f"{d.day} {d:%B %Y}", f"{d:%B} {d.day}, {d.year}"

def _r(x, n=3):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), n)


def compute(ents: dict, edges: list, vocabs: dict) -> dict:
    cfg = read_yaml(ROOT / "report" / "analysis.yaml")
    rub = vocabs["rubrics"]
    live = {t: [e for e in lst if not e.data.get("deprecated")] for t, lst in ents.items() if t != "run"}
    by_id = {e.id: e for lst in live.values() for e in lst}
    games = sorted(live.get("game", []), key=lambda e: e.id)
    mechs = sorted(live.get("mechanic", []), key=lambda e: e.id)
    techs = sorted(live.get("technique", []), key=lambda e: e.id)
    opps = sorted(live.get("opportunity", []), key=lambda e: e.id)
    fam_terms = vocab_terms(vocabs, "mechanic_family")
    sub_terms = vocab_terms(vocabs, "subgenre")
    derived: dict[str, dict] = defaultdict(dict)
    stats: dict[str, object] = {}
    tables: dict[str, dict] = {}
    figures: dict[str, dict] = {}
    shared: dict[str, object] = {}  # intermediate structures handed to viz.py; never written to dist directly

    # ---------------- inverse edges (computed, never stored)
    inverse = vocab_terms(vocabs, "edge_types")
    incoming: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    outgoing: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for ed in edges:
        if ed.source not in by_id or ed.target not in by_id:
            continue
        et = inverse[ed.type]
        outgoing[ed.source][ed.type].append(ed.target)
        inv = et["inverse"]
        if et.get("symmetric"):
            outgoing[ed.target][ed.type].append(ed.source)
        else:
            incoming[ed.target][inv].append(ed.source)
    for eid in by_id:
        if incoming.get(eid):
            derived[eid]["incoming"] = {k: sorted(set(v)) for k, v in sorted(incoming[eid].items())}

    # ---------------- game x mechanic
    N = len(games)
    gm: dict[str, dict[str, str]] = {g.id: {m["id"]: m["role"] for m in g.data.get("mechanics", []) if m["id"] in by_id} for g in games}
    mech_games: dict[str, list[str]] = defaultdict(list)
    for gid, ms in gm.items():
        for mid in ms:
            mech_games[mid].append(gid)
    year = {g.id: g.data.get("year") for g in games}

    for g in games:
        ms = gm[g.id]
        fam = Counter(by_id[m].data.get("family") for m in ms)
        derived[g.id].update({
            "mechanic_count": len(ms),
            "core_count": sum(1 for r in ms.values() if r == "core"),
            "family_profile": dict(sorted(fam.items())),
        })

    for m in mechs:
        gl = sorted(mech_games.get(m.id, []), key=lambda gid: (year.get(gid) or 9999, gid))
        core = [gid for gid in gl if gm[gid][m.id] == "core"]
        derived[m.id].update({
            "prevalence": len(gl),
            "prevalence_share": _r(len(gl) / N) if N else 0,
            "core_count": len(core),
            "earliest_year": year.get(gl[0]) if gl else None,
            "earliest_game": gl[0] if gl else None,
            "subgenre_spread": len({by_id[g].data.get("subgenre") for g in gl}),
        })

    # prevalence rank: 1 = used by the most games; tied mechanics share the best rank (competition ranking)
    for m in mechs:
        p = derived[m.id]["prevalence"]
        derived[m.id]["prevalence_rank"] = 1 + sum(1 for o in mechs if derived[o.id]["prevalence"] > p)

    # ---------------- technique exposure per mechanic
    comp = rub["composites"]["technique_exposure"]
    exposure = defaultdict(float)
    tech_on_mech = defaultdict(list)
    for t in techs:
        mw = comp["maturity_weights"][t.data.get("maturity")]
        for a in t.data.get("affects", []):
            if a["id"] in by_id:
                exposure[a["id"]] += mw * comp["effect_weights"][a["effect"]]
                tech_on_mech[a["id"]].append(t.id)
        fams = Counter(by_id[a["id"]].data.get("family") for a in t.data.get("affects", []) if a["id"] in by_id)
        derived[t.id].update({
            "affects_count": len(t.data.get("affects", [])),
            "families_affected": dict(sorted(fams.items())),
        })
    for m in mechs:
        derived[m.id]["technique_exposure"] = _r(exposure.get(m.id, 0.0))
        derived[m.id]["technique_count"] = len(set(tech_on_mech.get(m.id, [])))

    # ---------------- opportunity priority
    w = rub["composites"]["opportunity_priority"]["weights"]
    for o in opps:
        d = o.data
        pr = (d["impact"] ** w["w_impact"]) * (d["feasibility"] ** w["w_feasibility"]) * (d["novelty"] ** w["w_novelty"])
        derived[o.id]["priority"] = _r(pr)

    # ---------------- stats: counts
    for t, lst in live.items():
        stats[f"n_{t}"] = len(lst)
    stats["n_edges"] = len(edges)
    stats["n_uses_edges"] = sum(len(v) for v in gm.values())
    mc = [derived[g.id]["mechanic_count"] for g in games] or [0]
    stats["mean_mechanics_per_game"] = _r(float(np.mean(mc)), 1)
    # games per time model (book chapter 1 and the report cite these)
    tm = Counter(g.data.get("time_model") for g in games)
    for term, n in tm.items():
        stats["n_games_time_model_" + str(term).replace("-", "_")] = n
    stats["top_time_model"] = max(tm.items(), key=lambda kv: (kv[1], kv[0]))[0] if tm else ""
    stats["median_mechanics_per_game"] = _r(float(np.median(mc)), 1)
    yrs = [y for y in year.values() if isinstance(y, int)]
    stats["year_min"] = min(yrs) if yrs else None
    stats["year_max"] = max(yrs) if yrs else None
    stats["n_boundary_cases"] = sum(1 for g in games if g.data.get("boundary_case"))
    stats["n_sourced_or_verified"] = sum(1 for lst in live.values() for e in lst if e.data.get("status") in ("sourced", "verified"))
    stats["n_asserted"] = sum(1 for lst in live.values() for e in lst if e.data.get("status") == "asserted")
    # per type: asserted records, and records that cite no source at all (the preface and paper say how far sourcing goes)
    for t in ("game", "mechanic", "technique", "opportunity"):
        stats[f"n_{t}_asserted"] = sum(1 for e in live.get(t, []) if e.data.get("status") == "asserted")
        stats[f"n_{t}_no_sources"] = sum(1 for e in live.get(t, []) if not outgoing.get(e.id, {}).get("cites"))
    stats["n_families"] = len({m.data.get("family") for m in mechs})
    stats["n_subgenres"] = len({g.data.get("subgenre") for g in games})
    if mechs:
        top = max(mechs, key=lambda m: (derived[m.id]["prevalence"], m.id))
        stats["most_prevalent_mechanic"] = top.data["name"]
        stats["most_prevalent_mechanic_share_pct"] = _r(100 * derived[top.id]["prevalence"] / max(N, 1), 0)
        stats["n_mechanics_single_game"] = sum(1 for m in mechs if derived[m.id]["prevalence"] == 1)
        stats["n_mechanics_unused"] = sum(1 for m in mechs if derived[m.id]["prevalence"] == 0)
        # book chapter 1: the parts a game marks as core are rarer across the catalog than the parts it marks as supporting
        core_p, sup_p, rare_core = [], [], 0
        rare_max = (cfg.get("book") or {}).get("rare_max_games", 10)
        for g in games:
            ps = {u["id"]: (u.get("role"), derived[u["id"]]["prevalence"]) for u in g.data.get("mechanics", []) if u["id"] in derived}
            core_p += [p for r, p in ps.values() if r == "core"]
            sup_p += [p for r, p in ps.values() if r != "core"]
            rare_core += any(r == "core" and p <= rare_max for r, p in ps.values())
        stats["median_prevalence_core_uses"] = _r(float(np.median(core_p)), 1) if core_p else None
        stats["median_prevalence_supporting_uses"] = _r(float(np.median(sup_p)), 1) if sup_p else None
        stats["rare_max_games"] = rare_max
        stats["n_games_with_rare_core"] = rare_core
        stats["pct_games_with_rare_core"] = _r(100 * rare_core / max(N, 1), 0)
        # book chapters 7-8: what the shipped techniques reach, how often they replace a mechanic, and who explains
        shipped = [t for t in techs if str(t.data.get("maturity", "")).startswith("shipped")]
        sh_mechs = {a["id"] for t in shipped for a in t.data.get("affects", []) if a["id"] in derived}
        stats["n_technique_shipped"] = len(shipped)
        stats["n_technique_shipped_breaks"] = sum(1 for t in shipped if t.data.get("determinism_impact") == "breaks")
        stats["n_mechanics_touched_by_shipped"] = len(sh_mechs)
        stats["pct_uses_touched_by_shipped"] = _r(100 * sum(derived[m]["prevalence"] for m in sh_mechs) / max(stats["n_uses_edges"], 1), 0)
        stats["n_replaces_substrate_shipped"] = sum(1 for t in shipped for a in t.data.get("affects", []) if a["effect"] == "replaces-substrate")
        explainers = [t for t in techs if any(a["effect"] == "explains" for a in t.data.get("affects", []))]
        stats["n_explains_techniques"] = len(explainers)
        stats["n_effect_explains_shipped"] = sum(1 for t in shipped for a in t.data.get("affects", []) if a["effect"] == "explains")
        stats["n_technique_since_2023"] = sum(1 for t in techs if isinstance(t.data.get("year"), int) and t.data["year"] >= 2023)
        # book chapter 8: per family, how many mechanics it holds and how many no technique in the set affects
        for fam in sorted({m.data.get("family") for m in mechs if m.data.get("family")}):
            fm = [m for m in mechs if m.data.get("family") == fam]
            key = str(fam).replace("-", "_")
            stats[f"n_family_mechanics_{key}"] = len(fm)
            stats[f"n_family_zero_exposure_{key}"] = sum(1 for m in fm if exposure.get(m.id, 0.0) == 0)
        # book chapter 3: how much of the vocabulary the games released by 2000 show, against random sets of the same
        # number of games trimmed to the same sizes (so a shared vocabulary is not mistaken for early invention), and how
        # much of what later games use was already there. Seeded and sorted so the build stays deterministic.
        used_by_game = {g.id: sorted({u["id"] for u in g.data.get("mechanics", []) if u["id"] in derived}) for g in games}
        early_ids = [g.id for g in games if isinstance(year.get(g.id), int) and year[g.id] <= 2000]
        early_seen = set().union(*[set(used_by_game[x]) for x in early_ids]) if early_ids else set()
        stats["n_games_by_2000"] = len(early_ids)
        stats["pct_games_by_2000"] = _r(100 * len(early_ids) / max(N, 1), 0)
        stats["n_mechanics_seen_by_2000"] = len(early_seen)
        if early_ids:
            import random as _random
            rng = _random.Random(20261026)
            sizes = [len(used_by_game[x]) for x in early_ids]
            pool = sorted(used_by_game)
            null = []
            for _ in range(2000):
                pick = rng.sample(pool, len(early_ids))
                rng.shuffle(sizes)
                seen = set()
                for gid, k in zip(pick, sizes):
                    ms = used_by_game[gid]
                    seen.update(rng.sample(ms, min(k, len(ms))))
                null.append(len(seen))
            stats["n_mechanics_seen_null_mean"] = _r(float(np.mean(null)), 0)
            stats["pct_mechanics_seen_null_mean"] = _r(100 * float(np.mean(null)) / max(len(mechs), 1), 0)
            stats["p_mechanics_seen_by_2000"] = _r(sum(1 for v in null if v >= len(early_seen)) / len(null), 2)
        # book expansion: chapters 7-9
        # how many city builders use each mechanic that splits the genre in chapter 9 (treasury against stores, goods against needs)
        city_ids = [g.id for g in games if g.data.get("subgenre") == "city-builder"]
        for mid in ("budget-treasury", "storage-capacity", "goods-consumption", "needs-decay", "crop-cultivation"):
            stats[f"n_city_builder_uses_{mid.replace('-', '_')}"] = sum(1 for x in city_ids if mid in used_by_game[x])
        stats["n_city_builders"] = len(city_ids)
        # prototypes that are world models, and whether any other prototype replaces how a mechanic works (chapter 7)
        protos = [t for t in techs if t.data.get("maturity") == "prototype"]
        stats["n_technique_prototype_world_model"] = sum(1 for t in protos if t.data.get("category") == "generative-world-model")
        stats["n_technique_prototype_other_replaces_substrate"] = sum(
            1 for t in protos if t.data.get("category") != "generative-world-model"
            and any(a.get("effect") == "replaces-substrate" for a in t.data.get("affects") or []))
        stats["n_technique_prototype_horizon_now"] = sum(1 for t in protos if t.data.get("horizon") == "now")
        # research edges into the environment family and how many come from weather models; research techniques that
        # tune the economic core (chapter 8)
        fam_of = {m.id: m.data.get("family") for m in mechs}
        research = [t for t in techs if t.data.get("maturity") == "research"]
        env_edges = [t.id for t in research for a in t.data.get("affects") or [] if fam_of.get(a["id"]) == "environment-ecology"]
        stats["n_research_edges_environment_ecology"] = len(env_edges)
        stats["n_research_edges_environment_ecology_weather"] = sum(1 for x in env_edges if x == "ml-weather-models")
        econ_core = {"resources-production", "logistics-networks", "economy-finance", "population-lineage"}
        stats["n_research_techniques_tune_economic_core"] = sum(
            1 for t in research if any(a.get("effect") == "tunes" and fam_of.get(a["id"]) in econ_core for a in t.data.get("affects") or []))
        # how the games with permadeath or hand crafting end: share that are open sandboxes or survival runs (chapter 9)
        pc = [g for g in games if {"permadeath", "hand-crafting"} & set(used_by_game[g.id])]
        stats["n_games_permadeath_or_crafting"] = len(pc)
        stats["pct_permadeath_or_crafting_open_runs"] = (
            round(100 * sum(1 for g in pc if g.data.get("win_structure") in ("open-sandbox", "survival-duration")) / len(pc)) if pc else 0)
        # book expansion: chapters 10-13
        # where techniques run (chapter 11), prediction criteria (chapter 12), and the run log (chapter 13)
        for where in ("server-realtime", "client-realtime"):
            on = [t for t in techs if where in t.data["runtime"]]
            stats[f"n_technique_{where.replace('-', '_')}"] = len(on)
            stats[f"n_technique_{where.replace('-', '_')}_breaks"] = sum(1 for t in on if t.data["determinism_impact"] == "breaks")
        stats["n_technique_offline_only"] = sum(1 for t in techs if not {"client-realtime", "server-realtime"} & set(t.data["runtime"]))
        stats["n_technique_server_only"] = sum(1 for t in techs if "server-realtime" in t.data["runtime"] and "client-realtime" not in t.data["runtime"])
        stats["n_technique_server_only_breaks"] = sum(1 for t in techs if "server-realtime" in t.data["runtime"] and "client-realtime" not in t.data["runtime"]
                                                      and t.data["determinism_impact"] == "breaks")
        crit = [str(o.data["falsifiable_signal"].get("criteria", "")) for o in opps]
        stats["n_predictions_exclusion_clause"] = sum(1 for c in crit if "not count" in c)
        stats["n_predictions_console_alternative"] = sum(1 for c in crit if "console release" in c)
        stats["n_opportunity_now_due_2029"] = sum(1 for o in opps if o.data.get("horizon") == "now" and str(o.data["falsifiable_signal"]["resolve_by"]) >= "2029-01-01")
        stats["n_opportunity_deprecated"] = sum(1 for o in ents.get("opportunity", []) if o.data.get("deprecated"))
        run_list = ents.get("run", [])
        for kind in ("catalog", "taxonomy", "maintenance", "technique", "synthesis", "bootstrap"):
            stats[f"n_runs_{kind}"] = sum(1 for r in run_list if r.data.get("kind") == kind)
        run_dates = sorted(str(r.data.get("date")) for r in run_list)
        stats["first_run_date"] = run_dates[0] if run_dates else ""
        if run_dates:
            stats["first_run_date_long"] = written_dates(run_dates[0])[0]
        stats["n_run_days"] = len(set(run_dates))
        # book expansion: chapters 1-3
        # how much of itself each game marks as core (chapter 1), influences the records name (chapter 3), mechanic
        # proposals in the run log (chapter 1), and game-level win structures and math bases of mechanics (chapter 2)
        core_per_game = [derived[g.id]["core_count"] for g in games]
        stats["median_core_per_game"] = _r(float(np.median(core_per_game)), 1) if core_per_game else None
        stats["max_core_per_game"] = max(core_per_game) if core_per_game else None
        stats["n_games_one_core"] = sum(1 for c in core_per_game if c == 1)
        stats["n_mechanics_never_core"] = sum(1 for m in mechs if derived[m.id]["prevalence"] > 0 and derived[m.id]["core_count"] == 0)
        stats["n_mechanics_always_core"] = sum(1 for m in mechs if derived[m.id]["prevalence"] >= 3 and derived[m.id]["core_count"] == derived[m.id]["prevalence"])
        named_inf = Counter()
        for g in games:
            for x in g.data.get("influenced_by") or []:
                named_inf[x if isinstance(x, str) else x.get("id")] += 1
        for g in games:
            derived[g.id]["named_as_influence"] = named_inf.get(g.id, 0)
        stats["n_influence_links"] = sum(named_inf.values())
        stats["n_games_naming_influence"] = sum(1 for g in games if g.data.get("influenced_by"))
        stats["max_named_as_influence"] = max(named_inf.values()) if named_inf else 0
        sub_of = {g.id: g.data.get("subgenre") for g in games}
        stats["n_influence_links_cross_subgenre"] = sum(1 for g in games for x in (g.data.get("influenced_by") or [])
                                                        if sub_of.get(x if isinstance(x, str) else x.get("id")) not in (None, sub_of[g.id]))
        mech_props = [p for r in ents.get("run", []) for p in (r.data.get("proposals") or []) if p.get("kind") == "new-mechanic"]
        prop_targets = {p.get("target") for p in mech_props if p.get("target")}
        stats["n_mechanic_proposals"] = len(mech_props)
        stats["n_mechanic_proposals_adopted"] = sum(1 for t in prop_targets if t in by_id and by_id[t].type == "mechanic")
        win_n = Counter(g.data.get("win_structure") for g in games)
        for w, n in win_n.items():
            stats[f"n_games_win_{str(w).replace('-', '_')}"] = n
        role_n = Counter(g.data.get("player_role") for g in games)
        stats["n_player_roles"] = len(role_n)
        for r_, n in role_n.items():
            stats[f"n_games_role_{str(r_).replace('-', '_')}"] = n
        agency_n = Counter(a for g in games for a in (g.data.get("agency_model") if isinstance(g.data.get("agency_model"), list)
                                                      else [g.data.get("agency_model")]) if a)
        for a, n in agency_n.items():
            stats[f"n_games_agency_{str(a).replace('-', '_')}"] = n
        narr_n = Counter(g.data.get("narrative_mode") for g in games)
        for nm, n in narr_n.items():
            stats[f"n_games_narrative_{str(nm).replace('-', '_')}"] = n
        math_n = Counter(b for m in mechs for b in (m.data.get("math_basis") or []))
        for b, n in math_n.items():
            stats[f"n_mechanics_math_{b.replace('-', '_')}"] = n
        # book expansion: chapters 4-6
        # chapter 4 works the clustering's similarity through by hand: rarity weights and a few pairwise scores,
        # computed with the same weights the clustering uses (core weight times log(N / prevalence))
        _clw = cfg["clustering"]
        def _w(gid, mid):
            pv = derived[mid].get("prevalence") or 0
            if not pv:
                return 0.0
            idf_ = math.log(N / pv) if _clw.get("idf") else 1.0
            return (_clw["core_weight"] if gm[gid][mid] == "core" else 1.0) * idf_
        def _sim(a, b):
            if a not in gm or b not in gm:
                return None
            ids_ = set(gm[a]) | set(gm[b])
            mn = sum(min(_w(a, m) if m in gm[a] else 0.0, _w(b, m) if m in gm[b] else 0.0) for m in ids_)
            mx = sum(max(_w(a, m) if m in gm[a] else 0.0, _w(b, m) if m in gm[b] else 0.0) for m in ids_)
            return _r(mn / mx, 2) if mx else None
        for a_, b_ in (("factorio", "satisfactory"), ("factorio", "anno-1800"), ("rimworld", "the-sims"), ("rimworld", "dwarf-fortress"), ("simcity-1989", "cities-skylines")):
            v_ = _sim(a_, b_)
            if v_ is not None:
                stats[f"sim_{a_.replace('-', '_')}_{b_.replace('-', '_')}"] = v_
        if derived.get("storyteller-director", {}).get("prevalence") and derived.get("variable-speed", {}).get("prevalence"):
            stats["idf_ratio_storyteller_pause"] = _r(math.log(N / derived["storyteller-director"]["prevalence"]) / math.log(N / derived["variable-speed"]["prevalence"]), 1)
        stats["n_mechanics_tuning_5"] = sum(1 for m in mechs if m.data.get("tuning_difficulty") == 5)
        old_mechs = {m.id for m in mechs if (derived[m.id].get("earliest_year") or 9999) <= 2000}
        late_ids =[g.id for g in games if isinstance(year.get(g.id), int) and year[g.id] >= 2010]
        late_uses = sum(len(used_by_game[x]) for x in late_ids)
        stats["n_games_since_2010"] = len(late_ids)
        stats["n_games_since_2010_only_pre2001"] = sum(1 for x in late_ids if used_by_game[x] and set(used_by_game[x]) <= old_mechs)
        stats["pct_uses_since_2010_on_pre2001"] = _r(100 * sum(1 for x in late_ids for mid in used_by_game[x] if mid in old_mechs) / max(late_uses, 1), 0)
        for dec in range(1960, 2030, 10):
            stats[f"n_mechanics_first_{dec}s"] = sum(1 for m in mechs if (derived[m.id].get("earliest_year") or 0) // 10 * 10 == dec)
        intro = Counter(derived[m.id]["earliest_game"] for m in mechs if derived[m.id].get("earliest_game"))
        for g in games:
            derived[g.id]["introduced_count"] = intro.get(g.id, 0)
        if intro:
            top_g, top_n = min(intro.items(), key=lambda kv: (-kv[1], kv[0]))
            stats["top_introducer"] = by_id[top_g].data["name"]
            stats["top_introducer_count"] = top_n
        # book chapter 3: a mechanic's career, its second catalog game and the year it reached its fifth
        career = defaultdict(list)
        for g in games:
            if isinstance(year.get(g.id), int):
                for mid in used_by_game[g.id]:
                    career[mid].append((year[g.id], g.id))
        for m in mechs:
            us = sorted(career.get(m.id, []))
            derived[m.id]["second_game"] = us[1][1] if len(us) > 1 else None
            derived[m.id]["second_year"] = us[1][0] if len(us) > 1 else None
            derived[m.id]["year_fifth_game"] = us[4][0] if len(us) > 4 else None
        for dec in range(1960, 2030, 10):
            stats[f"n_games_{dec}s"] = sum(1 for g in games if isinstance(year.get(g.id), int) and year[g.id] // 10 * 10 == dec)
        # book chapters 5-6: legibility and tuning difficulty by emergence level, and how many mechanics sit at the top of
        # the compute and authoring scales (all rubric scores are one model rater's, chapter 5 says so)
        e1 = [m for m in mechs if m.data.get("emergence_potential") == 1]
        e4 = [m for m in mechs if (m.data.get("emergence_potential") or 0) >= 4]
        mean_of = lambda ms, f: _r(float(np.mean([m.data[f] for m in ms])), 1) if ms else None  # noqa: E731
        stats["n_mechanics_emergence_1"] = len(e1)
        stats["n_mechanics_emergence_4plus"] = len(e4)
        stats["mean_legibility_emergence_1"] = mean_of(e1, "legibility")
        stats["mean_legibility_emergence_4plus"] = mean_of(e4, "legibility")
        stats["mean_tuning_emergence_1"] = mean_of(e1, "tuning_difficulty")
        stats["mean_tuning_emergence_4plus"] = mean_of(e4, "tuning_difficulty")
        stats["n_mechanics_legibility_2_or_less"] = sum(1 for m in mechs if (m.data.get("legibility") or 5) <= 2)
        stats["n_mechanics_legibility_2_or_less_emergence_3plus"] = sum(1 for m in mechs if (m.data.get("legibility") or 5) <= 2 and (m.data.get("emergence_potential") or 0) >= 3)
        stats["n_mechanics_compute_4plus"] = sum(1 for m in mechs if (m.data.get("compute_cost") or 0) >= 4)
        stats["n_mechanics_authoring_4plus"] = sum(1 for m in mechs if (m.data.get("authoring_cost") or 0) >= 4)
        a4 = [m for m in mechs if (m.data.get("authoring_cost") or 0) >= 4]
        a12 = [m for m in mechs if (m.data.get("authoring_cost") or 0) <= 2]
        stats["mean_ai_leverage_authoring_4plus"] = mean_of(a4, "ai_leverage")
        stats["mean_ai_leverage_authoring_2_or_less"] = mean_of(a12, "ai_leverage")
        fam_n = Counter(m.data.get("family") for m in mechs)
        for f, n in fam_n.items():
            stats["n_mechanics_family_" + str(f).replace("-", "_")] = n
        big = max(games, key=lambda g: (derived[g.id]["mechanic_count"], g.id)) if games else None
        stats["most_mechanics_game"] = big.data["name"] if big is not None else ""  # label; game_most_mechanics (below) is the id
        # book chapters 10-13: opportunity horizons, technique risks, prediction dates, evidence status, runs
        hz = Counter(o.data.get("horizon") for o in opps)
        for term in ("now", "1-2y", "3-5y"):
            stats["n_opportunity_horizon_" + term.replace("-", "_")] = hz.get(term, 0)
        otype = Counter(o.data.get("opportunity_type") for o in opps)
        for term in vocab_terms(vocabs, "opportunity_type"):
            stats["n_opportunity_type_" + term.replace("-", "_")] = otype.get(term, 0)
        breaking = {t.id for t in techs if t.data.get("determinism_impact") == "breaks"}
        stats["n_opportunity_applies_breaking"] = sum(1 for o in opps if set(o.data.get("applies") or []) & breaking)
        rk = Counter(r for t in techs for r in (t.data.get("risks") or []))
        for term in vocab_terms(vocabs, "risk"):
            stats["n_technique_risk_" + term.replace("-", "_")] = rk.get(term, 0)
        stats["top_technique_risk"] = max(rk.items(), key=lambda kv: (kv[1], kv[0]))[0] if rk else ""
        rb = sorted(o.data["falsifiable_signal"]["resolve_by"] for o in opps)
        stats["last_prediction_resolves"] = rb[-1] if rb else None
        if rb:
            stats["last_prediction_resolves_long"], stats["last_prediction_resolves_spoken"] = written_dates(rb[-1])
        stats["n_predictions_first_date"] = sum(1 for d in rb if d == rb[0]) if rb else 0
        stats["n_predictions_by_2027"] = sum(1 for d in rb if d <= "2027-12-31")
        stats["n_predictions_by_2028"] = sum(1 for d in rb if d <= "2028-12-31")
        st_live = Counter(e.data.get("status") for lst in live.values() for e in lst)
        stats["n_verified"] = st_live.get("verified", 0)
        stats["n_contested"] = st_live.get("contested", 0)
        all_runs = ents.get("run", [])
        stats["n_runs"] = len(all_runs)
        stats["n_runs_verification"] = sum(1 for r in all_runs if r.data.get("kind") == "verification")
        stats["n_runs_agent"] = sum(1 for r in all_runs if r.data.get("actor") == "agent")
        stats["n_run_operators"] = len({str(r.data.get("operator", "")).strip().lower() for r in all_runs})
        # which models the agent runs used (paper section 2.5 discloses that every run was an agent run)
        run_models = Counter(str((r.data.get("agent") or {}).get("model", "")).strip() for r in all_runs if r.data.get("actor") == "agent")
        stats["n_run_models"] = len(run_models)
        if run_models:
            top_model, n_top = max(run_models.items(), key=lambda kv: (kv[1], kv[0]))
            stats["top_run_model"] = top_model
            stats["n_runs_top_model"] = n_top
        # everyone who has operated a run, credited from the run log; names and links come from report/meta.yaml
        profiles = contributor_profiles(read_yaml(ROOT / "report" / "meta.yaml") or {})
        by_op: dict[str, list] = {}
        for r in all_runs:
            by_op.setdefault(str(r.data.get("operator", "")).strip().lower(), []).append(r)
        prov = [(t, e.data, e.data.get("provenance") or {}) for t, lst in live.items() for e in lst]
        crows = []
        for op, rs in by_op.items():
            ids = {r.id for r in rs}
            verif = {r.id for r in rs if r.data.get("kind") == "verification"}
            pf = profiles.get(op, {})
            crows.append({"contributor": pf.get("name") or str(rs[0].data.get("operator", "")).strip(),
                          "github": str(rs[0].data.get("operator", "")).strip(),
                          "first_run": min(str(r.data.get("date")) for r in rs), "runs": len(rs),
                          "records_created": sum(1 for t, _, p in prov if t != "source" and p.get("created") in ids),
                          "sources_added": sum(1 for t, _, p in prov if t == "source" and p.get("created") in ids),
                          "records_verified": sum(1 for t, d, p in prov if d.get("status") == "verified" and verif & set(p.get("reviewed") or [])),
                          # a rating from the creating run is the original score kept beside the others, not a second reading
                          "scores_rated": sum(1 for _, d, p in prov for g in d.get("ratings") or [] if g.get("run") in ids and g.get("run") != p.get("created")),
                          "links": [pf[k] for k in PROFILE_LINKS if pf.get(k)]})
        crows.sort(key=lambda r: (r["first_run"], r["github"].lower()))
        tables["contributors"] = {"description": "Everyone who has operated a run, from the run log (log/runs). Records are games, mechanics, techniques, "
                                                 "and opportunities; a verified record counts for the person whose verification run checked it, and a "
                                                 "rated score for the person whose run added an independent rating of it. "
                                                 "Names and links come from each contributor's profile in report/meta.yaml; anyone without one appears by GitHub handle.",
                                  "columns": ["contributor", "github", "first_run", "runs", "records_created", "sources_added", "records_verified", "scores_rated", "links"],
                                  "rows": crows}
        stats["n_opportunity_asserted"] = sum(1 for o in opps if o.data.get("status") == "asserted")
        # book chapter 2: feedback polarity of mechanics, the game with the most mechanics, and where each large
        # subgenre spends its mechanic uses (top three families by share)
        fb = Counter(m.data.get("feedback") for m in mechs)
        for k in ("balancing", "reinforcing", "both", "none"):
            stats[f"n_mechanics_feedback_{k}"] = fb.get(k, 0)
        most = max(games, key=lambda g: (derived[g.id]["mechanic_count"], g.id)) if games else None
        stats["max_mechanics_per_game"] = derived[most.id]["mechanic_count"] if most else None
        stats["game_most_mechanics"] = most.id if most else ""
        smin = (cfg.get("book") or {}).get("subgenre_min_games", 6)
        spend = []
        for sg, members in sorted(Counter(g.data.get("subgenre") for g in games).items(), key=lambda kv: (-kv[1], kv[0])):
            if members < smin:
                continue
            fc = Counter(by_id[u["id"]].data.get("family") for g in games if g.data.get("subgenre") == sg
                         for u in g.data.get("mechanics", []) if u["id"] in by_id)
            tot = sum(fc.values()) or 1
            top3 = sorted(fc.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
            key = str(sg).replace("-", "_")
            stats[f"top_family_{key}"] = top3[0][0] if top3 else ""
            stats[f"top_family_pct_{key}"] = round(100 * top3[0][1] / tot) if top3 else 0
            row = {"subgenre": sub_terms.get(sg, {}).get("label", sg), "games": members}
            for i, (f, n) in enumerate(top3, start=1):
                row[f"family_{i}"] = f"{fam_terms.get(f, {}).get('label', f)} ({round(100 * n / tot)}%)"
            spend.append(row)
        tables["subgenre-spend"] = {"description": f"For each subgenre with at least {smin} catalog games, the three mechanic families that take the largest share of its games' mechanic uses.",
                                    "columns": ["subgenre", "games", "family_1", "family_2", "family_3"], "rows": spend}

    # ---------------- correlations across mechanics (Spearman)
    def corr(a, b):
        xs = [m.data[a] for m in mechs]
        ys = [m.data[b] for m in mechs]
        if len(set(xs)) < 2 or len(set(ys)) < 2:
            return None, None
        r, p = spearmanr(xs, ys)
        return _r(r, 2), p

    for a, b in [("legibility", "emergence_potential"), ("authoring_cost", "ai_leverage"), ("legibility", "compute_cost"),
                 ("emergence_potential", "tuning_difficulty"), ("legibility", "ai_leverage")]:
        r, p = corr(a, b)
        stats[f"rho_{a}_{b}"] = r
        stats[f"p_{a}_{b}"] = ("<0.001" if p is not None and p < 0.001 else (_r(p, 3) if p is not None else None))
    # robustness: interface families (legibility, time and pacing) are scored emergence 1 by rubric design
    iface = {"information-legibility", "time-pacing"}
    sub = [m for m in mechs if m.data["family"] not in iface]
    if len(sub) > 2:
        r, _ = spearmanr([m.data["legibility"] for m in sub], [m.data["emergence_potential"] for m in sub])
        stats["rho_legibility_emergence_potential_excl_interface"] = _r(r, 2)
    im = [m for m in mechs if m.data["family"] in iface]
    stats["pct_interface_emergence_1"] = _r(100 * sum(1 for m in im if m.data["emergence_potential"] == 1) / len(im), 0) if im else None
    if mechs and techs:
        xs = [m.data["ai_leverage"] for m in mechs]
        ys = [derived[m.id]["technique_exposure"] for m in mechs]
        if len(set(ys)) > 1:
            r, _ = spearmanr(xs, ys)
            stats["rho_ai_leverage_exposure"] = _r(r, 2)

    # ---------------- co-occurrence
    mids = [m.id for m in mechs if derived[m.id]["prevalence"] > 0]
    sets = {gid: set(ms) for gid, ms in gm.items()}
    pair_count = Counter()
    for gid, s in sets.items():
        for a, b in combinations(sorted(s), 2):
            pair_count[(a, b)] += 1
    prev = {m: derived[m]["prevalence"] for m in mids}
    tension_pairs = {tuple(sorted((ed.source, ed.target))) for ed in edges if ed.type == "tension"}
    shared.update({"gm": gm, "pair_count": pair_count, "prev": prev, "tension_pairs": tension_pairs, "year": year, "games": games, "N": N})
    rows = []
    for (a, b), c in pair_count.items():
        if c < cfg["cooccurrence"]["min_support"]:
            continue
        lift = c * N / (prev[a] * prev[b])
        rows.append({"mechanic_a": a, "mechanic_b": b, "games": c, "lift": _r(lift, 2),
                     "jaccard": _r(c / (prev[a] + prev[b] - c), 3)})
    rows.sort(key=lambda r: (-r["lift"], -r["games"], r["mechanic_a"], r["mechanic_b"]))
    tables["cooccurrence-top"] = {"description": f"Mechanic pairs ranked by lift (observed / expected co-occurrence across games), support >= {cfg['cooccurrence']['min_support']} games.",
                                  "columns": ["mechanic_a", "mechanic_b", "games", "lift", "jaccard"], "rows": rows[: cfg["cooccurrence"]["top_n"]], "link_columns": ["mechanic_a", "mechanic_b"]}
    tables["cooccurrence-all"] = {"description": "All pairs meeting support.", "columns": ["mechanic_a", "mechanic_b", "games", "lift", "jaccard"], "rows": rows, "link_columns": ["mechanic_a", "mechanic_b"]}
    stats["n_cooccurring_pairs"] = len(pair_count)
    stats["n_possible_pairs"] = len(mids) * (len(mids) - 1) // 2
    stats["pair_coverage_pct"] = _r(100 * len(pair_count) / max(stats["n_possible_pairs"], 1), 1)

    # ---------------- white space: common mechanics that rarely meet
    ws = cfg["whitespace"]
    thr = ws["min_prevalence_games"]
    common = [m for m in mids if prev[m] >= thr]
    wrows = []
    for a, b in combinations(sorted(common), 2):
        if ws["exclude_same_family"] and by_id[a].data["family"] == by_id[b].data["family"]:
            continue
        if by_id[a].data["family"] in ws.get("exclude_families", []) or by_id[b].data["family"] in ws.get("exclude_families", []):
            continue
        if (a, b) in tension_pairs:
            continue
        obs = pair_count.get((a, b), 0)
        if obs > ws["max_observed"]:
            continue
        expected = prev[a] * prev[b] / N
        wrows.append({"mechanic_a": a, "mechanic_b": b, "family_a": by_id[a].data["family"], "family_b": by_id[b].data["family"],
                      "observed": obs, "expected": _r(expected, 2), "gap": _r(expected - obs, 2)})
    wrows.sort(key=lambda r: (-r["gap"], r["mechanic_a"], r["mechanic_b"]))
    shared.update({"common": common, "whitespace_all": wrows})
    tables["whitespace"] = {"description": f"Pairs of common mechanics (each in >= {ws['min_prevalence_games']} games, different families, not marked as tension{', excluding ' + ', '.join(fam_terms[f]['label'] for f in ws.get('exclude_families', [])) if ws.get('exclude_families') else ''}) that co-occur at most {ws['max_observed']} time(s). Gap = expected - observed co-occurrence under independence.",
                            "columns": ["mechanic_a", "mechanic_b", "family_a", "family_b", "observed", "expected", "gap"], "rows": wrows[: ws["top_n"]], "link_columns": ["mechanic_a", "mechanic_b"]}
    stats["n_whitespace_pairs"] = len(wrows)
    stats["n_common_mechanics"] = len(common)
    stats["whitespace_min_games"] = ws["min_prevalence_games"]

    # ---------------- clustering games by weighted mechanic sets (weighted Jaccard)
    cl = cfg["clustering"]
    st_cfg = cl["stability"]
    if N >= st_cfg["k_max"] and mids:
        idx = {m: i for i, m in enumerate(mids)}
        gidx = {g.id: i for i, g in enumerate(games)}
        X = np.zeros((N, len(mids)))
        idf = {m: (math.log(N / prev[m]) if cl.get("idf") else 1.0) for m in mids}
        for gi, g in enumerate(games):
            for mid, role in gm[g.id].items():
                if mid in idx:
                    X[gi, idx[mid]] = (cl["core_weight"] if role == "core" else 1.0) * idf[mid]
        D = np.zeros((N, N))
        for i in range(N):
            for j in range(i + 1, N):
                mn = np.minimum(X[i], X[j]).sum()
                mx = np.maximum(X[i], X[j]).sum()
                d = 1 - (mn / mx if mx else 0)
                D[i, j] = D[j, i] = d
        shared.update({"game_ids": [g.id for g in games], "game_distance": D})
        Z = linkage(squareform(D, checks=False), method="average")
        # stability: re-cluster subsamples and compare with the full solution. Each game joins subsample b when a seeded
        # hash of (b, game id) falls below `fraction`, so adding or removing one game leaves every other game's
        # memberships unchanged and does not redraw the subsamples. k is chosen by the rule stated in
        # report/analysis.yaml, never by what the clusters look like.
        B, frac, seed = int(st_cfg["subsamples"]), float(st_cfg["fraction"]), st_cfg["seed"]
        gids = [g.id for g in games]
        subs = []
        for b in range(B):
            u = np.array([int(hashlib.sha256(f"{seed}:{b}:{gid}".encode()).hexdigest()[:12], 16) / 16 ** 12 for gid in gids])
            subs.append(np.flatnonzero(u < frac))
        Zs = [linkage(squareform(D[np.ix_(sb, sb)], checks=False), method="average") for sb in subs]
        curve = []
        for kk in range(st_cfg["k_min"], st_cfg["k_max"] + 1):
            Lk = fcluster(Z, t=kk, criterion="maxclust")
            aris = [_ari_int(Lk[sb], fcluster(Zb, t=kk, criterion="maxclust")) for sb, Zb in zip(subs, Zs)]
            curve.append({"k": kk, "clusters": int(len(set(Lk.tolist()))), "mean_ari": _r(float(np.mean(aris)), 4), "_mean": float(np.mean(aris)),
                          "p10_ari": _r(float(np.percentile(aris, 10)), 4),
                          "largest_cluster_share": _r(Counter(Lk.tolist()).most_common(1)[0][1] / N, 2)})
        thr, tol = float(st_cfg["min_mean_ari"]), float(st_cfg.get("drift_tolerance", 0.0))
        passing = [r for r in curve if r["_mean"] >= thr]
        k_rule = passing[0]["k"] if passing else max(curve, key=lambda r: (r["_mean"], -r["k"]))["k"]
        k_chosen = int(cl["k"])
        mean_at = {r["k"]: r["_mean"] for r in curve}
        # drift only when the evidence is clear: the configured k has fallen well below the threshold, or a smaller k
        # now clears it by the same margin. Differences inside the margin are resampling noise, not a reason to move k.
        drift = (k_chosen in mean_at and mean_at[k_chosen] < thr - tol) or any(r["_mean"] >= thr + tol for r in curve if r["k"] < k_chosen)
        for r in curve:
            r["selection"] = ", ".join(x for x, hit in (("configured", r["k"] == k_chosen), ("rule today", r["k"] == k_rule)) if hit)
            del r["_mean"]
        tables["cluster-stability"] = {"description": f"Agreement between the full clustering and re-clusterings of {B} subsamples, each holding about {int(frac * 100)}% of games (adjusted Rand index), for each candidate k. The selection rule picks the smallest k whose mean ARI reaches {thr}; k is fixed in report/analysis.yaml from the last selection, and the validator warns (W107) only when the configured k falls more than {tol} below the threshold or a smaller k clears it by more than {tol}.",
                                       "columns": ["k", "clusters", "mean_ari", "p10_ari", "largest_cluster_share", "selection"], "rows": curve}
        stats["cluster_rule_k"] = k_rule
        stats["cluster_k_drift"] = 1 if drift else 0
        labels = fcluster(Z, t=k_chosen, criterion="maxclust")
        co = np.zeros((N, N))
        both = np.zeros((N, N))
        jac = defaultdict(list)
        for sb, Zb in zip(subs, Zs):
            lb = fcluster(Zb, t=k_chosen, criterion="maxclust")
            co[np.ix_(sb, sb)] += (lb[:, None] == lb[None, :])
            both[np.ix_(sb, sb)] += 1
            # cluster-wise Jaccard (Hennig 2007): each full cluster against its best-matching subsample cluster
            la = labels[sb]
            ct = np.zeros((int(labels.max()) + 1, int(lb.max()) + 1))
            np.add.at(ct, (la, lb), 1)
            rows_, cols_ = ct.sum(1), ct.sum(0)
            for c in range(1, ct.shape[0]):
                if rows_[c] > 0:
                    jac[c].append(float(np.max(ct[c] / (rows_[c] + cols_ - ct[c]))))
        C = np.where(both > 0, co / np.maximum(both, 1), 0.0)
        np.fill_diagonal(C, 1.0)
        cocluster = {"index": {g.id: i for i, g in enumerate(games)}, "value": lambda i, j: _r(float(C[i, j]), 3),
                     "together": st_cfg["together"], "apart": st_cfg["apart"]}
        clust_jac = {c: float(np.mean(v)) for c, v in jac.items()}
        clusters = defaultdict(list)
        for g, lab in zip(games, labels):
            clusters[int(lab)].append(g)
        crow = []
        ordered = sorted(clusters.items(), key=lambda kv: (-len(kv[1]), min(x.id for x in kv[1])))
        for ci, (lab, members) in enumerate(ordered, start=1):
            cnt = Counter(mid for g in members for mid in gm[g.id])
            scored = []
            for mid, c in cnt.items():
                share_in = c / len(members)
                share_all = prev[mid] / N
                scored.append((share_in * math.log((share_in + 1e-9) / (share_all + 1e-9) + 1), mid))
            scored.sort(key=lambda x: (-x[0], x[1]))
            topm = [mid for _, mid in scored[: cl["top_mechanics_per_cluster"]]]
            subs = Counter(g.data.get("subgenre") for g in members).most_common(2)
            label = " + ".join(by_id[m].data["name"] for m in topm[:2])
            for g in members:
                derived[g.id]["cluster"] = f"C{ci:02d}"
            crow.append({"cluster": f"C{ci:02d}", "label": label, "size": len(members),
                         "stability": _r(clust_jac.get(lab, 0.0), 2),
                         "dominant_subgenres": ", ".join(f"{sub_terms.get(s, {}).get('label', s)} ({n})" for s, n in subs),
                         "signature_mechanics": topm,
                         "members": [g.id for g in sorted(members, key=lambda g: (float(np.mean([D[gidx[g.id], gidx[o.id]] for o in members])), g.id))]})
        tables["game-clusters"] = {"description": f"Games clustered by weighted Jaccard similarity of mechanic sets (average linkage, k={k_chosen} chosen by subsample stability, core weight {cl['core_weight']}{', inverse-prevalence weighting so ubiquitous mechanics do not dominate' if cl.get('idf') else ''}). Stability is the mean Jaccard overlap between the cluster and its best match when {int(st_cfg['fraction'] * 100)}% subsamples are re-clustered (at least {st_cfg['stable_cluster']} counts as stable). Signature mechanics maximize within-cluster share x log-lift. Members are ordered by centrality (mean distance to the rest of the cluster), so the first members are the most typical.",
                                   "columns": ["cluster", "label", "size", "stability", "dominant_subgenres", "signature_mechanics", "members"], "rows": crow,
                                   "link_columns": ["signature_mechanics", "members"], "max_links": 8}
        # how often clusters cut across subgenres
        cross = sum(1 for r in crow if len(set(by_id[g].data.get("subgenre") for g in r["members"])) > 1)
        stats["n_clusters"] = len(crow)
        stats["n_clusters_cross_subgenre"] = cross
        stats["cluster_k"] = k_chosen
        stats["cluster_mean_ari"] = next(r["mean_ari"] for r in curve if r["k"] == k_chosen)
        stats["cluster_drift_tolerance"] = tol
        stats["cluster_min_mean_ari"] = st_cfg["min_mean_ari"]
        stats["cluster_subsamples"] = st_cfg["subsamples"]
        stats["cluster_subsample_pct"] = int(round(st_cfg["fraction"] * 100))
        stats["n_stable_clusters"] = sum(1 for r in crow if r["stability"] >= st_cfg["stable_cluster"])
        stats["cluster_stable_jaccard"] = st_cfg["stable_cluster"]
        stats["cocluster_together"] = st_cfg["together"]
        stats["cocluster_apart"] = st_cfg["apart"]
        stats["cocluster_together_pct"] = int(round(100 * st_cfg["together"]))
        stats["cocluster_apart_pct"] = int(round(100 * st_cfg["apart"]))
        # agreement with subgenre labels, against a permutation null (labels shuffled across games)
        sub_lab = [g.data.get("subgenre") for g in games]
        obs_ari, obs_nmi = _ari(labels, sub_lab), _nmi(labels, sub_lab)
        prng = np.random.default_rng(st_cfg.get("permutations_seed", st_cfg["seed"] + 1))
        null_ari, null_nmi = [], []
        arr = np.array(sub_lab, dtype=object)
        for _ in range(st_cfg["permutations"]):
            perm = arr[prng.permutation(N)]
            null_ari.append(_ari(labels, perm))
            null_nmi.append(_nmi(labels, perm))
        P = st_cfg["permutations"]
        stats["cluster_subgenre_ari"] = _r(obs_ari, 2)
        stats["cluster_subgenre_nmi"] = _r(obs_nmi, 2)
        stats["cluster_subgenre_null_nmi"] = _r(float(np.mean(null_nmi)), 2)
        # NMI corrected for chance: 0 is what unrelated labelings score on average, 1 is identical labelings
        stats["cluster_subgenre_ami"] = _r(_ami(labels, sub_lab), 2)
        stats["p_cluster_subgenre_ari"] = _r((1 + sum(1 for x in null_ari if x >= obs_ari)) / (P + 1), 3)
        stats["p_cluster_subgenre_nmi"] = _r((1 + sum(1 for x in null_nmi if x >= obs_nmi)) / (P + 1), 3)
        stats["cluster_permutations"] = P
        shared["cocluster"] = cocluster

    # ---------------- family x subgenre
    fam_ids = list(fam_terms)
    subs_used = sorted({g.data.get("subgenre") for g in games}, key=lambda s: list(sub_terms).index(s) if s in sub_terms else 999)
    mat = {s: Counter() for s in subs_used}
    for g in games:
        for mid in gm[g.id]:
            mat[g.data["subgenre"]][by_id[mid].data["family"]] += 1
    frows = []
    for s in subs_used:
        tot = sum(mat[s].values()) or 1
        row = {"subgenre": s, "games": sum(1 for g in games if g.data["subgenre"] == s)}
        for f in fam_ids:
            row[f] = _r(mat[s][f] / tot, 2)
        frows.append(row)
    tables["family-by-subgenre"] = {"description": "Share of each subgenre's mechanic uses falling in each mechanic family (rows sum to 1).",
                                    "columns": ["subgenre", "games"] + fam_ids, "rows": frows}

    # ---------------- family summaries
    famrows = []
    for f in fam_ids:
        ms = [m for m in mechs if m.data["family"] == f]
        if not ms:
            continue
        famrows.append({
            "family": f,
            "mechanics": len(ms),
            "uses": sum(derived[m.id]["prevalence"] for m in ms),
            "mean_legibility": _r(np.mean([m.data["legibility"] for m in ms]), 2),
            "mean_emergence": _r(np.mean([m.data["emergence_potential"] for m in ms]), 2),
            "mean_authoring_cost": _r(np.mean([m.data["authoring_cost"] for m in ms]), 2),
            "mean_ai_leverage": _r(np.mean([m.data["ai_leverage"] for m in ms]), 2),
            "technique_exposure": _r(sum(derived[m.id]["technique_exposure"] for m in ms), 2),
            "mean_exposure": _r(sum(derived[m.id]["technique_exposure"] for m in ms) / len(ms), 2),
        })
    famrows.sort(key=lambda r: (-r["technique_exposure"], r["family"]))
    tables["family-summary"] = {"description": "Per mechanic family: size, total game uses, mean rubric scores, summed technique exposure (maturity x effect weights from vocab/rubrics.yaml), and exposure per mechanic. Sorted by summed exposure.",
                                "columns": ["family", "mechanics", "uses", "mean_legibility", "mean_emergence", "mean_authoring_cost", "mean_ai_leverage", "technique_exposure", "mean_exposure"], "rows": famrows}
    mean_rows = sorted(({"family": r["family"], "mechanics": r["mechanics"], "mean_exposure": r["mean_exposure"], "technique_exposure": r["technique_exposure"]} for r in famrows),
                       key=lambda r: (-r["mean_exposure"], r["family"]))
    tables["family-mean-exposure"] = {"description": "Mechanic families ordered by technique exposure per mechanic (summed exposure divided by the family's mechanics), so large families do not lead by size alone.",
                                      "columns": ["family", "mechanics", "mean_exposure", "technique_exposure"], "rows": mean_rows}
    comp_by_fam = {f: np.mean([m.data["compute_cost"] for m in mechs if m.data["family"] == f]) for f in fam_ids if any(m.data["family"] == f for m in mechs)}
    if comp_by_fam:
        stats["top_compute_family"] = fam_terms[max(comp_by_fam, key=lambda f: (comp_by_fam[f], f))]["label"]
        stats["top_legibility_family"] = fam_terms[max(famrows, key=lambda r: (r["mean_legibility"], r["family"]))["family"]]["label"]
    if famrows:
        stats["most_used_family"] = fam_terms[max(famrows, key=lambda r: (r["uses"], r["family"]))["family"]]["label"]
    if famrows and famrows[0]["technique_exposure"] > 0:
        stats["top_exposed_family"] = fam_terms[famrows[0]["family"]]["label"]
        stats["least_exposed_family"] = fam_terms[famrows[-1]["family"]]["label"]
        stats["top_mean_exposed_family"] = fam_terms[max(famrows, key=lambda r: (r["mean_exposure"], r["family"]))["family"]]["label"]

    # ---------------- AI leverage gap: high judged leverage but low current technique exposure
    gap_rows = []
    if techs:
        max_exp = max(derived[m.id]["technique_exposure"] for m in mechs) or 1
        for m in mechs:
            gap_rows.append({"mechanic": m.id, "family": m.data["family"], "ai_leverage": m.data["ai_leverage"],
                             "technique_exposure": derived[m.id]["technique_exposure"], "prevalence": derived[m.id]["prevalence"],
                             "gap": _r(m.data["ai_leverage"] / 5 - derived[m.id]["technique_exposure"] / max_exp, 3)})
        gap_rows.sort(key=lambda r: (-r["gap"], -r["prevalence"], r["mechanic"]))
    tables["leverage-gap"] = {"description": "Mechanics where rater-judged AI leverage outruns the techniques currently linked to them (normalized). High gap = under-researched opportunity or missing technique links. Equal gaps are ordered by prevalence, so more-used mechanics come first.",
                              "columns": ["mechanic", "family", "ai_leverage", "technique_exposure", "prevalence", "gap"], "rows": gap_rows[:25], "link_columns": ["mechanic"]}
    exp_rows = sorted(({"mechanic": m.id, "family": m.data["family"], "technique_exposure": derived[m.id]["technique_exposure"],
                        "technique_count": derived[m.id]["technique_count"], "prevalence": derived[m.id]["prevalence"]} for m in mechs),
                      key=lambda r: (-r["technique_exposure"], -r["prevalence"], r["mechanic"]))
    tables["most-exposed-mechanics"] = {"description": "Mechanics most affected by the technique set.", "columns": ["mechanic", "family", "technique_exposure", "technique_count", "prevalence"],
                                        "rows": exp_rows[:25], "link_columns": ["mechanic"]}

    # ---------------- technique x family matrix
    trows = []
    for t in techs:
        row = {"technique": t.id, "category": t.data["category"], "maturity": t.data["maturity"], "trl": t.data["trl"], "horizon": t.data["horizon"]}
        fp = derived[t.id]["families_affected"]
        row["families"] = ", ".join(f"{fam_terms[f]['label']} ({n})" for f, n in sorted(fp.items(), key=lambda x: (-x[1], x[0])))
        trows.append(row)
    trows.sort(key=lambda r: (-MATURITY_ORDER.index(r["maturity"]), -r["trl"], r["technique"]))
    tables["technique-landscape"] = {"description": "Techniques ordered by game-deployment maturity and TRL, with mechanic families they affect.",
                                     "columns": ["technique", "category", "maturity", "trl", "horizon", "families"], "rows": trows, "link_columns": ["technique"]}
    zero = [m for m in mechs if derived[m.id]["technique_exposure"] == 0]
    stats["n_mechanics_zero_exposure"] = len(zero)
    total_uses = sum(derived[m.id]["prevalence"] for m in mechs) or 1
    stats["pct_uses_on_zero_exposure"] = _r(100 * sum(derived[m.id]["prevalence"] for m in zero) / total_uses, 0)
    # opportunities propose techniques for mechanics that no published result reaches yet: count the opportunity-mechanic
    # pairs that none of the opportunity's techniques has an affects edge to, and the share of uses left unreached once a
    # mechanic that an opportunity proposes a technique for counts as reached
    reach = {t.id: {a["id"] for a in t.data.get("affects", [])} for t in techs}
    opp_pairs = [(m, o.data.get("applies") or []) for o in opps for m in o.data.get("involves") or []]
    stats["n_opportunity_mechanic_pairs"] = len(opp_pairs)
    stats["n_opportunity_pairs_unlinked"] = sum(1 for m, ts in opp_pairs if not any(m in reach.get(t, ()) for t in ts))
    proposed = {m for m, ts in opp_pairs if ts}
    stats["pct_uses_on_zero_exposure_unproposed"] = _r(100 * sum(derived[m.id]["prevalence"] for m in zero if m.id not in proposed) / total_uses, 0)
    top10 = sorted(mechs, key=lambda m: (-derived[m.id]["prevalence"], m.id))[:10]
    stats["n_top10_prevalent_zero_exposure"] = sum(1 for m in top10 if derived[m.id]["technique_exposure"] == 0)
    early = [derived[m.id]["earliest_year"] for m in mechs if derived[m.id]["earliest_year"]]
    stats["pct_mechanics_seen_by_2000"] = _r(100 * sum(1 for y in early if y <= 2000) / max(len(early), 1), 0)
    eff = Counter(a["effect"] for t in techs for a in t.data.get("affects", []))
    for k in vocab_terms(vocabs, "effect"):
        stats[f"n_effect_{k.replace('-', '_')}"] = eff.get(k, 0)
    tables["effect-distribution"] = {"description": "How techniques change mechanics, by effect type.", "columns": ["effect", "edges"],
                                     "rows": [{"effect": k, "edges": v} for k, v in sorted(eff.items(), key=lambda x: (-x[1], x[0]))]}
    if eff:
        stats["top_effect"] = vocab_terms(vocabs, "effect")[eff.most_common(1)[0][0]]["label"]
        stats["rarest_effect"] = vocab_terms(vocabs, "effect")[min(eff.items(), key=lambda x: (x[1], x[0]))[0]]["label"]
        stats["n_affects_edges"] = sum(eff.values())
    mat_counts = Counter(t.data["maturity"] for t in techs)
    for k in MATURITY_ORDER:
        stats[f"n_technique_{k.replace('-', '_')}"] = mat_counts.get(k, 0)
    det = Counter(t.data["determinism_impact"] for t in techs)
    stats["n_technique_breaks_determinism"] = det.get("breaks", 0)
    rt = [t for t in techs if {"client-realtime", "server-realtime"} & set(t.data["runtime"])]
    stats["n_technique_runtime"] = len(rt)
    for k in ("breaks", "mitigable", "preserves"):
        stats[f"n_technique_runtime_{k}"] = sum(1 for t in rt if t.data["determinism_impact"] == k)

    # ---------------- opportunities ranked
    orows = sorted(({"opportunity": o.id, "type": o.data["opportunity_type"], "priority": derived[o.id]["priority"], "impact": o.data["impact"],
                     "feasibility": o.data["feasibility"], "novelty": o.data["novelty"], "horizon": o.data["horizon"]} for o in opps),
                   key=lambda r: (-r["priority"], r["opportunity"]))
    tables["opportunities-ranked"] = {"description": "Opportunities by composite priority (weighted geometric mean of impact, feasibility, novelty; weights in vocab/rubrics.yaml).",
                                      "columns": ["opportunity", "type", "priority", "impact", "feasibility", "novelty", "horizon"], "rows": orows, "link_columns": ["opportunity"]}
    if orows:
        stats["top_opportunity"] = by_id[orows[0]["opportunity"]].data["name"]
    stats["n_predictions"] = len(opps)
    res = sorted(o.data["falsifiable_signal"]["resolve_by"] for o in opps)
    stats["first_prediction_resolves"] = res[0] if res else None
    if res:
        stats["first_prediction_resolves_long"], stats["first_prediction_resolves_spoken"] = written_dates(res[0])
    outcomes = Counter()
    for o in opps:
        r = o.data["falsifiable_signal"].get("resolution")
        derived[o.id]["prediction_status"] = r["outcome"] if r else "open"
        outcomes[r["outcome"] if r else "open"] += 1
    for k in ["open"] + list(vocab_terms(vocabs, "prediction_outcome")):
        stats[f"n_predictions_{k}"] = outcomes.get(k, 0)

    # ---------------- raters: agreement between independent ratings, and calibration results
    runs = {r.id: r for r in ents.get("run", [])}
    pair_stats = defaultdict(lambda: {"scores": 0, "pairs": 0, "exact": 0, "within_one": 0})
    n_ratings = 0
    rated_mechs: set[str] = set()
    for t in ("mechanic", "game", "technique", "opportunity"):
        for e in sorted(live.get(t, []), key=lambda e: e.id):
            per = defaultdict(list)
            for r in e.data.get("ratings") or []:
                per[r["field"]].append(r)
                n_ratings += 1
            for fld, rs in sorted(per.items()):
                ps = [(x, y) for i, x in enumerate(rs) for y in rs[i + 1:] if independent(runs.get(x["run"]), runs.get(y["run"]))]
                if ps:
                    if t == "mechanic":
                        rated_mechs.add(e.id)
                    ag = pair_stats[fld]
                    ag["scores"] += 1
                    ag["pairs"] += len(ps)
                    ag["exact"] += sum(1 for x, y in ps if x["value"] == y["value"])
                    ag["within_one"] += sum(1 for x, y in ps if abs(x["value"] - y["value"]) <= 1)
    tables["rater-agreement"] = {"description": "Agreement between ratings from independent runs (different operator, and different model for agent runs), per scored field. A field appears once a second rater has scored it (tasks/rate-scores.md).",
                                 "columns": ["field", "scores", "pairs", "exact", "within_one"],
                                 "rows": [{"field": f, "scores": v["scores"], "pairs": v["pairs"], "exact": _r(v["exact"] / v["pairs"], 2), "within_one": _r(v["within_one"] / v["pairs"], 2)} for f, v in sorted(pair_stats.items())]}
    stats["n_ratings"] = n_ratings
    # how far the second ratings reach, and how often independent raters agree on each scale (chapter 5)
    stats["n_mechanics_independently_rated"] = len(rated_mechs)
    for f, v in sorted(pair_stats.items()):
        stats[f"pct_rater_exact_{f}"] = int(round(100 * v["exact"] / v["pairs"]))
        stats[f"pct_rater_within_one_{f}"] = int(round(100 * v["within_one"] / v["pairs"]))
    stats["n_scores_independently_rated"] = sum(v["scores"] for v in pair_stats.values())
    stats["n_mechanic_scores"] = sum(1 for m in mechs for f, s in rub["scales"].items() if s.get("applies_to") == "mechanic" and m.data.get(f) is not None)
    n_mech_rated = sum(v["scores"] for f, v in pair_stats.items() if (rub["scales"].get(f) or {}).get("applies_to") == "mechanic")
    stats["pct_mechanic_scores_independently_rated"] = _r(100 * n_mech_rated / max(stats["n_mechanic_scores"], 1), 0)
    cal = load_calibration(load_registry())
    cal_rows = []
    for r in sorted(runs.values(), key=lambda r: r.id):
        c = r.data.get("calibration")
        if c and cal:
            ag = calibration_agreement(cal.get("mechanics") or {}, c.get("scores") or {})
            cal_rows.append({"run": r.id, "model": (r.data.get("agent") or {}).get("model", ""), "operator": r.data.get("operator"),
                         "scores": ag["n"], "exact": ag["exact"], "within_one": ag["within_one"], "kappa": ag["kappa_quadratic"]})
    tables["calibration-results"] = {"description": f"Raters' blind scores on the calibration set ({cal.get('id') if cal else 'missing'}) compared with its frozen scores: exact and within-one agreement and quadratic-weighted kappa.",
                                     "columns": ["run", "model", "operator", "scores", "exact", "within_one", "kappa"], "rows": cal_rows}
    stats["n_calibrated_runs"] = len(cal_rows)
    stats["n_calibration_mechanics"] = len((cal or {}).get("mechanics") or {})

    # ---------------- adoption over time
    by_decade = Counter()
    for m in mechs:
        y = derived[m.id]["earliest_year"]
        if y:
            by_decade[f"{(y // 10) * 10}s"] += 1
    tables["mechanic-origins-by-decade"] = {"description": "Mechanics by decade of earliest appearance in the dataset (a lower bound on true origin; dataset is a sample).",
                                            "columns": ["decade", "mechanics"], "rows": [{"decade": k, "mechanics": v} for k, v in sorted(by_decade.items())]}
    late = sorted((m for m in mechs if (derived[m.id]["earliest_year"] or 0) >= 2010),
                  key=lambda m: (m.data["family"], derived[m.id]["earliest_year"], m.id))
    tables["mechanics-since-2010"] = {"description": "Mechanics whose earliest appearance in the dataset is 2010 or later, grouped by family.",
                                      "columns": ["family", "mechanic", "earliest_year", "earliest_game"],
                                      "rows": [{"family": fam_terms[m.data["family"]]["label"], "mechanic": m.id,
                                                "earliest_year": derived[m.id]["earliest_year"], "earliest_game": derived[m.id]["earliest_game"]} for m in late],
                                      "link_columns": ["mechanic", "earliest_game"]}
    stats["n_mechanics_since_2010"] = len(late)
    total_dated = sum(by_decade.values())
    stats["pct_mechanics_first_seen_1980_1999"] = _r(100 * (by_decade.get("1980s", 0) + by_decade.get("1990s", 0)) / total_dated, 0) if total_dated else None
    stats["peak_origin_decade"] = max(by_decade.items(), key=lambda x: (x[1], x[0]))[0] if by_decade else None
    games_by_decade = Counter(f"{(y // 10) * 10}s" for y in yrs)
    tables["games-by-decade"] = {"description": "Games in the dataset by decade of first release.", "columns": ["decade", "games"],
                                 "rows": [{"decade": k, "games": v} for k, v in sorted(games_by_decade.items())]}

    # ---------------- verification queue
    q = []
    for t in ("technique", "game", "mechanic", "opportunity"):
        for e in sorted(live.get(t, []), key=lambda e: e.id):
            if e.data.get("status") == "asserted":
                q.append({"type": t, "id": e.id, "name": e.data.get("name")})
    tables["verification-queue"] = {"description": "Asserted entities awaiting sources, in triage order.", "columns": ["type", "id", "name"], "rows": q}

    # ---------------- figures
    figures.update(_figures(mechs, derived, fam_terms, famrows, by_id, games, year))
    # the byline names the first contributors by first run; everyone after them is credited as "SimGrammar contributors"
    contrib = [r["contributor"] for r in (tables.get("contributors") or {}).get("rows") or []]
    k = int((read_yaml(ROOT / "report" / "meta.yaml") or {}).get("byline_names", 3))
    byline = contrib[:k] + (["SimGrammar contributors"] if len(contrib) > k else [])
    stats["byline"] = ", ".join(byline[:-1]) + (", and " if len(byline) > 2 else " and ") + byline[-1] if len(byline) > 1 else "".join(byline)
    import viz  # local import: viz renders figures from the structures computed above
    vizzes = viz.build(shared, live, by_id, derived, tables, stats, vocabs, cfg)
    return {"derived": {k: dict(sorted(v.items())) for k, v in sorted(derived.items())}, "stats": dict(sorted(stats.items())),
            "tables": tables, "figures": figures, "vizzes": vizzes, "byline": byline, "cocluster": shared.get("cocluster", {}),
            "pair_count": shared.get("pair_count", {}), "mechanic_ids": {m.id for m in mechs}}


def _contingency(a, b):
    _, ai = np.unique(np.asarray(a, dtype=object).astype(str), return_inverse=True)
    _, bi = np.unique(np.asarray(b, dtype=object).astype(str), return_inverse=True)
    C = np.zeros((ai.max() + 1, bi.max() + 1))
    np.add.at(C, (ai, bi), 1)
    return C


def _ari(a, b) -> float:
    """Adjusted Rand index (Hubert and Arabie 1985) between two labelings of the same items."""
    C = _contingency(a, b)
    c2 = lambda x: x * (x - 1) / 2  # noqa: E731
    s, sa, sb, n = c2(C).sum(), c2(C.sum(1)).sum(), c2(C.sum(0)).sum(), c2(C.sum())
    exp = sa * sb / n if n else 0.0
    mx = (sa + sb) / 2
    return float((s - exp) / (mx - exp)) if mx != exp else 1.0


def _ari_int(a, b) -> float:
    """Adjusted Rand index for two integer labelings (fcluster output); same value as _ari, faster."""
    a = np.asarray(a) - np.min(a)
    b = np.asarray(b) - np.min(b)
    nb = int(b.max()) + 1
    C = np.bincount(a * nb + b, minlength=(int(a.max()) + 1) * nb).reshape(-1, nb).astype(float)
    c2 = lambda x: x * (x - 1) / 2  # noqa: E731
    s, sa, sb, n = c2(C).sum(), c2(C.sum(1)).sum(), c2(C.sum(0)).sum(), c2(C.sum())
    exp = sa * sb / n if n else 0.0
    mx = (sa + sb) / 2
    return float((s - exp) / (mx - exp)) if mx != exp else 1.0


def _nmi(a, b) -> float:
    """Normalized mutual information, arithmetic-mean normalization."""
    C = _contingency(a, b)
    P = C / C.sum()
    pa, pb = P.sum(1), P.sum(0)
    nz = P > 0
    mi = float((P[nz] * np.log(P[nz] / np.outer(pa, pb)[nz])).sum())
    ha = float(-(pa[pa > 0] * np.log(pa[pa > 0])).sum())
    hb = float(-(pb[pb > 0] * np.log(pb[pb > 0])).sum())
    return mi / ((ha + hb) / 2) if ha + hb else 1.0


def _ami(a, b) -> float:
    """Adjusted mutual information (Vinh, Epps and Bailey 2010), arithmetic-mean normalization like _nmi:
    (MI - E[MI]) / (mean entropy - E[MI]), with E[MI] taken over all labelings with the same cluster sizes."""
    C = _contingency(a, b)
    n = C.sum()
    ra, cb = C.sum(1), C.sum(0)
    P = C / n
    pa, pb = ra / n, cb / n
    nz = P > 0
    mi = float((P[nz] * np.log(P[nz] / np.outer(pa, pb)[nz])).sum())
    ha = float(-(pa[pa > 0] * np.log(pa[pa > 0])).sum())
    hb = float(-(pb[pb > 0] * np.log(pb[pb > 0])).sum())
    emi = 0.0
    for ai in ra:
        for bj in cb:
            lo, hi = int(max(1, ai + bj - n)), int(min(ai, bj))
            if hi < lo:
                continue
            nij = np.arange(lo, hi + 1, dtype=float)
            logp = (gammaln(ai + 1) + gammaln(bj + 1) + gammaln(n - ai + 1) + gammaln(n - bj + 1) - gammaln(n + 1)
                    - gammaln(nij + 1) - gammaln(ai - nij + 1) - gammaln(bj - nij + 1) - gammaln(n - ai - bj + nij + 1))
            emi += float((nij / n * np.log(n * nij / (ai * bj)) * np.exp(logp)).sum())
    den = (ha + hb) / 2 - emi
    return (mi - emi) / den if den else 1.0


# ======================================================================= SVG
_FONT = "style=\"font-family:var(--mono,'IBM Plex Mono',ui-monospace,Menlo,monospace);font-size:10px\""


def _svg(w, h, body):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}' width='{w}' height='{h}' {_FONT}>"
            f"<rect width='{w}' height='{h}' style='fill:var(--paper,#fafaf7)'/>{body}</svg>\n")


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;")


def _figures(mechs, derived, fam_terms, famrows, by_id, games, year):
    figs = {}
    if not mechs:
        return figs
    # 1. legibility vs emergence, bubble = prevalence (deterministic jitter from id hash)
    W, H, L, B = 560, 460, 60, 50
    body = []
    for v in range(1, 6):
        x = L + (v - 0.5) * (W - L - 20) / 5
        y = H - B - (v - 0.5) * (H - B - 20) / 5
        body.append(f"<line x1='{x:.1f}' y1='20' x2='{x:.1f}' y2='{H-B}' style='stroke:var(--rule,#dcdcd4)'/>")
        body.append(f"<line x1='{L}' y1='{y:.1f}' x2='{W-20}' y2='{y:.1f}' style='stroke:var(--rule,#dcdcd4)'/>")
        body.append(f"<text x='{x:.1f}' y='{H-B+16}' text-anchor='middle'>{v}</text>")
        body.append(f"<text x='{L-10}' y='{y+4:.1f}' text-anchor='end'>{v}</text>")
    maxp = max(derived[m.id]["prevalence"] for m in mechs) or 1
    for m in sorted(mechs, key=lambda m: -derived[m.id]["prevalence"]):
        h = int(__import__("hashlib").md5(m.id.encode()).hexdigest(), 16)
        jx = ((h % 1000) / 1000 - 0.5) * 0.7
        jy = (((h // 1000) % 1000) / 1000 - 0.5) * 0.7
        x = L + (m.data["legibility"] - 0.5 + jx) * (W - L - 20) / 5
        y = H - B - (m.data["emergence_potential"] - 0.5 + jy) * (H - B - 20) / 5
        r = 2.5 + 9 * math.sqrt(derived[m.id]["prevalence"] / maxp)
        body.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r:.1f}' fill-opacity='0.3' style='fill:var(--ink,#171717);stroke:var(--ink,#171717);stroke-width:0.6'><title>{_esc(m.data['name'])}</title></circle>")
    body.append(f"<text x='{(W+L)/2:.0f}' y='{H-12}' text-anchor='middle'>Legibility (1 opaque - 5 transparent)</text>")
    body.append(f"<text transform='translate(16,{(H-B)/2:.0f}) rotate(-90)' text-anchor='middle'>Emergence potential</text>")
    figs["legibility-vs-emergence"] = {"svg": _svg(W, H, "".join(body)),
                                       "caption": "Each mechanic placed by rubric legibility (x) and emergence potential (y); area ~ number of games using it. Jitter is deterministic."}

    # 2. technique exposure by family (horizontal bars)
    rows = [r for r in famrows if r["technique_exposure"] > 0]
    if rows:
        W, rowh, L = 620, 22, 190
        H = 30 + rowh * len(rows) + 30
        mx = max(r["technique_exposure"] for r in rows)
        body = []
        for i, r in enumerate(rows):
            y = 20 + i * rowh
            wbar = (W - L - 60) * r["technique_exposure"] / mx
            body.append(f"<text x='{L-8}' y='{y+14}' text-anchor='end'>{_esc(fam_terms[r['family']]['label'])}</text>")
            body.append(f"<rect x='{L}' y='{y+3}' width='{wbar:.1f}' height='{rowh-7}' style='fill:var(--ink,#171717)'/>")
            body.append(f"<text x='{L+wbar+6:.1f}' y='{y+14}'>{r['technique_exposure']}</text>")
        body.append(f"<text x='{L}' y='{H-8}' style='fill:var(--muted,#696961)'>Summed technique exposure (maturity x effect weights)</text>")
        figs["exposure-by-family"] = {"svg": _svg(W, H, "".join(body)), "caption": "Where current techniques concentrate: summed exposure of each family's mechanics."}

    # 3. cumulative mechanics by earliest year
    ys = sorted(derived[m.id]["earliest_year"] for m in mechs if derived[m.id]["earliest_year"])
    if ys:
        W, H, L, B = 620, 300, 50, 40
        y0, y1 = ys[0], max(ys[-1], ys[0] + 1)
        n = len(ys)
        pts = []
        for i, y in enumerate(ys, start=1):
            x = L + (y - y0) / (y1 - y0) * (W - L - 20)
            yy = H - B - i / n * (H - B - 20)
            pts.append(f"{x:.1f},{yy:.1f}")
        body = [f"<polyline points='{' '.join(pts)}' style='fill:none;stroke:var(--ink,#171717);stroke-width:2'/>"]
        for dec in range((y0 // 10) * 10, y1 + 1, 10):
            if dec < y0:
                continue
            x = L + (dec - y0) / (y1 - y0) * (W - L - 20)
            body.append(f"<line x1='{x:.1f}' y1='20' x2='{x:.1f}' y2='{H-B}' style='stroke:var(--rule,#dcdcd4)'/><text x='{x:.1f}' y='{H-B+16}' text-anchor='middle'>{dec}</text>")
        body.append(f"<text x='{L-8}' y='{H-B}' text-anchor='end'>0</text><text x='{L-8}' y='26' text-anchor='end'>{n}</text>")
        body.append(f"<text x='{(W+L)/2:.0f}' y='{H-6}' text-anchor='middle'>Year of earliest dataset game using the mechanic</text>")
        figs["mechanic-accumulation"] = {"svg": _svg(W, H, "".join(body)),
                                         "caption": "Cumulative count of mechanics by first appearance in the dataset. Steps mark the years a design vocabulary expanded."}
    return figs
