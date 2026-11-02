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
import re
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from scipy.special import gammaln
from scipy.stats import rankdata, spearmanr

from lib import CALIBRATION_SCALES, ROOT, calibration_agreement, independent, load_calibration, load_registry, lower_median, read_yaml, vocab_terms

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
    # evidence: status partitions the records (the four types that carry one) into sourced or verified, asserted, and
    # contested, so n_sourced_or_verified + n_asserted + n_contested == n_records. Citing is a different count: it also
    # holds the contested records, whose sources disagree, and asserted records that already cite a source in a claim but
    # have not been promoted. Pages that state either take these stats rather than counting for themselves.
    recs = [e for t in ("game", "mechanic", "technique", "opportunity") for e in live.get(t, [])]
    status = Counter(e.data.get("status") for e in recs)
    stats["n_records"] = len(recs)
    stats["n_sourced_or_verified"] = status.get("sourced", 0) + status.get("verified", 0)
    stats["n_asserted"] = status.get("asserted", 0)
    stats["n_verified"] = status.get("verified", 0)
    stats["n_contested"] = status.get("contested", 0)
    stats["n_records_citing"] = sum(1 for e in recs if outgoing.get(e.id, {}).get("cites"))
    stats["n_asserted_citing"] = sum(1 for e in recs if e.data.get("status") == "asserted" and outgoing.get(e.id, {}).get("cites"))
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
        # §5.1: how far the head of the prevalence distribution rests on tags a rule sets, on unsourced mechanics, and on
        # interface and structure. A tag is rule-set when the game's time_model or modding term requires the mechanic
        # (E033), so the tag restates the field; tags on games whose term only allows the mechanic were coded one by one.
        # The state-owning variant drops whole families as a proxy for a per-mechanic classification nobody has coded.
        req_by = defaultdict(set)  # mechanic -> {(field, term)} whose term requires it
        for fld in ("time_model", "modding"):
            for term, t in vocab_terms(vocabs, fld).items():
                if t.get("requires_mechanic"):
                    req_by[t["requires_mechanic"]].add((fld, str(term)))
        rule_set = Counter(mid for g in games for mid in gm[g.id] if any(str(g.data.get(f)) == v for f, v in req_by.get(mid, ())))
        for mid in sorted(req_by):
            key = mid.replace("-", "_")
            stats[f"n_{key}_rule_tags"] = rule_set.get(mid, 0)
            stats[f"n_{key}_coded_tags"] = derived[mid]["prevalence"] - rule_set.get(mid, 0) if mid in derived else 0
        # one list for this check and §8.2's unreached share, so the two leave out the same families (review E37)
        nonstate_fams = tuple(cfg.get("nonstate_families") or ())
        ns_words = [str(fam_terms.get(f, {}).get("label", f)).replace("&", "and").lower() for f in nonstate_fams]
        stats["nonstate_family_names"] = ", ".join(ns_words[:-1]) + ", and " + ns_words[-1] if len(ns_words) > 2 else " and ".join(ns_words)
        stats["n_nonstate_families"] = len(nonstate_fams)
        asserted_m = {m.id for m in mechs if m.data.get("status") == "asserted"}
        prev_rows = []
        for variant, key, keep, count in (
                ("all tags", "", lambda m: True, lambda m: derived[m.id]["prevalence"]),
                ("rule-set tags (E033) left out", "coded", lambda m: True, lambda m: derived[m.id]["prevalence"] - rule_set.get(m.id, 0)),
                ("asserted mechanics left out", "sourced", lambda m: m.id not in asserted_m, lambda m: derived[m.id]["prevalence"]),
                ("state-owning families only", "state", lambda m: m.data.get("family") not in nonstate_fams, lambda m: derived[m.id]["prevalence"])):
            ms_ = sorted((m for m in mechs if keep(m)), key=lambda m: (-count(m), m.id))
            prev_rows.append({"variant": variant, "mechanics": len(ms_), "uses": sum(count(m) for m in ms_),
                              "most_used": ", ".join(f"{m.data['name']} ({count(m)})" for m in ms_[:6])})
            if key and ms_:
                stats[f"most_prevalent_{key}_mechanic"] = ms_[0].data["name"]
                stats[f"most_prevalent_{key}_mechanic_share_pct"] = _r(100 * count(ms_[0]) / max(N, 1), 0)
                stats[f"n_mechanics_{key}_variant"] = len(ms_)
        tables["prevalence-sensitivity"] = {
            "description": "The six most used mechanics, with the number of games tagging each, under four readings: every tag; tags that a "
                           "game's time model or modding field requires (rule E033) left out, so pause and modding count only where a "
                           "contributor coded them; mechanics still asserted (no source) left out; and mechanics in the "
                           f"{stats['nonstate_family_names']} families left out, a family-level proxy for mechanics that own "
                           "simulation state (the families §8.2 leaves out of the unreached share).",
            "columns": ["variant", "mechanics", "uses", "most_used"], "rows": prev_rows}
        stats["n_mechanics_asserted_uses"] = sum(derived[m]["prevalence"] for m in asserted_m if m in derived)
        stats["pct_uses_on_asserted_mechanics"] = _r(100 * stats["n_mechanics_asserted_uses"] / max(sum(len(v) for v in gm.values()), 1), 0)
        stats["n_mechanics_nonstate_families"] = sum(1 for m in mechs if m.data.get("family") in nonstate_fams)
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
            null, kept = [], 0
            for _ in range(2000):
                pick = rng.sample(pool, len(early_ids))
                rng.shuffle(sizes)
                seen = set()
                for gid, k in zip(pick, sizes):
                    ms = used_by_game[gid]
                    seen.update(rng.sample(ms, min(k, len(ms))))
                    kept += min(k, len(ms))
                null.append(len(seen))
            stats["pct_uses_null_kept"] = _r(100 * kept / 2000 / max(sum(sizes), 1), 0)
            stats["n_mechanics_seen_null_mean"] = _r(float(np.mean(null)), 0)
            stats["pct_mechanics_seen_null_mean"] = _r(100 * float(np.mean(null)) / max(len(mechs), 1), 0)
            stats["p_mechanics_seen_by_2000"] = _r(sum(1 for v in null if v >= len(early_seen)) / len(null), 2)
            # The test above is the v0.3 one, kept because episode 2 narrates it. Its pool holds the early games themselves,
            # and a drawn game smaller than the size it is matched to keeps all its mechanics, so its sets carry fewer uses
            # than the early games do and cover less. The paper reports two nulls drawn only from games released after the
            # cutoff. "trim": as above, each drawn game cut to a random early game's size by a uniform random subset of its
            # mechanics. "uses": whole games in random order until their uses reach the early games' total, the last game cut
            # to fit, so a set carries exactly the early games' uses. Two-sided p doubles the smaller tail, each counted with +1.
            def _rarefy(cut, mode, draws=2000):
                early_ = [g.id for g in games if isinstance(year.get(g.id), int) and year[g.id] <= cut]
                late_ = [g.id for g in games if isinstance(year.get(g.id), int) and year[g.id] > cut]
                seen_ = len(set().union(*[set(used_by_game[x]) for x in early_]))
                sizes_ = [len(used_by_game[x]) for x in early_]
                total_ = sum(sizes_)
                rng_ = _random.Random(f"rarefy:{cut}:{mode}")
                cov_, kept_ = [], []
                for _ in range(draws):
                    s_, u_ = set(), 0
                    if mode == "trim":
                        rng_.shuffle(sizes_)
                        for gid, k in zip(rng_.sample(late_, len(early_)), sizes_):
                            part = rng_.sample(used_by_game[gid], min(k, len(used_by_game[gid])))
                            s_.update(part)
                            u_ += len(part)
                    else:
                        for gid in rng_.sample(late_, len(late_)):
                            ms = used_by_game[gid]
                            part = ms if u_ + len(ms) <= total_ else rng_.sample(ms, total_ - u_)
                            s_.update(part)
                            u_ += len(part)
                            if u_ >= total_:
                                break
                    cov_.append(len(s_))
                    kept_.append(u_)
                a_ = np.array(cov_, dtype=float)
                lo_, hi_ = (float(x) for x in np.percentile(a_, [2.5, 97.5]))
                tails = ((1 + int((a_ >= seen_).sum())) / (draws + 1), (1 + int((a_ <= seen_).sum())) / (draws + 1))
                return {"early": len(early_), "late": len(late_), "uses": total_, "seen": seen_, "mean": float(a_.mean()),
                        "sd": float(a_.std(ddof=1)), "lo": lo_, "hi": hi_, "p": min(1.0, 2 * min(tails)), "kept": float(np.mean(kept_))}
            rare_cuts = (1995, 1997, 2000, 2003, 2005)
            rare = {(c, mode): _rarefy(c, mode) for c in rare_cuts for mode in ("trim", "uses")}
            stats["rarefaction_draws"] = 2000
            stats["n_games_after_2000"] = rare[(2000, "uses")]["late"]
            stats["n_uses_by_2000"] = rare[(2000, "uses")]["uses"]
            for mode in ("trim", "uses"):
                r_ = rare[(2000, mode)]
                stats[f"n_mechanics_seen_null_{mode}_mean"] = _r(r_["mean"], 1)
                stats[f"n_mechanics_seen_null_{mode}_sd"] = _r(r_["sd"], 1)
                stats[f"n_mechanics_seen_null_{mode}_lo"] = _r(r_["lo"], 0)
                stats[f"n_mechanics_seen_null_{mode}_hi"] = _r(r_["hi"], 0)
                stats[f"p_mechanics_seen_{mode}"] = _r(r_["p"], 2)
                # the early games' excess over chance at the null's 97.5th and 2.5th percentiles, and the excess a set
                # would need to reach the upper 2.5% tail (the smallest early advantage this test can detect)
                stats[f"n_mechanics_seen_excess_{mode}_max"] = _r(r_["seen"] - r_["lo"], 0)
                stats[f"n_mechanics_seen_excess_{mode}_min"] = _r(r_["seen"] - r_["hi"], 0)
                stats[f"n_mechanics_seen_shortfall_{mode}"] = _r(r_["mean"] - r_["seen"], 1)
                stats[f"n_mechanics_seen_shortfall_{mode}_max"] = _r(r_["hi"] - r_["seen"], 0)
                stats[f"n_mechanics_detectable_{mode}"] = _r(r_["hi"] - r_["mean"], 0)
                stats[f"pct_mechanics_detectable_{mode}"] = _r(100 * (r_["hi"] - r_["mean"]) / max(len(mechs), 1), 0)
            stats["n_mechanics_seen_null_uses_round"] = int(round(rare[(2000, "uses")]["mean"]))  # a whole number for narration
            stats["n_uses_null_trim_mean"] = _r(rare[(2000, "trim")]["kept"], 0)
            stats["pct_uses_null_trim_kept"] = _r(100 * rare[(2000, "trim")]["kept"] / max(rare[(2000, "trim")]["uses"], 1), 0)
            stats["n_rarefaction_cutoffs_p05"] = sum(1 for c in rare_cuts for mode in ("trim", "uses") if rare[(c, mode)]["p"] <= 0.05)
            stats["n_rarefaction_cutoffs_uses_above_mean"] = sum(1 for c in rare_cuts if rare[(c, "uses")]["seen"] > rare[(c, "uses")]["mean"])
            stats["n_rarefaction_cutoffs"] = len(rare_cuts)
            tables["rarefaction-sensitivity"] = {
                "description": "Mechanics shown by the catalog games released in or before each cutoff year, against random sets drawn from the "
                               f"games released after it ({stats['rarefaction_draws']} sets each). Trimmed: as many games as the early set, each "
                               "cut to an early game's size by a random subset of its mechanics (a game smaller than its target keeps all of "
                               "them, so these sets carry fewer uses). Use-matched: whole games until the sets carry exactly the early games' "
                               "uses, the last game cut to fit. Intervals hold 95% of the random sets; p is two-sided.",
                "columns": ["cutoff", "early_games", "early_uses", "mechanics_seen", "trimmed_mean", "trimmed_p", "use_matched_mean",
                            "use_matched_interval", "use_matched_p"],
                "rows": [{"cutoff": c, "early_games": rare[(c, "uses")]["early"], "early_uses": rare[(c, "uses")]["uses"],
                          "mechanics_seen": rare[(c, "uses")]["seen"], "trimmed_mean": _r(rare[(c, "trim")]["mean"], 1),
                          "trimmed_p": _r(rare[(c, "trim")]["p"], 2), "use_matched_mean": _r(rare[(c, "uses")]["mean"], 1),
                          "use_matched_interval": f"{int(round(rare[(c, 'uses')]['lo']))}-{int(round(rare[(c, 'uses')]['hi']))}",
                          "use_matched_p": _r(rare[(c, "uses")]["p"], 2)} for c in rare_cuts]}
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
        # The reuse share against the catalog's composition: shuffle release years across games, each game keeping its
        # mechanics (so every game keeps its size and every mechanic its prevalence), re-date every mechanic by its earliest
        # game, and recompute the share. A mechanic many games use lands before 2001 under almost any dating, so the
        # shuffled share is what composition alone gives. Subsets: every mechanic, the ten most used left out, and thirds by
        # prevalence (ranked by games, ties by id). Seeded; p is two-sided, each tail counted with +1.
        dated_g = [g.id for g in games if isinstance(year.get(g.id), int)]
        m_index = {m.id: i for i, m in enumerate(mechs)}
        use_g = np.array([gi for gi, gid in enumerate(dated_g) for _ in used_by_game[gid]], dtype=int)
        use_m = np.array([m_index[mid] for gid in dated_g for mid in used_by_game[gid]], dtype=int)
        yrs_arr = np.array([year[gid] for gid in dated_g], dtype=int)
        by_prev = sorted((m for m in mechs if derived[m.id]["prevalence"] > 0), key=lambda m: (derived[m.id]["prevalence"], m.id))
        third = len(by_prev) // 3
        top10_ids = {m.id for m in sorted(mechs, key=lambda m: (-derived[m.id]["prevalence"], m.id))[:10]}
        reuse_sets = [("every mechanic", {m.id for m in by_prev}), ("the 10 most used left out", {m.id for m in by_prev} - top10_ids),
                      ("least used third", {m.id for m in by_prev[:third]}), ("middle third", {m.id for m in by_prev[third:2 * third]}),
                      ("most used third", {m.id for m in by_prev[2 * third:]})]
        masks = [np.array([m.id in s for m in mechs]) for _, s in reuse_sets]

        def _reuse_shares(yv):
            first = np.full(len(mechs), 9999)
            np.minimum.at(first, use_m, yv[use_g])
            old_u = (first <= 2000)[use_m]
            late_u = yv[use_g] >= 2010
            return [100 * float((old_u & late_u & mk[use_m]).sum()) / max(int((late_u & mk[use_m]).sum()), 1) for mk in masks]
        reuse_obs = _reuse_shares(yrs_arr)
        prng_reuse = np.random.default_rng(20261027)
        reuse_null = np.array([_reuse_shares(prng_reuse.permutation(yrs_arr)) for _ in range(999)])
        reuse_rows = []
        for i, (label, s) in enumerate(reuse_sets):
            col = reuse_null[:, i]
            lo_, hi_ = np.percentile(col, [2.5, 97.5])
            p_ = min(1.0, 2 * min((1 + int((col >= reuse_obs[i]).sum())) / 1000, (1 + int((col <= reuse_obs[i]).sum())) / 1000))
            prevs = [derived[m]["prevalence"] for m in s]
            reuse_rows.append({"mechanics": label, "count": len(s), "games_per_mechanic": f"{min(prevs)}-{max(prevs)}",
                               "uses_since_2010": int(sum(1 for x in late_ids for mid in used_by_game[x] if mid in s)),
                               "pct_on_pre2001": _r(reuse_obs[i], 1), "null_mean": _r(float(col.mean()), 1),
                               "null_interval": f"{lo_:.1f}-{hi_:.1f}", "p": _r(p_, 3)})
            if i == 0:
                stats["pct_uses_since_2010_on_pre2001_null_mean"] = _r(float(col.mean()), 0)
                stats["pct_uses_since_2010_on_pre2001_null_lo"] = _r(float(lo_), 0)
                stats["pct_uses_since_2010_on_pre2001_null_hi"] = _r(float(hi_), 0)
                stats["p_uses_since_2010_on_pre2001"] = _r(p_, 2)
                stats["pct_uses_since_2010_on_pre2001_vs_null"] = _r(reuse_obs[i] - float(col.mean()), 1)
            if i == 1:
                stats["pct_uses_since_2010_on_pre2001_excl_top10"] = _r(reuse_obs[i], 0)
                stats["pct_uses_since_2010_on_pre2001_excl_top10_null_mean"] = _r(float(col.mean()), 0)
        stats["n_reuse_subsets"] = len(reuse_rows)
        stats["n_reuse_subsets_above_null"] = sum(1 for r in reuse_rows if r["pct_on_pre2001"] > r["null_mean"])
        stats["reuse_permutations"] = 999
        tables["reuse-null"] = {
            "description": "Share of the mechanic uses in games released since 2010 that fall on mechanics already in a catalog game by 2000, "
                           "for every mechanic and for subsets by how many games use them, against 999 shuffles of release years across "
                           "games (each game keeps its mechanics; every mechanic is re-dated by its earliest game). The interval holds "
                           "95% of the shuffles; p is two-sided.",
            "columns": ["mechanics", "count", "games_per_mechanic", "uses_since_2010", "pct_on_pre2001", "null_mean", "null_interval", "p"],
            "rows": reuse_rows}
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
        all_runs = ents.get("run", [])   # (n_verified and n_contested are counted with the other statuses, above)
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

    score_pairs = [("legibility", "emergence_potential"), ("authoring_cost", "ai_leverage"), ("legibility", "compute_cost"),
                   ("emergence_potential", "tuning_difficulty"), ("legibility", "ai_leverage")]
    for a, b in score_pairs:
        r, p = corr(a, b)
        stats[f"rho_{a}_{b}"] = r
        stats[f"p_{a}_{b}"] = ("<0.001" if p is not None and p < 0.001 else (_r(p, 3) if p is not None else None))
    # How far the score correlations can be trusted (§5.6, review findings D8, D10, E23, E26). The p-values above treat
    # mechanics as independent draws, but mechanics in one family share the kind of state they own, and the interface
    # families sit at the floor of emergence potential by construction. So, on the stored scores:
    #  - a bootstrap over mechanics, and one over whole families (each drawn family brings all its mechanics), which keeps
    #    the family structure and is the interval to read; percentile intervals, fixed seed;
    #  - the correlation within families: ranks centred on each family's mean rank, so differences between families drop out;
    #  - the correlation if the doubly rated fields stored the mean or the upper of their ratings instead of the lower median,
    #    since with two raters the lower median is the lower score.
    sc_cfg = cfg.get("rubric_scores") or {}
    n_boot, boot_seed = int(sc_cfg.get("bootstrap", 2000)), int(sc_cfg.get("seed", 20261031))
    q_lo, q_hi = 50 * (1 - float(sc_cfg.get("interval", 0.95))), 50 * (1 + float(sc_cfg.get("interval", 0.95)))
    score_fields = [f for f in CALIBRATION_SCALES if all(isinstance(m.data.get(f), int) for m in mechs)]
    sv = {f: np.array([m.data[f] for m in mechs], float) for f in score_fields}
    alt = {"mean": {f: sv[f].copy() for f in score_fields}, "upper": {f: sv[f].copy() for f in score_fields}}
    for i, m in enumerate(mechs):
        for f in score_fields:
            vals = [r["value"] for r in m.data.get("ratings") or [] if r["field"] == f]
            if len(vals) > 1:
                alt["mean"][f][i], alt["upper"][f][i] = float(np.mean(vals)), float(max(vals))
    fam_of = np.array([m.data["family"] for m in mechs])
    members = [np.flatnonzero(fam_of == f) for f in sorted(set(fam_of))]
    rng = np.random.default_rng(boot_seed)
    draw_mech = rng.integers(0, len(mechs), (n_boot, len(mechs))) if mechs else None
    draw_fam = [np.concatenate([members[k] for k in pick]) for pick in rng.integers(0, len(members), (n_boot, len(members)))] if mechs else []
    crows = []
    for a, b in score_pairs:
        if a not in sv or b not in sv or stats.get(f"rho_{a}_{b}") is None:
            continue
        x, y = sv[a], sv[b]
        bm = _spearman_rows(x[draw_mech], y[draw_mech])
        bf = np.array([_spearman(x[ii], y[ii]) for ii in draw_fam])
        lab = lambda f: f.replace("_", " ").replace("ai leverage", "AI leverage")  # noqa: E731
        row = {"pair": f"{lab(a)} × {lab(b)}", "rho": stats[f"rho_{a}_{b}"], "p": stats[f"p_{a}_{b}"],
               "low": _r(np.nanpercentile(bm, q_lo), 2), "high": _r(np.nanpercentile(bm, q_hi), 2),
               "family_low": _r(np.nanpercentile(bf, q_lo), 2), "family_high": _r(np.nanpercentile(bf, q_hi), 2),
               "within_family": _r(_spearman_within(x, y, members), 2),
               "mean_rule": _r(_spearman(alt["mean"][a], alt["mean"][b]), 2), "upper_rule": _r(_spearman(alt["upper"][a], alt["upper"][b]), 2)}
        for k in ("low", "high", "family_low", "family_high", "within_family", "mean_rule", "upper_rule"):
            stats[f"rho_{a}_{b}_{k}"] = row[k]
        crows.append(row)
    stats["n_bootstrap"], stats["pct_bootstrap_interval"] = n_boot, round(q_hi - q_lo)
    rule_moves = [abs(r[k] - r["rho"]) for r in crows for k in ("mean_rule", "upper_rule") if r[k] is not None]
    stats["max_rho_change_aggregation"] = _r(max(rule_moves), 2) if rule_moves else None
    tables["score-correlations"] = {
        "description": f"Spearman correlations between rubric scores across all mechanics, on the stored scores. p treats mechanics as independent and is "
                       f"descriptive. Low and high bound a {round(q_hi - q_lo)}% bootstrap interval over mechanics, family low and high one over whole "
                       f"families ({n_boot} resamples each); within family ranks each score against its family's mean, so differences between families "
                       "drop out. Mean rule and upper rule store the mean or the higher of the two ratings on the doubly rated fields instead of the "
                       "lower median. Every score comes mostly from one model rater.",
        "columns": ["pair", "rho", "p", "low", "high", "family_low", "family_high", "within_family", "mean_rule", "upper_rule"], "rows": crows}
    # family means (the ceilings figure, §6) under the same alternatives: how far a family's mean moves, and how many of the
    # figure's marks change (the same rule as viz.constraint_profile: a cost at 3 or above, legibility below 3.3)
    shift, marks = 0.0, {"mean": 0, "upper": 0}
    for ii in members:
        for f in score_fields:
            shift = max(shift, abs(float(alt["upper"][f][ii].mean() - sv[f][ii].mean())))
        for k in marks:
            for f in ("authoring_cost", "compute_cost", "tuning_difficulty", "legibility"):
                if f in sv:
                    v0, v1 = sv[f][ii].mean(), alt[k][f][ii].mean()
                    marks[k] += int((v0 < 3.3) != (v1 < 3.3) if f == "legibility" else (v0 >= 3) != (v1 >= 3))
    stats["max_family_mean_shift_upper"] = _r(shift, 2)
    stats["n_family_marks_changed_mean"], stats["n_family_marks_changed_upper"] = marks["mean"], marks["upper"]
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
    # A baseline for pair coverage and for white space: a fixed-margin null that keeps every game's size and every
    # mechanic's prevalence and scatters the rest. Curveball trades (Strona et al. 2014): two games swap a random part of
    # the mechanics only one of them has. After a burn-in, every `null_thin` trades give one null catalog. Seeded and
    # sorted, so the build is deterministic. Each null catalog keeps its coverage, its coverage among mechanics in at
    # least `restricted_min_games` games, and the co-occurrence counts among the mechanics white space screens.
    cc = cfg["cooccurrence"]
    m_pos = {m: i for i, m in enumerate(mids)}
    cb_rows = [sorted(m_pos[m] for m in gm[g.id] if m in m_pos) for g in games]
    ws_thr = cfg["whitespace"]["min_prevalence_games"]
    ws_common = [m_pos[m] for m in mids if prev[m] >= ws_thr]
    iu = np.triu_indices(len(mids), 1)
    rmin = cc["restricted_min_games"]
    elig = np.array([prev[m] >= rmin for m in mids])
    in_restricted = elig[iu[0]] & elig[iu[1]]
    import random as _cb_random
    cb_rng = _cb_random.Random(cc["null_seed"])

    def _trade(k):
        for _ in range(k):
            i, j = cb_rng.sample(range(len(cb_rows)), 2)
            a_, b_ = set(cb_rows[i]), set(cb_rows[j])
            only_a, only_b = sorted(a_ - b_), sorted(b_ - a_)
            if not only_a or not only_b:
                continue
            pool_ = only_a + only_b
            cb_rng.shuffle(pool_)
            cb_rows[i] = sorted((a_ & b_) | set(pool_[: len(only_a)]))
            cb_rows[j] = sorted((a_ & b_) | set(pool_[len(only_a):]))
    null_cov, null_cov_r, null_ws = [], [], []
    if len(cb_rows) > 1 and mids:
        _trade(cc["null_burnin"])
        for _ in range(cc["null_samples"]):
            _trade(cc["null_thin"])
            Xn = np.zeros((len(cb_rows), len(mids)), dtype=np.int32)
            for r_, cols in enumerate(cb_rows):
                Xn[r_, cols] = 1
            Cn = Xn.T @ Xn
            up = Cn[iu]
            null_cov.append(100 * float((up > 0).mean()))
            null_cov_r.append(100 * float((up[in_restricted] > 0).mean()) if in_restricted.any() else 0.0)
            null_ws.append(Cn[np.ix_(ws_common, ws_common)].astype(np.int16))
    shared["cooccurrence_null"] = {"common": [mids[i] for i in ws_common], "counts": np.array(null_ws)}
    if null_cov:
        S_ = len(null_cov)
        nc, ncr = np.array(null_cov), np.array(null_cov_r)
        stats["cooccurrence_null_samples"] = S_
        stats["pair_coverage_null_mean_pct"] = _r(float(nc.mean()), 1)
        stats["pair_coverage_null_lo_pct"] = _r(float(np.percentile(nc, 2.5)), 1)
        stats["pair_coverage_null_hi_pct"] = _r(float(np.percentile(nc, 97.5)), 1)
        obs_cov = 100 * len(pair_count) / max(stats["n_possible_pairs"], 1)
        stats["p_pair_coverage"] = _r(min(1.0, 2 * min((1 + int((nc <= obs_cov).sum())) / (S_ + 1), (1 + int((nc >= obs_cov).sum())) / (S_ + 1))), 3)
        stats["n_pairs_short_of_null"] = int(round((float(nc.mean()) - obs_cov) / 100 * stats["n_possible_pairs"]))
        n_r = int(in_restricted.sum())
        obs_r = 100 * sum(1 for (a, b) in pair_count if prev[a] >= rmin and prev[b] >= rmin) / max(n_r, 1)
        stats["restricted_min_games"] = rmin
        stats["n_mechanics_restricted"] = int(elig.sum())
        stats["n_possible_pairs_restricted"] = n_r
        stats["pair_coverage_restricted_pct"] = _r(obs_r, 1)
        stats["pair_coverage_restricted_null_mean_pct"] = _r(float(ncr.mean()), 1)
        stats["pair_coverage_restricted_null_lo_pct"] = _r(float(np.percentile(ncr, 2.5)), 1)
        stats["pair_coverage_restricted_null_hi_pct"] = _r(float(np.percentile(ncr, 97.5)), 1)

    # ---------------- white space: common mechanics that rarely meet
    ws = cfg["whitespace"]
    thr = ws["min_prevalence_games"]
    common = [m for m in mids if prev[m] >= thr]
    wrows = []
    # the selection and the ranking by gap are unchanged; the fixed-margin null (co-occurrence block) adds, per pair, the
    # mean count over the null catalogs and the share of them with a count at or below the observed one (+1 counted)
    cn = shared["cooccurrence_null"]
    cn_pos = {m: i for i, m in enumerate(cn["common"])}
    S_ws = len(cn["counts"])
    candidates = []
    for a, b in combinations(sorted(common), 2):
        if ws["exclude_same_family"] and by_id[a].data["family"] == by_id[b].data["family"]:
            continue
        if by_id[a].data["family"] in ws.get("exclude_families", []) or by_id[b].data["family"] in ws.get("exclude_families", []):
            continue
        if (a, b) in tension_pairs:
            continue
        candidates.append((a, b))
        obs = pair_count.get((a, b), 0)
        if obs > ws["max_observed"]:
            continue
        expected = prev[a] * prev[b] / N
        row = {"mechanic_a": a, "mechanic_b": b, "family_a": by_id[a].data["family"], "family_b": by_id[b].data["family"],
               "observed": obs, "expected": _r(expected, 2), "gap": _r(expected - obs, 2)}
        if S_ws:
            nd = cn["counts"][:, cn_pos[a], cn_pos[b]]
            row["null_expected"] = _r(float(nd.mean()), 2)
            row["null_p"] = _r((1 + int((nd <= obs).sum())) / (S_ws + 1), 3)
        wrows.append(row)
    wrows.sort(key=lambda r: (-r["gap"], r["mechanic_a"], r["mechanic_b"]))
    shared.update({"common": common, "whitespace_all": wrows})
    ws_cols = ["mechanic_a", "mechanic_b", "family_a", "family_b", "observed", "expected", "gap"] + (["null_expected", "null_p"] if S_ws else [])
    tables["whitespace"] = {"description": f"Pairs of common mechanics (each in >= {ws['min_prevalence_games']} games, different families, not marked as tension{', excluding ' + ', '.join(fam_terms[f]['label'] for f in ws.get('exclude_families', [])) if ws.get('exclude_families') else ''}) that co-occur at most {ws['max_observed']} time(s). Gap = expected - observed co-occurrence under independence."
                                           + (f" Null expected = mean co-occurrence over {S_ws} null catalogs that keep every game's size and every mechanic's prevalence; null p = share of them with a count at or below the observed one, uncorrected for the pairs screened." if S_ws else ""),
                            "columns": ws_cols, "rows": wrows[: ws["top_n"]], "link_columns": ["mechanic_a", "mechanic_b"]}
    stats["n_whitespace_pairs"] = len(wrows)
    stats["n_common_mechanics"] = len(common)
    stats["whitespace_min_games"] = ws["min_prevalence_games"]
    stats["whitespace_top_n"] = min(ws["top_n"], len(wrows))
    stats["n_whitespace_candidates"] = len(candidates)
    stats["n_whitespace_observed_0"] = sum(1 for r in wrows if r["observed"] == 0)
    stats["n_whitespace_observed_1"] = sum(1 for r in wrows if r["observed"] == 1)
    # unsourced mechanics (E32) and rule-set tags (E033): how much of the list rests on them. Dropping a mechanic leaves the
    # other pairs' counts and order unchanged, so the list without them is the list minus the pairs they are in.
    asserted_ids = {m.id for m in mechs if m.data.get("status") == "asserted"}
    in_asserted = [r for r in wrows if r["mechanic_a"] in asserted_ids or r["mechanic_b"] in asserted_ids]
    stats["n_whitespace_pairs_asserted"] = len(in_asserted)
    stats["n_whitespace_top10_asserted"] = sum(1 for r in wrows[:10] if r["mechanic_a"] in asserted_ids or r["mechanic_b"] in asserted_ids)
    stats["n_whitespace_pairs_sourced"] = len(wrows) - len(in_asserted)
    stats["n_whitespace_pairs_modding_api"] = sum(1 for r in wrows if "modding-api" in (r["mechanic_a"], r["mechanic_b"]))
    if S_ws and wrows:
        stats["n_whitespace_null_p05"] = sum(1 for r in wrows if r["null_p"] <= 0.05)
        stats["n_whitespace_top_null_p05"] = sum(1 for r in wrows[: ws["top_n"]] if r["null_p"] <= 0.05)
        stats["n_whitespace_null_above_independence"] = sum(1 for r in wrows if r["null_expected"] > r["expected"])
        stats["whitespace_null_to_independence"] = _r(float(np.mean([r["null_expected"] / r["expected"] for r in wrows if r["expected"]])), 2)
        # the list as a whole: how many screened pairs would co-occur at most max_observed times in a null catalog
        ia_ = [cn_pos[a] for a, _ in candidates]
        ib_ = [cn_pos[b] for _, b in candidates]
        n_null = (cn["counts"][:, ia_, ib_] <= ws["max_observed"]).sum(axis=1) if candidates else np.zeros(S_ws)
        stats["n_whitespace_pairs_null_mean"] = _r(float(n_null.mean()), 0)
        stats["n_whitespace_pairs_null_lo"] = _r(float(np.percentile(n_null, 2.5)), 0)
        stats["n_whitespace_pairs_null_hi"] = _r(float(np.percentile(n_null, 97.5)), 0)
        stats["p_n_whitespace_pairs"] = _r((1 + int((n_null >= len(wrows)).sum())) / (S_ws + 1), 3)

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
        # every subsample's cut at every candidate k, kept for the curve and for the checks by k below
        sub_cuts = {}
        curve = []
        for kk in range(st_cfg["k_min"], st_cfg["k_max"] + 1):
            Lk = fcluster(Z, t=kk, criterion="maxclust")
            sub_cuts[kk] = [fcluster(Zb, t=kk, criterion="maxclust") for Zb in Zs]
            aris = [_ari_int(Lk[sb], lb) for sb, lb in zip(subs, sub_cuts[kk])]
            curve.append({"k": kk, "clusters": int(len(set(Lk.tolist()))), "mean_ari": _r(float(np.mean(aris)), 4), "_mean": float(np.mean(aris)),
                          "p10_ari": _r(float(np.percentile(aris, 10)), 4), "p90_ari": _r(float(np.percentile(aris, 90)), 4),
                          "largest_cluster_share": _r(Counter(Lk.tolist()).most_common(1)[0][1] / N, 2)})
        thr, tol = float(st_cfg["min_mean_ari"]), float(st_cfg.get("drift_tolerance", 0.0))
        passing = [r for r in curve if r["_mean"] >= thr]
        k_rule = passing[0]["k"] if passing else max(curve, key=lambda r: (r["_mean"], -r["k"]))["k"]
        k_chosen = int(cl["k"])
        mean_at = {r["k"]: r["_mean"] for r in curve}
        # drift only when the evidence is clear: the configured k has fallen well below the threshold, or a smaller k
        # now clears it by the same margin. Differences inside the margin are resampling noise, not a reason to move k.
        drift = (k_chosen in mean_at and mean_at[k_chosen] < thr - tol) or any(r["_mean"] >= thr + tol for r in curve if r["k"] < k_chosen)
        # the rule's pick under other thresholds (B2: the 0.75 is a convention, so show what it decides)
        # (each alternatives list is reported by its lowest and highest value, as <stat>_lo and <stat>_hi)
        alts = st_cfg.get("alternatives") or {}
        for end, t_ in (("lo", min(alts.get("min_mean_ari", [thr]))), ("hi", max(alts.get("min_mean_ari", [thr])))):
            hit = [r["k"] for r in curve if r["_mean"] >= float(t_)]
            stats[f"cluster_min_mean_ari_{end}"] = float(t_)
            stats[f"cluster_rule_k_{end}"] = hit[0] if hit else None
        # the k the rule cannot tell from the configured one: the run of k up to it whose mean ARI is within the drift
        # tolerance of the threshold (E28 asks whether the headline readings hold there)
        k_near = k_chosen
        while k_near - 1 in mean_at and mean_at[k_near - 1] >= thr - tol:
            k_near -= 1
        for r in curve:
            r["selection"] = ", ".join(x for x, hit in (("configured", r["k"] == k_chosen), ("rule today", r["k"] == k_rule)) if hit)
            del r["_mean"]
        tables["cluster-stability"] = {"description": f"Agreement between the full clustering and re-clusterings of {B} subsamples, each holding about {int(frac * 100)}% of games (adjusted Rand index between the full clustering restricted to the subsample's games and the subsample's own clustering, with its 10th and 90th percentiles across subsamples), for each candidate k. The selection rule picks the smallest k whose mean ARI reaches {thr}; k is fixed in report/analysis.yaml from the last selection, and the validator warns (W107) only when the configured k falls more than {tol} below the threshold or a smaller k clears it by more than {tol}.",
                                       "columns": ["k", "clusters", "mean_ari", "p10_ari", "p90_ari", "largest_cluster_share", "selection"], "rows": curve}
        stats["cluster_rule_k"] = k_rule
        stats["cluster_k_drift"] = 1 if drift else 0
        stats["cluster_k_near_min"] = k_near
        stats["cluster_p10_ari"] = next(r["p10_ari"] for r in curve if r["k"] == k_chosen)
        labels = fcluster(Z, t=k_chosen, criterion="maxclust")
        co = np.zeros((N, N))
        both = np.zeros((N, N))
        for sb, lb in zip(subs, sub_cuts[k_chosen]):
            co[np.ix_(sb, sb)] += (lb[:, None] == lb[None, :])
            both[np.ix_(sb, sb)] += 1
        C = np.where(both > 0, co / np.maximum(both, 1), 0.0)
        np.fill_diagonal(C, 1.0)
        cocluster = {"index": {g.id: i for i, g in enumerate(games)}, "value": lambda i, j: _r(float(C[i, j]), 3),
                     "together": st_cfg["together"], "apart": st_cfg["apart"]}
        # cluster-wise Jaccard (Hennig 2007, subsetting): the stability column. The full-membership version is reported
        # beside it for comparison (E9); with 80% subsamples it cannot much exceed 0.8 even when nothing regroups.
        clust_jac = _cluster_jaccard(labels, subs, sub_cuts[k_chosen])
        full_jac = _cluster_jaccard(labels, subs, sub_cuts[k_chosen], restrict=False)
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
            top_subs = Counter(g.data.get("subgenre") for g in members).most_common(2)
            label = " + ".join(by_id[m].data["name"] for m in topm[:2])
            for g in members:
                derived[g.id]["cluster"] = f"C{ci:02d}"
            crow.append({"cluster": f"C{ci:02d}", "label": label, "size": len(members),
                         "stability": _r(clust_jac.get(lab, 0.0), 2),
                         "dominant_subgenres": ", ".join(f"{sub_terms.get(s, {}).get('label', s)} ({n})" for s, n in top_subs),
                         "signature_mechanics": topm,
                         "members": [g.id for g in sorted(members, key=lambda g: (float(np.mean([D[gidx[g.id], gidx[o.id]] for o in members])), g.id))]})
        min_size = int(st_cfg.get("min_family_size", 1))
        tables["game-clusters"] = {"description": f"Games clustered by weighted Jaccard similarity of mechanic sets (average linkage, k={k_chosen} chosen by subsample stability, core weight {cl['core_weight']}{', inverse-prevalence weighting so ubiquitous mechanics do not dominate' if cl.get('idf') else ''}). Stability is the cluster's mean best-match Jaccard overlap across {B} subsamples of about {int(st_cfg['fraction'] * 100)}% of games: in each subsample the cluster is restricted to the games the subsample keeps and compared with every cluster of the subsample's own clustering by Jaccard index (the games in both, divided by the games in either), the best match counts, and subsamples keeping none of the cluster's games are skipped. A cluster with stability of at least {st_cfg['stable_cluster']} and at least {min_size} games counts as stable. Signature mechanics maximize within-cluster share x log-lift. Members are ordered by centrality (mean distance to the rest of the cluster), so the first members are the most typical.",
                                   "columns": ["cluster", "label", "size", "stability", "dominant_subgenres", "signature_mechanics", "members"], "rows": crow,
                                   "link_columns": ["signature_mechanics", "members"], "max_links": 8}
        # how often clusters cut across subgenres: any second subgenre (the original count), and stricter shares (E8)
        sub_lab = [g.data.get("subgenre") for g in games]
        sub_names, sub_codes = np.unique(np.asarray(sub_lab, dtype=object).astype(str), return_inverse=True)
        nS = len(sub_names)
        mixed_shares = [float(s) for s in cl.get("mixed_shares", [])]
        cross = _n_mixed(labels, sub_codes, nS)
        stats["n_clusters"] = len(crow)
        stats["n_clusters_cross_subgenre"] = cross
        stats["pct_clusters_cross_subgenre"] = _r(100 * cross / len(crow), 0)
        for s_ in mixed_shares:
            stats[f"n_clusters_mixed_{int(round(100 * s_))}"] = _n_mixed(labels, sub_codes, nS, s_)
            stats[f"pct_clusters_mixed_{int(round(100 * s_))}"] = _r(100 * stats[f"n_clusters_mixed_{int(round(100 * s_))}"] / len(crow), 0)
            stats[f"cluster_mixed_share_{int(round(100 * s_))}"] = int(round(100 * s_))
        stats["cluster_k"] = k_chosen
        stats["cluster_mean_ari"] = next(r["mean_ari"] for r in curve if r["k"] == k_chosen)
        stats["cluster_drift_tolerance"] = tol
        stats["cluster_min_mean_ari"] = st_cfg["min_mean_ari"]
        stats["cluster_subsamples"] = st_cfg["subsamples"]
        stats["cluster_subsample_pct"] = int(round(st_cfg["fraction"] * 100))
        # a stable cluster reaches the Jaccard threshold and holds at least min_family_size games: a pair or trio is
        # described by how often its games co-cluster, not by a cluster's stability (E28)
        stable_thr = float(st_cfg["stable_cluster"])
        stats["cluster_min_family_size"] = min_size
        stats["n_stable_clusters"] = sum(1 for r in crow if r["stability"] >= stable_thr and r["size"] >= min_size)
        stats["n_stable_clusters_any_size"] = sum(1 for r in crow if r["stability"] >= stable_thr)
        for end, t_ in (("lo", min(alts.get("stable_cluster", [stable_thr]))), ("hi", max(alts.get("stable_cluster", [stable_thr])))):
            stats[f"cluster_stable_jaccard_{end}"] = float(t_)
            stats[f"n_stable_clusters_jaccard_{end}"] = sum(1 for r in crow if r["stability"] >= float(t_) and r["size"] >= min_size)
        lab_of = {r["cluster"]: lab for r, (lab, _) in zip(crow, ordered)}
        stats["n_stable_clusters_full_membership"] = sum(1 for r in crow if _r(full_jac.get(lab_of[r["cluster"]], 0.0), 2) >= stable_thr)
        stats["cluster_full_membership_max"] = _r(max(full_jac.values()), 2)
        stats["cluster_stable_jaccard"] = st_cfg["stable_cluster"]
        stats["cocluster_together"] = st_cfg["together"]
        stats["cocluster_apart"] = st_cfg["apart"]
        stats["cocluster_together_pct"] = int(round(100 * st_cfg["together"]))
        stats["cocluster_apart_pct"] = int(round(100 * st_cfg["apart"]))
        # agreement with subgenre labels, against a permutation null (labels shuffled across games). Shuffling keeps
        # every subgenre's size, so E[MI], and with it AMI's correction, is the same for every shuffle.
        obs_ari, obs_nmi = _ari(labels, sub_lab), _nmi(labels, sub_lab)
        C_obs = _contingency(labels, sub_lab)
        emi_obs = _emi(C_obs.sum(1), C_obs.sum(0), C_obs.sum())
        prng = np.random.default_rng(st_cfg.get("permutations_seed", st_cfg["seed"] + 1))
        null_ari, null_nmi, null_ami = [], [], []
        null_mixed = defaultdict(list)
        arr = np.array(sub_lab, dtype=object)
        for _ in range(st_cfg["permutations"]):
            order = prng.permutation(N)
            perm = arr[order]
            null_ari.append(_ari(labels, perm))
            null_nmi.append(_nmi(labels, perm))
            null_ami.append(_ami(labels, perm, emi=emi_obs))
            for s_ in [1.0] + mixed_shares:
                null_mixed[s_].append(_n_mixed(labels, sub_codes[order], nS, s_))
        P = st_cfg["permutations"]
        stats["cluster_subgenre_ari"] = _r(obs_ari, 2)
        stats["cluster_subgenre_nmi"] = _r(obs_nmi, 2)
        stats["cluster_subgenre_null_nmi"] = _r(float(np.mean(null_nmi)), 2)
        # (+ 0.0 turns a rounded -0.0 into 0.0, which is what both chance-corrected scores average under the null)
        stats["cluster_subgenre_null_ari"] = _r(float(np.mean(null_ari)), 2) + 0.0
        stats["cluster_subgenre_null_ami"] = _r(float(np.mean(null_ami)), 2) + 0.0
        # NMI corrected for chance: 0 is what unrelated labelings score on average, 1 is identical labelings
        stats["cluster_subgenre_ami"] = _r(_ami(labels, sub_lab), 2)
        stats["p_cluster_subgenre_ari"] = _r((1 + sum(1 for x in null_ari if x >= obs_ari)) / (P + 1), 3)
        stats["p_cluster_subgenre_nmi"] = _r((1 + sum(1 for x in null_nmi if x >= obs_nmi)) / (P + 1), 3)
        stats["cluster_permutations"] = P
        # shuffled labels mix almost every cluster, so the mixed count is read against that null: p is the share of
        # shuffles with as few mixed clusters as observed (clusters purer than chance)
        stats["cluster_null_mixed"] = _r(float(np.mean(null_mixed[1.0])), 1)
        stats["p_cluster_mixed"] = _r((1 + sum(1 for x in null_mixed[1.0] if x <= cross)) / (P + 1), 3)
        for s_ in mixed_shares:
            stats[f"cluster_null_mixed_{int(round(100 * s_))}"] = _r(float(np.mean(null_mixed[s_])), 1)
        # many subgenre labels are small; pool them, or leave their games out, and recompute agreement (E8)
        small_n = int(cl.get("small_subgenre_games", 5))
        sub_n = Counter(sub_lab)
        big = np.array([sub_n[s] >= small_n for s in sub_lab])
        stats["cluster_small_subgenre_games"] = small_n
        stats["n_subgenres_small"] = sum(1 for v in sub_n.values() if v < small_n)
        stats["n_games_small_subgenres"] = int((~big).sum())
        stats["cluster_subgenre_ami_pooled"] = _r(_ami(labels, [s if sub_n[s] >= small_n else "(pooled)" for s in sub_lab]), 2)
        stats["cluster_subgenre_ami_large_only"] = _r(_ami(labels[big], [s for s, k_ in zip(sub_lab, big) if k_]), 2)
        stats["cluster_subgenre_ari_large_only"] = _r(_ari(labels[big], [s for s, k_ in zip(sub_lab, big) if k_]), 2)

        # the headline readings at other k (E28, B2): agreement, mixing, and stable clusters for a spread of cuts and for
        # every k the rule cannot tell from the configured one
        rep_k = sorted({int(x) for x in cl.get("report_k", []) if st_cfg["k_min"] <= int(x) <= st_cfg["k_max"]} | {k_chosen})
        by_k = {}
        for kk in sorted(set(rep_k) | set(range(k_near, k_chosen + 1))):
            Lk = labels if kk == k_chosen else fcluster(Z, t=kk, criterion="maxclust")
            size_k = Counter(Lk.tolist())
            jk = {c: _r(v, 2) for c, v in _cluster_jaccard(Lk, subs, sub_cuts[kk]).items()}
            row = {"k": kk, "clusters": len(size_k), "ami_subgenre": _r(_ami(Lk, sub_lab), 2), "mixed": _n_mixed(Lk, sub_codes, nS)}
            for s_ in mixed_shares:
                row[f"mixed_{int(round(100 * s_))}"] = _n_mixed(Lk, sub_codes, nS, s_)
            row["stable_any_size"] = sum(1 for v in jk.values() if v >= stable_thr)
            row["stable"] = sum(1 for c, v in jk.items() if v >= stable_thr and size_k[c] >= min_size)
            row["largest_cluster_share"] = _r(max(size_k.values()) / N, 2)
            by_k[kk] = row
        mcols = [f"mixed_{int(round(100 * s_))}" for s_ in mixed_shares]
        tables["cluster-k-sensitivity"] = {"description": f"The clustering's headline readings at other numbers of clusters. ami_subgenre: adjusted mutual information with subgenre labels. mixed: clusters holding more than one subgenre; " + "; ".join(f"{c}: clusters whose largest subgenre holds less than {c.split('_')[1]}% of their games" for c in mcols) + f". stable_any_size: clusters whose stability (best-match Jaccard, as in game-clusters) reaches {stable_thr}; stable: those that also hold at least {min_size} games. k={k_chosen} is the configured cut.",
                                           "columns": ["k", "clusters", "ami_subgenre", "mixed"] + mcols + ["stable_any_size", "stable", "largest_cluster_share"],
                                           "rows": [by_k[kk] for kk in rep_k]}
        near = [by_k[kk] for kk in range(k_near, k_chosen + 1)]
        stats["cluster_subgenre_ami_near_min"] = min(r["ami_subgenre"] for r in near)
        stats["cluster_subgenre_ami_near_max"] = max(r["ami_subgenre"] for r in near)
        stats["pct_clusters_mixed_near_min"] = _r(min(100 * r["mixed"] / r["clusters"] for r in near), 0)
        stats["pct_clusters_mixed_near_max"] = _r(max(100 * r["mixed"] / r["clusters"] for r in near), 0)
        stats["n_stable_clusters_near_min"] = min(r["stable"] for r in near)
        stats["n_stable_clusters_near_max"] = max(r["stable"] for r in near)
        for kk in rep_k:
            stats[f"cluster_subgenre_ami_k{kk}"] = by_k[kk]["ami_subgenre"]
            stats[f"n_stable_clusters_k{kk}"] = by_k[kk]["stable"]
            stats[f"pct_clusters_mixed_k{kk}"] = _r(100 * by_k[kk]["mixed"] / by_k[kk]["clusters"], 0)

        # other methods on the same distances (E10). Ward's criterion needs Euclidean distances, so it runs on a
        # classical multidimensional scaling of D (every positive eigenvalue kept; coordinates rounded so that BLAS noise
        # cannot reorder merges). Complete linkage is cut at k when its merges allow it; games sharing no mechanic sit at
        # distance 1, so its last merges tie there and the finest cut below that distance is used instead.
        J_ = np.eye(N) - 1.0 / N
        ev, evec = np.linalg.eigh(-0.5 * J_ @ (D ** 2) @ J_)
        pos = ev > 1e-9 * ev.max()
        Y = np.round(evec[:, pos] * np.sqrt(ev[pos]), 9)
        L_ward = fcluster(linkage(Y, method="ward"), t=k_chosen, criterion="maxclust")
        Zc = linkage(squareform(D, checks=False), method="complete")
        L_comp = fcluster(Zc, t=k_chosen, criterion="maxclust")
        if len(set(L_comp.tolist())) < k_chosen:
            below = Zc[:, 2][Zc[:, 2] < Zc[:, 2].max()]
            L_comp = fcluster(Zc, t=float(below.max()) if below.size else 0.0, criterion="distance")
        stats["pct_game_pairs_no_shared_mechanic"] = _r(100 * float(np.mean(D[np.triu_indices(N, 1)] >= 1.0)), 0)
        stats["cluster_mds_dims"] = int(pos.sum())
        stats["pct_mds_negative_eigen"] = _r(100 * float(-ev[ev < 0].sum() / np.abs(ev).sum()), 1)
        stats["cluster_ward_ari"] = _r(_ari(labels, L_ward), 2)
        stats["cluster_ward_ami"] = _r(_ami(labels, L_ward), 2)
        stats["cluster_ward_subgenre_ami"] = _r(_ami(L_ward, sub_lab), 2)
        stats["cluster_ward_largest_share"] = _r(Counter(L_ward.tolist()).most_common(1)[0][1] / N, 2)
        stats["cluster_complete_n"] = len(set(L_comp.tolist()))
        stats["cluster_complete_ari"] = _r(_ari(labels, L_comp), 2)
        stats["cluster_complete_ami"] = _r(_ami(labels, L_comp), 2)
        stats["cluster_complete_subgenre_ami"] = _r(_ami(L_comp, sub_lab), 2)
        stats["cluster_ward_complete_ari"] = _r(_ari(L_ward, L_comp), 2)
        # a cluster has a counterpart in another partition when its best match there reaches Jaccard 0.5 (below that,
        # Hennig counts a cluster as dissolved)
        stats["cluster_match_jaccard"] = 0.5
        for nm_, L_ in (("ward", L_ward), ("complete", L_comp)):
            stats[f"n_clusters_matched_{nm_}"] = sum(1 for v in _best_match(labels, L_).values() if v > stats["cluster_match_jaccard"])
        # consensus across k (E27): how often two games share a cluster over every subsample and every k in the range,
        # and the partition that co-association gives when cut at k
        ck0, ck1 = (int(x) for x in cl.get("consensus_k", [k_chosen, k_chosen]))
        ck0, ck1 = max(ck0, st_cfg["k_min"]), min(ck1, st_cfg["k_max"])
        cons = np.zeros((N, N))
        for bi, sb in enumerate(subs):
            Lb = np.stack([sub_cuts[kk][bi] for kk in range(ck0, ck1 + 1)])
            cons[np.ix_(sb, sb)] += (Lb[:, :, None] == Lb[:, None, :]).sum(0)
        Cons = np.where(both > 0, cons / np.maximum(both * (ck1 - ck0 + 1), 1), 0.0)
        np.fill_diagonal(Cons, 1.0)
        L_cons = fcluster(linkage(squareform(1.0 - Cons, checks=False), method="average"), t=k_chosen, criterion="maxclust")
        stats["cluster_consensus_k_min"], stats["cluster_consensus_k_max"] = ck0, ck1
        stats["cluster_consensus_ari"] = _r(_ari(labels, L_cons), 2)

        # sensitivity to the inputs (E32, D2, B2): the same method on changed mechanic sets or weights, cut at the same k
        def _recluster(gm_, cw=cl["core_weight"], idf_on=bool(cl.get("idf"))):
            Dv = _wj_distance(gm_, gids, cw, idf_on)
            return fcluster(linkage(squareform(Dv, checks=False), method="average"), t=k_chosen, criterion="maxclust")
        asserted = {m.id for m in mechs if m.data.get("status") == "asserted"}
        gm_sourced = {g: {m: r for m, r in gm[g].items() if m not in asserted} for g in gids}
        L_noass = _recluster(gm_sourced)
        stats["cluster_n_asserted_mechanics"] = len(asserted & set(mids))
        stats["cluster_pct_uses_asserted"] = _r(100 * sum(1 for g in gids for m in gm[g] if m in asserted) / max(sum(len(gm[g]) for g in gids), 1), 0)
        stats["cluster_ari_no_asserted"] = _r(_ari(labels, L_noass), 2)
        stats["cluster_subgenre_ami_no_asserted"] = _r(_ami(L_noass, sub_lab), 2)
        # coarser vocabulary: each mechanic lumped with the mechanics it specializes or requires (union of the edges)
        parent = {m: m for m in mids}
        def _find(m):
            while parent[m] != m:
                parent[m] = parent[parent[m]]
                m = parent[m]
            return m
        n_rel = 0
        for ed in sorted(edges, key=lambda e: (e.type, e.source, e.target)):
            if ed.type in ("specializes", "requires") and ed.source in parent and ed.target in parent:
                n_rel += 1
                a_, b_ = _find(ed.source), _find(ed.target)
                if a_ != b_:
                    parent[max(a_, b_)] = min(a_, b_)
        root = {m: _find(m) for m in mids}
        gm_merged = _merge_mechanics({g: gm[g] for g in gids}, root)
        L_merged = _recluster(gm_merged)
        stats["cluster_n_relation_edges"] = n_rel
        stats["cluster_n_mechanics_merged"] = len(mids) - len(set(root.values()))
        stats["cluster_ari_merged"] = _r(_ari(labels, L_merged), 2)
        stats["cluster_subgenre_ami_merged"] = _r(_ami(L_merged, sub_lab), 2)
        # random lumping: pair up rare mechanics at random within each family and merge each pair, several times
        gran = cl.get("granularity") or {}
        rare_max, reps = int(gran.get("rare_max_games", 5)), int(gran.get("random_merges", 0))
        grng = np.random.default_rng(int(gran.get("seed", st_cfg["seed"])))
        rare_by_fam = defaultdict(list)
        for m in mids:
            if prev[m] <= rare_max:
                rare_by_fam[by_id[m].data.get("family")].append(m)
        rand_aris, n_pairs = [], 0
        for _ in range(reps):
            rmap = {}
            for f_ in sorted(rare_by_fam, key=str):
                ms_ = [rare_by_fam[f_][i] for i in grng.permutation(len(rare_by_fam[f_]))]
                for a_, b_ in zip(ms_[0::2], ms_[1::2]):
                    rmap[b_] = a_
            n_pairs = len(rmap)
            rand_aris.append(_ari(labels, _recluster(_merge_mechanics({g: gm[g] for g in gids}, rmap))))
        if rand_aris:
            stats["cluster_rare_max_games"] = rare_max
            stats["cluster_random_merges"] = reps
            stats["cluster_random_merge_pairs"] = n_pairs
            stats["cluster_ari_random_merge_mean"] = _r(float(np.mean(rand_aris)), 2)
            stats["cluster_ari_random_merge_min"] = _r(float(np.min(rand_aris)), 2)
            stats["cluster_ari_random_merge_max"] = _r(float(np.max(rand_aris)), 2)
        for end, cw in (("lo", min(alts.get("core_weight", [cl["core_weight"]]))), ("hi", max(alts.get("core_weight", [cl["core_weight"]])))):
            stats[f"cluster_core_weight_{end}"] = float(cw)
            stats[f"cluster_ari_core_weight_{end}"] = _r(_ari(labels, _recluster(gm, cw=float(cw))), 2)
        stats["cluster_core_weight"] = float(cl["core_weight"])
        stats["cluster_ari_unweighted"] = _r(_ari(labels, _recluster(gm, idf_on=False)), 2)
        # does the lumped vocabulary keep the prevalence head and the lift ranking (D2)? A mechanic maps to its lump.
        pv_m = Counter(m for g in gids for m in gm_merged[g])
        top_prev = [m for m in mids if derived[m]["prevalence_rank"] <= 10]
        stats["granularity_top10_prevalence"] = len(top_prev)
        stats["granularity_top10_prevalence_kept"] = sum(1 for m in top_prev if 1 + sum(1 for v in pv_m.values() if v > pv_m[root[m]]) <= 10)
        cpair = Counter()
        for g in gids:
            for a_, b_ in combinations(sorted(gm_merged[g]), 2):
                cpair[(a_, b_)] += 1
        mrows = sorted(((c * N / (pv_m[a_] * pv_m[b_]), c, a_, b_) for (a_, b_), c in cpair.items() if c >= cfg["cooccurrence"]["min_support"]),
                       key=lambda r: (-round(r[0], 2), -r[1], r[2], r[3]))
        top_lift_m = {(a_, b_) for _, _, a_, b_ in mrows[: cfg["cooccurrence"]["top_n"]]}
        top_lift = [(r["mechanic_a"], r["mechanic_b"]) for r in tables["cooccurrence-top"]["rows"]]
        stats["granularity_top_lift"] = len(top_lift)
        stats["granularity_top_lift_kept"] = sum(1 for a_, b_ in top_lift if tuple(sorted((root[a_], root[b_]))) in top_lift_m)

        # the groupings the paper and the book name (report/analysis.yaml clustering.groupings): for each, the lowest
        # co-clustering share of any two of its games, at k and across the consensus range, and which methods put all of
        # them in one cluster (E10, E27). Listing a grouping changes no cluster.
        def _one(L_, ix):
            return len({int(L_[i]) for i in ix}) == 1
        yn = lambda ok: "yes" if ok else "no"  # noqa: E731
        grows = defaultdict(list)
        for where, gdefs in sorted((cl.get("groupings") or {}).items()):
            for slug, ids in (gdefs or {}).items():
                if not ids or any(x not in gidx for x in ids):
                    continue
                ix = [gidx[x] for x in ids]
                prs = list(combinations(ix, 2)) or [(ix[0], ix[0])]
                mco = min(_r(float(C[a_, b_]), 3) for a_, b_ in prs)
                mcons = min(_r(float(Cons[a_, b_]), 3) for a_, b_ in prs)
                avg_ok = _one(labels, ix) and mco >= st_cfg["together"]
                methods = int(avg_ok) + int(_one(L_ward, ix)) + int(_one(L_comp, ix))
                key = "grouping_" + slug.replace("-", "_")
                stats[key + "_min_cocluster"] = mco
                stats[key + "_min_consensus"] = mcons
                stats[key + "_methods"] = methods
                # the paper's test for naming a family: average linkage keeps it together and another method agrees
                stats[key + "_agreed"] = int(avg_ok and methods >= 2)
                grows[where].append({"grouping": slug.replace("-", " "), "games": list(ids), "min_cocluster": mco, "min_consensus": mcons,
                                     "average": yn(avg_ok), "ward": yn(_one(L_ward, ix)), "complete": yn(_one(L_comp, ix)), "methods": methods,
                                     "without_asserted": yn(_one(L_noass, ix)), "lumped": yn(_one(L_merged, ix))})
        for where, rows_g in grows.items():
            stats[f"n_groupings_{where}"] = len(rows_g)
            stats[f"n_groupings_{where}_agreed"] = sum(1 for r in rows_g if r["average"] == "yes" and r["methods"] >= 2)
            stats[f"n_groupings_{where}_all_methods"] = sum(1 for r in rows_g if r["methods"] == 3)
        if grows.get("paper"):
            # the families section 5.4 names, then the links it names between neighbouring families (all their games together)
            frows = [{"kind": "family", **r} for r in grows["paper"]] + [{"kind": "link", **r} for r in grows.get("links", [])]
            tables["family-robustness"] = {"description": f"Each family of games that section 5.4 names, by the games it names, then each link it names between two families (the games of both), checked against other methods and inputs. min_cocluster: the lowest share of subsamples in which any two of the games share a cluster at k={k_chosen}; min_consensus: the same over every k from {ck0} to {ck1}. average: average linkage at k={k_chosen} puts them in one cluster and min_cocluster is at least {st_cfg['together']}; ward: Ward's method on a classical scaling of the same distances, cut at k={k_chosen}, puts them in one cluster; complete: complete linkage, cut at {stats['cluster_complete_n']} clusters, does; methods: how many of the three do. without_asserted: average linkage without the asserted mechanics puts them in one cluster; lumped: average linkage does with each mechanic merged with those it specializes or requires.",
                                           "columns": ["kind", "grouping", "games", "min_cocluster", "min_consensus", "average", "ward", "complete", "methods", "without_asserted", "lumped"],
                                           "rows": frows, "link_columns": ["games"]}
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

    # ---------------- techniques: the 2019-2026 window, and whether TRL and maturity tell the same story (§7.1)
    tcfg = cfg.get("techniques") or {}
    w0 = int(tcfg.get("window_start", 2019))
    in_window = {t.id for t in techs if isinstance(t.data.get("year"), int) and t.data["year"] >= w0}
    built_on_by = defaultdict(set)
    for t in techs:
        for b in t.data.get("builds_on") or []:
            built_on_by[b].add(t.id)
    def _src_year(sid):
        s = by_id.get(sid)
        try:
            return int(str((s.data.get("date") if s else "") or "")[:4])
        except ValueError:
            return None
    pre_rows = []
    for t in techs:
        if t.id in in_window:
            derived[t.id]["window"] = f"{w0} on"
            continue
        # an older technique stays only for a reason the records show; the first that holds is named, with its evidence
        why, ev = "", []
        late_src = sorted({x for x in outgoing.get(t.id, {}).get("cites", []) if x in by_id and (_src_year(x) or 0) >= w0
                           and by_id[x].data.get("kind") != "encyclopedia"})
        if built_on_by[t.id] & in_window:
            why, ev = "built on by", sorted(built_on_by[t.id] & in_window)
        elif any(isinstance(year.get(g), int) and year[g] >= w0 for g in t.data.get("deployed_in") or []):
            why, ev = "deployed in", sorted(g for g in t.data["deployed_in"] if isinstance(year.get(g), int) and year[g] >= w0)
        elif late_src:
            why, ev = f"cites later work, from {w0} on", late_src
        derived[t.id]["window"] = f"historical exception ({why})" if why else f"before {w0}, no reason recorded"
        pre_rows.append({"technique": t.id, "year": t.data["year"], "maturity": t.data["maturity"], "reason": why or "none recorded", "evidence": ev})
    stats["technique_window_start"] = w0
    stats["n_technique_in_window"] = len(in_window)
    stats["n_technique_pre_window"] = len(pre_rows)
    stats["n_technique_pre_window_unexplained"] = sum(1 for r in pre_rows if r["reason"] == "none recorded")
    stats["n_technique_pre_window_shipped"] = sum(1 for r in pre_rows if r["maturity"].startswith("shipped"))
    for k in MATURITY_ORDER:
        stats[f"n_technique_in_window_{k.replace('-', '_')}"] = sum(1 for t in techs if t.id in in_window and t.data["maturity"] == k)
    stats["n_technique_in_window_shipped"] = sum(1 for t in techs if t.id in in_window and t.data["maturity"].startswith("shipped"))
    tables["techniques-before-window"] = {"description": f"Techniques whose key result predates {w0}, kept as historical exceptions, with the reason the records give (report/analysis.yaml, techniques.window_start).",
                                          "columns": ["technique", "year", "maturity", "reason", "evidence"], "rows": sorted(pre_rows, key=lambda r: (r["year"], r["technique"])),
                                          "link_columns": ["technique", "evidence"], "max_links": 3}
    mat_terms = vocab_terms(vocabs, "technique_maturity")
    trl_rng = tcfg.get("trl_by_maturity") or {}
    trl_text = rub["scales"]["trl"]["levels"]
    anchor_rows, outside = [], []
    for k in MATURITY_ORDER:
        lo, hi = trl_rng.get(k, [1, 9])
        ts = [t for t in techs if t.data["maturity"] == k]
        off = sorted(t.id for t in ts if not lo <= t.data["trl"] <= hi)
        outside += off
        seen = sorted({t.data["trl"] for t in ts})
        anchor_rows.append({"maturity": k, "definition": mat_terms[k]["definition"],
                            "trl_by_anchor": f"{lo}" if lo == hi else f"{lo} to {hi}",
                            "trl_anchor": f"{lo}: {str(trl_text[lo]).rstrip('.')}" + (f"; {hi}: {str(trl_text[hi]).rstrip('.')}" if hi != lo else ""),
                            "techniques": len(ts), "trl_recorded": (f"{seen[0]}" if len(seen) == 1 else f"{seen[0]} to {seen[-1]}") if seen else "",
                            "trl_outside_range": off})
    tables["technique-maturity-anchors"] = {"description": "Each deployment-maturity level with its definition (vocab/technique_maturity.yaml), the TRL levels whose anchors describe the same evidence (vocab/rubrics.yaml; mapping in report/analysis.yaml), the techniques at that level, the TRLs they carry, and any whose TRL falls outside the range.",
                                            "columns": ["maturity", "definition", "trl_by_anchor", "trl_anchor", "techniques", "trl_recorded", "trl_outside_range"],
                                            "rows": anchor_rows, "link_columns": ["trl_outside_range"]}
    stats["n_technique_trl_outside_maturity"] = len(outside)
    stats["n_technique_trl_outside_maturity_prototype"] = sum(1 for x in outside if by_id[x].data["maturity"] == "prototype")
    # what "shipped" rests on: the anchor needs one commercial game, so count the catalog deployments behind each rating
    shipped_t = [t for t in techs if t.data["maturity"].startswith("shipped")]
    ndep = {t.id: len([g for g in t.data.get("deployed_in") or [] if g in by_id]) for t in shipped_t}
    stats["n_technique_shipped_no_catalog_game"] = sum(1 for v in ndep.values() if v == 0)
    stats["n_technique_shipped_one_catalog_game"] = sum(1 for v in ndep.values() if v == 1)
    stats["n_technique_shipped_two_plus_catalog_games"] = sum(1 for v in ndep.values() if v >= 2)
    stats["n_technique_research_horizon_now"] = sum(1 for t in techs if t.data["maturity"] == "research" and t.data["horizon"] == "now")
    stats["n_technique_horizon_now"] = sum(1 for t in techs if t.data["horizon"] == "now")
    now_trl = sorted(t.data["trl"] for t in techs if t.data["horizon"] == "now")
    stats["min_trl_horizon_now"] = now_trl[0] if now_trl else None
    stats["max_trl_horizon_now"] = now_trl[-1] if now_trl else None
    # who wrote the technique and opportunity records (and so their edges, maturity judgments, and ratings): models and
    # operators of the creating runs, for the single-rater limitation in §8 and §9
    run_by = {r.id: r for r in ents.get("run", [])}
    for t_, lst_ in (("technique", techs), ("opportunity", opps)):
        made = [run_by.get((e.data.get("provenance") or {}).get("created")) for e in lst_]
        stats[f"n_models_{t_}_records"] = len({str((r.data.get("agent") or {}).get("model", "")).strip().lower() for r in made if r is not None})
        stats[f"n_operators_{t_}_records"] = len({str(r.data.get("operator", "")).strip().lower() for r in made if r is not None})

    # ---------------- exposure: the weights in print, and how far the §8 readings depend on them (review E6, E12,
    # E14, E20, E21, E22, E30). Exposure is a deployment-weighted heuristic: these checks recompute it under other
    # weights, other technique sets, other mechanic sets, and perturbed inputs. Parameters: report/analysis.yaml.
    xcfg = cfg.get("exposure") or {}
    pcfg = cfg.get("perturbation") or {}
    mat_w, eff_w = comp["maturity_weights"], comp["effect_weights"]
    eff_terms = vocab_terms(vocabs, "effect")
    wrows = [{"factor": "maturity in games", "level": mat_terms[k]["label"], "weight": mat_w[k], "count": mat_counts.get(k, 0)} for k in MATURITY_ORDER]
    wrows += [{"factor": "effect", "level": eff_terms[k]["label"], "weight": eff_w[k], "count": eff.get(k, 0)}
              for k in sorted(eff_w, key=lambda k: (-eff_w[k], k))]
    tables["exposure-weights"] = {"description": "The weights behind technique exposure, read from vocab/rubrics.yaml (composites.technique_exposure). Count is techniques for a maturity level and affects edges for an effect. A mechanic's exposure is the sum, over the techniques with an edge to it, of maturity weight times effect weight.",
                                  "columns": ["factor", "level", "weight", "count"], "rows": wrows}
    stats["w_exposure_maturity_min"], stats["w_exposure_maturity_max"] = min(mat_w.values()), max(mat_w.values())
    stats["w_exposure_effect_min"], stats["w_exposure_effect_max"] = min(eff_w.values()), max(eff_w.values())
    mech_ids = [m.id for m in mechs]
    fam_of_m = {m.id: m.data["family"] for m in mechs}
    fams_used = [f for f in fam_ids if any(fam_of_m[x] == f for x in mech_ids)]
    edges_tm = [(t.id, t.data["maturity"], a["id"], a["effect"]) for t in techs for a in t.data.get("affects", []) if a["id"] in fam_of_m]

    def _mexp(mw, ew, skip=frozenset(), merge=frozenset()):
        """Exposure per mechanic under maturity weights mw (by technique id) and effect weights ew (by effect); techniques
        in `merge` count once per mechanic, at the largest member's weight."""
        per = defaultdict(lambda: defaultdict(float))
        for tid, _, mid, e in edges_tm:
            if tid not in skip:
                per[mid][tid] += mw[tid] * ew[e]
        out = {}
        for mid in mech_ids:
            p = per.get(mid, {})
            grp = [v for k, v in p.items() if k in merge]
            out[mid] = sum(v for k, v in p.items() if k not in merge) + (max(grp) if grp else 0.0)
        return out

    def _franks(mx, drop=frozenset()):
        """Family ranks (1 = most exposed) by summed exposure and by exposure per mechanic, ties broken by family id."""
        tot, mean = {}, {}
        for f in fams_used:
            ms = [x for x in mech_ids if fam_of_m[x] == f and x not in drop]
            if ms:
                tot[f] = sum(mx[x] for x in ms)
                mean[f] = tot[f] / len(ms)
        rk = lambda v: {f: i + 1 for i, f in enumerate(sorted(v, key=lambda f: (-round(v[f], 9), f)))}  # noqa: E731
        return rk(tot), rk(mean)

    def _rho(a, b):
        ks = sorted(set(a) & set(b))
        return _r(spearmanr([a[k] for k in ks], [b[k] for k in ks])[0], 2) if len(ks) > 2 else None

    tmat = {t.id: t.data["maturity"] for t in techs}
    base_mw = {t: mat_w[m] for t, m in tmat.items()}
    one_mw = {t: 1.0 for t in tmat}
    one_ew = {e: 1.0 for e in eff_w}
    # technique-native mechanics: most of their catalog games are AI-native titles or deploy a technique that affects them
    ai_sub = xcfg.get("ai_native_subgenre", "ai-native")
    dep_on = defaultdict(set)
    for t in techs:
        for g in t.data.get("deployed_in") or []:
            dep_on[g].update(a["id"] for a in t.data.get("affects", []))
    native = set()
    for m in mechs:
        us = mech_games.get(m.id, [])
        n_ai = sum(1 for g in us if by_id[g].data.get("subgenre") == ai_sub or m.id in dep_on.get(g, ()))
        derived[m.id]["technique_native"] = bool(us) and n_ai / len(us) > float(xcfg.get("technique_native_share", 0.5))
        if derived[m.id]["technique_native"]:
            native.add(m.id)
    stats["n_mechanics_technique_native"] = len(native)
    stats["technique_native_share_pct"] = _r(100 * float(xcfg.get("technique_native_share", 0.5)), 0)
    # collapsed effects (review D4): deepens, enables-new and cuts-authoring-cost read as one effect at their edge-weighted mean
    overl = ("deepens", "enables-new", "cuts-authoring-cost")
    n_ov = sum(eff.get(k, 0) for k in overl) or 1
    col_ew = dict(eff_w)
    for k in overl:
        col_ew[k] = sum(eff_w[x] * eff.get(x, 0) for x in overl) / n_ov
    eff_col = Counter()
    for k, v in eff.items():
        eff_col["overlapping" if k in overl else k] += v
    rare_col = min(eff_col.items(), key=lambda x: (x[1], x[0]))[0]
    stats["rarest_effect_collapsed"] = eff_terms[rare_col]["label"] if rare_col in eff_terms else rare_col
    stats["n_effect_overlapping_collapsed"] = eff_col.get("overlapping", 0)
    base_mx = _mexp(base_mw, eff_w)
    base_tot, base_mean = _franks(base_mx)
    variants = {
        "equal": (_mexp(one_mw, one_ew), frozenset()),
        "maturity_only": (_mexp(base_mw, one_ew), frozenset()),
        "effect_only": (_mexp(one_mw, eff_w), frozenset()),
        "collapsed_effects": (_mexp(base_mw, col_ew), frozenset()),
        "merged_world_models": (_mexp(base_mw, eff_w, merge=frozenset(xcfg.get("merge_world_models") or [])), frozenset()),
        "no_presentation": (_mexp(base_mw, eff_w, skip=frozenset(xcfg.get("presentation_only") or [])), frozenset()),
        "classical": (base_mx, frozenset(native)),
    }
    core_f = list(xcfg.get("economic_core") or [])
    core_min = int(xcfg.get("economic_core_min_rank", 16))
    ntop = int(xcfg.get("top_families", 4))
    top_base = {f for f, r in base_tot.items() if r <= ntop}
    vr = {}
    for name, (mx, drop) in variants.items():
        tr, mr = _franks(mx, drop)
        vr[name] = (tr, mr)
        stats[f"rho_family_exposure_{name}"] = _rho(base_tot, tr)
        stats[f"rho_family_mean_exposure_{name}"] = _rho(base_mean, mr)
        stats[f"n_top_families_kept_{name}"] = len(top_base & {f for f, r in tr.items() if r <= ntop})
        stats[f"economic_core_bottom_{name}"] = int(all(mr.get(f, 0) >= core_min for f in core_f))
        stats[f"top_exposed_family_{name}"] = fam_terms[min(tr, key=tr.get)]["label"]
        stats[f"top_mean_exposed_family_{name}"] = fam_terms[min(mr, key=mr.get)]["label"]
        gone = sorted(top_base - {f for f, r in tr.items() if r <= ntop})
        stats[f"dropped_top_family_{name}"] = ", ".join(fam_terms[f]["label"] for f in gone)
    for f in core_f:
        k_ = f.replace("-", "_")
        stats[f"rank_mean_exposure_{k_}_classical"] = vr["classical"][1].get(f)
    schemes3 = ("equal", "maturity_only", "effect_only")
    stats["min_rho_family_exposure_weights"] = min(stats[f"rho_family_exposure_{s}"] for s in schemes3)
    stats["max_rho_family_exposure_weights"] = max(stats[f"rho_family_exposure_{s}"] for s in schemes3)
    stats["min_rho_family_mean_exposure_weights"] = min(stats[f"rho_family_mean_exposure_{s}"] for s in schemes3)
    stats["max_rho_family_mean_exposure_weights"] = max(stats[f"rho_family_mean_exposure_{s}"] for s in schemes3)
    others = [s_ for s_ in variants if s_ not in schemes3]
    stats["min_rho_family_exposure_other_variants"] = min(stats[f"rho_family_exposure_{s_}"] for s_ in others)
    stats["min_rho_family_mean_exposure_other_variants"] = min(stats[f"rho_family_mean_exposure_{s_}"] for s_ in others)
    stats["n_exposure_variants"] = len(variants)
    stats["n_exposure_variants_economic_core_bottom"] = sum(stats[f"economic_core_bottom_{s}"] for s in variants)
    stats["min_top_families_kept"] = min(stats[f"n_top_families_kept_{s}"] for s in variants)
    stats["n_top_families"] = ntop

    # perturbation: every maturity level moves by up to one step and every weight by up to +/- spread, per draw
    rng = np.random.default_rng(int(pcfg.get("seed", 20261031)))
    R = int(pcfg.get("draws", 1000))
    sp = float(pcfg.get("weight_spread", 0.2))
    qlo, qhi = (pcfg.get("interval") or [0.05, 0.95])
    tid_sorted = sorted(tmat)
    mat_keys = list(MATURITY_ORDER)
    eff_keys = sorted(eff_w)
    lev_ids = [m.id for m in mechs]
    lev0 = np.array([m.data["ai_leverage"] for m in mechs], dtype=float)
    prev_v = np.array([derived[x]["prevalence"] for x in lev_ids], dtype=float)
    gap_top = [r["mechanic"] for r in gap_rows[:25]]
    tot_draws, mean_draws, gap_draws = defaultdict(list), defaultdict(list), defaultdict(list)
    kept_top_fam = kept_top4 = kept_core = 0
    top_fam0 = min(base_tot, key=base_tot.get)
    for _ in range(R):
        mwp = {k: mat_w[k] * rng.uniform(1 - sp, 1 + sp) for k in mat_keys}
        ewp = {k: eff_w[k] * rng.uniform(1 - sp, 1 + sp) for k in eff_keys}
        shift = rng.integers(-1, 2, size=len(tid_sorted))
        tw = {t: mwp[mat_keys[min(max(mat_keys.index(tmat[t]) + int(s), 0), len(mat_keys) - 1)]] for t, s in zip(tid_sorted, shift)}
        mx = _mexp(tw, ewp)
        tr, mr = _franks(mx)
        for f in fams_used:
            tot_draws[f].append(tr[f])
            mean_draws[f].append(mr[f])
        kept_top_fam += min(tr, key=tr.get) == top_fam0
        kept_top4 += {f for f, r in tr.items() if r <= ntop} == top_base
        kept_core += all(mr.get(f, 0) >= core_min for f in core_f)
        lev = np.clip(lev0 + rng.integers(-1, 2, size=len(lev0)), 1, 5)
        ev = np.array([mx[x] for x in lev_ids])
        gp = lev / 5 - ev / (ev.max() or 1)
        order = sorted(range(len(lev_ids)), key=lambda i: (-round(gp[i], 9), -prev_v[i], lev_ids[i]))
        pos = {lev_ids[i]: j + 1 for j, i in enumerate(order)}
        for x in gap_top:
            gap_draws[x].append(pos[x])
    q = lambda v: (int(np.quantile(v, qlo, method="lower")), int(np.quantile(v, qhi, method="higher")))  # noqa: E731
    span = lambda a, b: f"{a}" if a == b else f"{a} to {b}"  # noqa: E731
    stats["perturbation_draws"] = R
    stats["perturbation_weight_spread_pct"] = _r(100 * sp, 0)
    stats["perturbation_interval_pct"] = _r(100 * (qhi - qlo), 0)
    stats["pct_draws_top_exposed_family_kept"] = _r(100 * kept_top_fam / R, 0)
    stats["pct_draws_top_families_kept"] = _r(100 * kept_top4 / R, 0)
    stats["pct_draws_economic_core_bottom"] = _r(100 * kept_core / R, 0)
    fe_rows = []
    edge_n = Counter(fam_of_m[mid] for _, _, mid, _ in edges_tm)
    for f in sorted(fams_used, key=lambda f: base_tot[f]):
        tr_all = [vr[s][0][f] for s in variants if f in vr[s][0]] + [base_tot[f]]
        mr_all = [vr[s][1][f] for s in variants if f in vr[s][1]] + [base_mean[f]]
        fe_rows.append({"family": f, "edges": edge_n.get(f, 0), "rank": base_tot[f], "rank_by_edges": vr["equal"][0][f],
                        "rank_across_variants": span(min(tr_all), max(tr_all)), "rank_interval": span(*q(tot_draws[f])),
                        "mean_rank": base_mean[f], "mean_rank_across_variants": span(min(mr_all), max(mr_all)),
                        "mean_rank_interval": span(*q(mean_draws[f]))})
    tables["family-exposure-sensitivity"] = {
        "description": "Family exposure ranks (1 = most exposed) under the stated weights, by unweighted affects edges, across seven variants (equal weights, maturity only, effect only, the three overlapping effects collapsed, related world models merged, presentation-only techniques removed, technique-native mechanics removed), and as the "
                       f"{_r(100 * qlo, 0):g}th to {_r(100 * qhi, 0):g}th percentile over {R} seeded draws that move every maturity level by up to one step and every weight by up to {_r(100 * sp, 0):g} percent. Rank is by summed exposure; mean rank by exposure per mechanic.",
        "columns": ["family", "edges", "rank", "rank_by_edges", "rank_across_variants", "rank_interval", "mean_rank", "mean_rank_across_variants", "mean_rank_interval"],
        "rows": fe_rows}

    # where the techniques reach: the share of uses left unreached under other denominators (review E12, E14)
    def _pct(ms, w):
        tot_ = sum(w(x) for x in ms) or 1
        return _r(100 * sum(w(x) for x in ms if base_mx[x] == 0) / tot_, 0)
    core_n = Counter(mid for g in games for mid, r in gm[g.id].items() if r == "core")
    use_w = lambda x: derived[x]["prevalence"]  # noqa: E731
    iface_f = set(cfg.get("nonstate_families") or [])  # the families §5.1 leaves out of the head of the distribution (review E37)
    stats["pct_mechanics_zero_exposure"] = _r(100 * stats["n_mechanics_zero_exposure"] / max(len(mechs), 1), 0)
    stats["pct_core_uses_on_zero_exposure"] = _pct(mech_ids, lambda x: core_n.get(x, 0))
    stats["pct_supporting_uses_on_zero_exposure"] = _pct(mech_ids, lambda x: use_w(x) - core_n.get(x, 0))
    stats["n_core_uses"] = sum(core_n.values())
    non_if = [x for x in mech_ids if fam_of_m[x] not in iface_f]
    stats["pct_uses_on_zero_exposure_excl_interface"] = _pct(non_if, use_w)
    stats["pct_core_uses_on_zero_exposure_excl_interface"] = _pct(non_if, lambda x: core_n.get(x, 0))
    stats["n_mechanics_zero_exposure_excl_interface"] = sum(1 for x in non_if if base_mx[x] == 0)
    stats["n_mechanics_excl_interface"] = len(non_if)
    stats["n_interface_families"] = len(iface_f)
    top10_ids = {m.id for m in top10}
    stats["pct_uses_on_zero_exposure_excl_top10"] = _pct([x for x in mech_ids if x not in top10_ids], use_w)
    stats["pct_uses_on_zero_exposure_classical"] = _pct([x for x in mech_ids if x not in native], use_w)
    un_rows = []
    for f in fams_used:
        ms = [x for x in mech_ids if fam_of_m[x] == f]
        un_rows.append({"family": f, "mechanics": len(ms), "unreached": sum(1 for x in ms if base_mx[x] == 0),
                        "uses": sum(use_w(x) for x in ms), "pct_uses_unreached": _pct(ms, use_w),
                        "core_uses": sum(core_n.get(x, 0) for x in ms), "pct_core_unreached": _pct(ms, lambda x: core_n.get(x, 0))})
    un_rows.sort(key=lambda r: (-r["pct_uses_unreached"], -r["uses"], r["family"]))
    tables["family-unreached"] = {"description": "Per mechanic family: mechanics with no affects edge from any technique in the set (unreached), and the share of the family's game uses, and of its core uses, that fall on them. Sorted by the share of uses unreached.",
                                  "columns": ["family", "mechanics", "unreached", "uses", "pct_uses_unreached", "core_uses", "pct_core_unreached"], "rows": un_rows}
    # the most exposed mechanics with and without the technique-native ones
    cl_rank = {r["mechanic"]: i + 1 for i, r in enumerate(x for x in exp_rows if x["mechanic"] not in native)}
    for r in tables["most-exposed-mechanics"]["rows"]:
        r["technique_native"] = "yes" if r["mechanic"] in native else ""
        r["rank_without_native"] = cl_rank.get(r["mechanic"], "")
        r["technique_exposure"] = _r(r["technique_exposure"], 1)
    tables["most-exposed-mechanics"]["columns"] = ["mechanic", "family", "technique_exposure", "technique_count", "prevalence", "technique_native", "rank_without_native"]
    tables["most-exposed-mechanics"]["description"] = (f"Mechanics most affected by the technique set, exposure shown to one decimal. Technique-native: more than {_r(100 * float(xcfg.get('technique_native_share', 0.5)), 0):g} percent of the catalog games that use it are AI-native titles or deploy a technique that affects it. "
                                                       "Rank without native: the order once technique-native mechanics are set aside.")
    for x in ("utility-action-selection", "rigid-body-physics", "direct-avatar", "procedural-terrain"):
        if x in cl_rank:
            stats[f"rank_without_native_{x.replace('-', '_')}"] = cl_rank[x]
    # leverage gap: shown to one decimal, with how many rows tie and where each row lands under perturbed inputs
    if gap_rows:
        stats["n_leverage_gap_tied_top"] = sum(1 for r in gap_rows if r["gap"] == gap_rows[0]["gap"])
        stats["n_leverage_gap_tied_top_shown"] = sum(1 for r in gap_rows if _r(r["gap"], 1) == _r(gap_rows[0]["gap"], 1))
    for r in tables["leverage-gap"]["rows"]:
        r["rank_interval"] = span(*q(gap_draws[r["mechanic"]])) if r["mechanic"] in gap_draws else ""
        r["gap"] = _r(r["gap"], 1)
        r["technique_exposure"] = _r(r["technique_exposure"], 1)
    tables["leverage-gap"]["columns"] = ["mechanic", "family", "ai_leverage", "technique_exposure", "prevalence", "gap", "rank_interval"]
    tables["leverage-gap"]["description"] += (f" Gap and exposure are shown to one decimal; rank interval is the {_r(100 * qlo, 0):g}th to {_r(100 * qhi, 0):g}th percentile of the row's place over {R} seeded draws that move each AI leverage score and each technique's maturity by up to one step and every weight by up to {_r(100 * sp, 0):g} percent.")
    for tbl in ("family-summary", "family-mean-exposure"):
        for r in tables[tbl]["rows"]:
            r["technique_exposure"] = _r(r["technique_exposure"], 1)
        tables[tbl]["description"] += " Summed exposure is shown to one decimal and exposure per mechanic to two, so a small nonzero mean stays distinct from none; rows are ordered by the unrounded values."
    # explanation edges, by technique (review E4)
    ex_by = defaultdict(list)
    for t in techs:
        for a in t.data.get("affects", []):
            if a["effect"] == "explains":
                ex_by[t.id].append(a["id"])
    ex_rows = sorted(({"technique": k, "maturity": tmat[k], "edges": len(v), "mechanics": sorted(v)} for k, v in ex_by.items()),
                     key=lambda r: (-r["edges"], r["technique"]))
    tables["explains-edges"] = {"description": "Every affects edge coded as explains, by technique.", "columns": ["technique", "maturity", "edges", "mechanics"],
                                "rows": ex_rows, "link_columns": ["technique", "mechanics"]}
    if ex_rows:
        stats["n_effect_explains_top_technique"] = ex_rows[0]["edges"]
        stats["explains_top_technique"] = ex_rows[0]["technique"]

    # ---------------- opportunities ranked
    orows = sorted(({"opportunity": o.id, "type": o.data["opportunity_type"], "priority": derived[o.id]["priority"], "impact": o.data["impact"],
                     "feasibility": o.data["feasibility"], "novelty": o.data["novelty"], "horizon": o.data["horizon"]} for o in opps),
                   key=lambda r: (-r["priority"], r["opportunity"]))
    tables["opportunities-ranked"] = {"description": "Opportunities by composite priority (weighted geometric mean of impact, feasibility, novelty; weights in vocab/rubrics.yaml).",
                                      "columns": ["opportunity", "type", "priority", "impact", "feasibility", "novelty", "horizon"], "rows": orows, "link_columns": ["opportunity"]}
    if orows:
        stats["top_opportunity"] = by_id[orows[0]["opportunity"]].data["name"]
    # ---------------- opportunity priority in print, its ties, its stability, and the evidence behind each rating
    # (review E16, E19, E22, E24, E25, E31). Ratings are one rater's; these checks say how much the order depends on them.
    ocfg = cfg.get("opportunities") or {}
    pc = rub["composites"]["opportunity_priority"]
    pw = pc["weights"]
    rated = [k.removeprefix("w_") for k in pw]
    tables["priority-weights"] = {"description": f"The weights of the priority composite, read from vocab/rubrics.yaml (composites.opportunity_priority): priority = {pc['formula']}, a weighted geometric mean on the 1 to 5 scale of the three ratings.",
                                  "columns": ["rating", "weight", "question"],
                                  "rows": [{"rating": k, "weight": pw["w_" + k], "question": rub["scales"][k]["question"]} for k in rated]}
    for k in rated:
        stats[f"w_priority_{k}"] = pw["w_" + k]
    pv = Counter(r["priority"] for r in orows)
    stats["n_opportunity_priority_values"] = len(pv)
    stats["n_opportunity_priority_tied"] = sum(n for n in pv.values() if n > 1)
    topn = int(pcfg.get("top_n", 8))
    stats["opportunity_top_n"] = topn
    top_ids = [r["opportunity"] for r in orows[:topn]]
    rng_o = np.random.default_rng(int(pcfg.get("seed", 20261031)) + 1)
    oids = [r["opportunity"] for r in orows]
    sc0 = np.array([[by_id[x].data[k] for k in rated] for x in oids], dtype=float)
    wv0 = np.array([pw["w_" + k] for k in rated], dtype=float)
    o_ranks, overlap, first_kept = defaultdict(list), [], 0
    for _ in range(R):
        sc = np.clip(sc0 + rng_o.integers(-1, 2, size=sc0.shape), 1, 5)
        wv = wv0 * rng_o.uniform(1 - sp, 1 + sp, size=len(wv0))
        pr = np.exp(np.log(sc) @ (wv / wv.sum()))
        order = sorted(range(len(oids)), key=lambda i: (-round(pr[i], 9), oids[i]))
        for j, i in enumerate(order):
            o_ranks[oids[i]].append(j + 1)
        overlap.append(len(set(top_ids) & {oids[i] for i in order[:topn]}))
        first_kept += oids[order[0]] == oids[0]
    for r in orows:
        rk_ = o_ranks[r["opportunity"]]
        r["rank_interval"] = span(*q(rk_))
        r["top_share"] = _r(100 * sum(1 for v in rk_ if v <= topn) / R, 0)
        derived[r["opportunity"]]["top_share"] = r["top_share"]
    stats["pct_draws_top_opportunity_first"] = _r(100 * first_kept / R, 0)
    stats["mean_top_opportunities_kept"] = _r(float(np.mean(overlap)), 1) if overlap else None
    stats["n_top_opportunities_majority"] = sum(1 for r in orows[:topn] if r["top_share"] >= 50)
    stats["n_opportunities_outside_top_majority"] = sum(1 for r in orows[topn:] if r["top_share"] >= 50)
    # what each opportunity's techniques have shown in games: the weakest and the best maturity it lists, whether any
    # of them has a published edge to the mechanics it involves, and whether its horizon is earlier than all of theirs
    hz_order = list(vocab_terms(vocabs, "horizon"))
    caps = ocfg.get("feasibility_cap_by_best_maturity") or {}
    ev_rows = []
    budget_re = re.compile(str(ocfg.get("budget_pattern", r"tokens? per|\bms\b|first token|VRAM|frame-time|player-hour")), re.I)
    for r in orows:
        o = by_id[r["opportunity"]]
        ts = [by_id[t] for t in o.data.get("applies") or [] if t in by_id]
        mi = lambda t: MATURITY_ORDER.index(t.data["maturity"])  # noqa: E731
        weak = min(ts, key=lambda t: (mi(t), t.data["trl"], t.id)) if ts else None
        best = max(ts, key=lambda t: (mi(t), t.data["trl"], t.id)) if ts else None
        inv = o.data.get("involves") or []
        linked = sum(1 for m in inv if any(m in reach.get(t.id, ()) for t in ts))
        early = bool(ts) and hz_order.index(o.data["horizon"]) < min(hz_order.index(t.data["horizon"]) for t in ts)
        flags = (["no published edge"] if ts and linked == 0 else []) + (["dated before every listed technique"] if early else [])
        cap = caps.get(best.data["maturity"], 5) if best else 5
        rt_model = any({"client-realtime", "server-realtime"} & set(t.data["runtime"]) and {"compute-cost", "latency"} & set(t.data.get("risks") or []) for t in ts)
        derived[o.id].update({"weakest_technique": weak.id if weak else None, "mechanics_reached": linked,
                              "horizon_before_techniques": early, "feasibility_cap": cap, "runtime_model": rt_model,
                              "states_compute_budget": bool(budget_re.search(o.data.get("validation_experiment", "")))})
        ev_rows.append({"opportunity": o.id, "horizon": o.data["horizon"], "feasibility": o.data["feasibility"],
                        "weakest_technique": weak.id if weak else "", "weakest_maturity": mat_terms[weak.data["maturity"]]["label"] if weak else "",
                        "weakest_trl": weak.data["trl"] if weak else "", "best_maturity": mat_terms[best.data["maturity"]]["label"] if best else "",
                        "mechanics_reached": f"{linked} of {len(inv)}", "flags": "; ".join(flags)})
    tables["opportunity-evidence"] = {"description": "For each opportunity, in priority order: the least mature technique it applies (maturity in games and TRL), the most mature one, how many of the mechanics it involves have an affects edge from any of its techniques, and flags for an opportunity none of whose mechanics has such an edge, or whose horizon is earlier than every technique it lists.",
                                      "columns": ["opportunity", "horizon", "feasibility", "weakest_technique", "weakest_maturity", "weakest_trl", "best_maturity", "mechanics_reached", "flags"],
                                      "rows": ev_rows, "link_columns": ["opportunity", "weakest_technique"]}
    stats["n_opportunity_no_published_edge"] = sum(1 for o in opps if derived[o.id]["mechanics_reached"] == 0)
    stats["n_opportunity_horizon_before_techniques"] = sum(1 for o in opps if derived[o.id]["horizon_before_techniques"])
    stats["n_opportunity_best_research"] = sum(1 for r in ev_rows if r["best_maturity"] == mat_terms["research"]["label"])
    stats["n_opportunity_weakest_research"] = sum(1 for r in ev_rows if r["weakest_maturity"] == mat_terms["research"]["label"])
    # feasibility read against the best technique's maturity in games (anchor 4 asks for known techniques): cap it and re-rank
    capped = {o.id: min(o.data["feasibility"], derived[o.id]["feasibility_cap"]) for o in opps}
    stats["n_opportunity_feasibility_capped"] = sum(1 for o in opps if capped[o.id] < o.data["feasibility"])
    for k_ in ("research", "prototype"):
        stats[f"feasibility_cap_{k_}"] = caps.get(k_)
    if len(orows) > 1:   # the leader's margin: its priority one feasibility point lower, beside the runner-up's (both to one decimal)
        o1 = by_id[orows[0]["opportunity"]].data
        stats["priority_top_opportunity_feasibility_minus_one"] = _r((o1["impact"] ** pw["w_impact"]) * (max(o1["feasibility"] - 1, 1) ** pw["w_feasibility"])
                                                                     * (o1["novelty"] ** pw["w_novelty"]), 1)
        stats["priority_second_opportunity"] = _r(orows[1]["priority"], 1)
    cap_pr = {o.id: (o.data["impact"] ** pw["w_impact"]) * (capped[o.id] ** pw["w_feasibility"]) * (o.data["novelty"] ** pw["w_novelty"]) for o in opps}
    cap_order = sorted(cap_pr, key=lambda x: (-round(cap_pr[x], 9), x))
    for i, x in enumerate(cap_order):
        derived[x]["rank_feasibility_capped"] = i + 1
    stats["n_top_opportunities_kept_feasibility_capped"] = len(set(top_ids) & set(cap_order[:topn]))
    stats["n_top_opportunities_feasibility_capped"] = sum(1 for x in top_ids if capped[x] < by_id[x].data["feasibility"])
    # §9.1's reading of the top of the list, checked: how many apply a frame-generating world model, and how many list a
    # technique that has shipped in a game
    wm_set = set(xcfg.get("merge_world_models") or [])
    stats["n_top_opportunities_world_model"] = sum(1 for x in top_ids if wm_set & set(by_id[x].data.get("applies") or []))
    stats["n_opportunities_world_model"] = sum(1 for o in opps if wm_set & set(o.data.get("applies") or []))
    stats["n_top_opportunities_best_shipped"] = sum(1 for x in top_ids if any(str(by_id[t].data.get("maturity", "")).startswith("shipped")
                                                                              for t in by_id[x].data.get("applies") or [] if t in by_id))
    # runtime cost (review E25): Now-horizon opportunities that call a model during play, and whether their records state a budget
    now_rt = [o for o in opps if o.data["horizon"] == "now" and derived[o.id]["runtime_model"]]
    stats["n_opportunity_now_runtime_model"] = len(now_rt)
    stats["n_opportunity_now_runtime_model_budget"] = sum(1 for o in now_rt if derived[o.id]["states_compute_budget"])
    # what a resolution would show (review F1, F4): each prediction's criteria end in one sentence "Technique class: ..., so
    # this is a technique test" or "... a feature test". A technique test is one that only the technique class the
    # opportunity applies can meet; a feature test is one that classical, symbolic, or operations-research methods can meet
    # too, so its confirmation shows the feature shipped. A criterion with no such sentence, or more than one, is counted
    # unclassified, and section 11 asserts there are none, so a new prediction must say which kind it is.
    test_re = re.compile(r"Technique class: [^.]*?\bso this is an? (technique|feature) test\b")
    kinds = Counter()
    for o in opps:
        c = str(o.data["falsifiable_signal"].get("criteria", ""))
        found = test_re.findall(c)
        kind = found[0] if len(found) == 1 and c.count("Technique class:") == 1 else "unclassified"
        derived[o.id]["prediction_test"] = kind
        kinds[kind] += 1
    stats["n_predictions_technique_test"] = kinds["technique"]
    stats["n_predictions_feature_test"] = kinds["feature"]
    stats["n_predictions_unclassified"] = kinds["unclassified"]
    # displayed to one decimal: three ordinal ratings do not support more (review E22); rows keep their unrounded order
    for r in orows:
        r["priority"] = _r(r["priority"], 1)
        derived[r["opportunity"]]["priority_shown"] = r["priority"]
    tables["opportunities-ranked"]["columns"] = ["opportunity", "type", "priority", "impact", "feasibility", "novelty", "horizon", "rank_interval", "top_share"]
    tables["opportunities-ranked"]["description"] = (
        "Opportunities by composite priority (weighted geometric mean of impact, feasibility, and novelty; weights in vocab/rubrics.yaml), shown to one decimal; rows are ordered by the unrounded value. "
        f"Rank interval: the {_r(100 * qlo, 0):g}th to {_r(100 * qhi, 0):g}th percentile of the opportunity's rank over {R} seeded draws that move each rating by up to one anchor and each weight by up to {_r(100 * sp, 0):g} percent. "
        f"Top share: the percentage of those draws in which it ranks in the top {topn}.")
    stats["n_predictions"] = len(opps)
    res = sorted(o.data["falsifiable_signal"]["resolve_by"] for o in opps)
    stats["first_prediction_resolves"] = res[0] if res else None
    if res:
        stats["first_prediction_resolves_long"], stats["first_prediction_resolves_spoken"] = written_dates(res[0])
        # whole calendar years from the paper's release (report/meta.yaml date) to the first and the last resolve-by date
        year0 = int(str(read_yaml(ROOT / "report" / "meta.yaml")["date"])[:4])
        stats["years_to_first_prediction"] = int(str(res[0])[:4]) - year0
        stats["years_to_last_prediction"] = int(str(res[-1])[:4]) - year0
    outcomes = Counter()
    for o in opps:
        r = o.data["falsifiable_signal"].get("resolution")
        derived[o.id]["prediction_status"] = r["outcome"] if r else "open"
        outcomes[r["outcome"] if r else "open"] += 1
    for k in ["open"] + list(vocab_terms(vocabs, "prediction_outcome")):
        stats[f"n_predictions_{k}"] = outcomes.get(k, 0)

    # ---------------- raters: agreement between independent ratings, and calibration results
    runs = {r.id: r for r in ents.get("run", [])}
    pair_stats = defaultdict(lambda: {"scores": 0, "pairs": 0, "exact": 0, "within_one": 0, "units": [], "ordered": []})
    n_ratings = 0
    rated_mechs: set[str] = set()
    for t in ("mechanic", "game", "technique", "opportunity"):
        for e in sorted(live.get(t, []), key=lambda e: e.id):
            per = defaultdict(list)
            for r in e.data.get("ratings") or []:
                per[r["field"]].append(r)
                n_ratings += 1
            created_id = (e.data.get("provenance") or {}).get("created")
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
                    ag["units"].append([r["value"] for r in rs])
                    # each independent pair as (first, second): the creating run's original score first, else the earlier run's
                    ag["ordered"] += [(x["value"], y["value"]) if x["run"] == created_id or (y["run"] != created_id and x["run"] <= y["run"])
                                      else (y["value"], x["value"]) for x, y in ps]
    # chance-corrected agreement (review findings D8, D16, E23): Krippendorff's alpha with the ordinal metric over every rating
    # of a rated field, with a bootstrap over the rated records; quadratic-weighted kappa, as calibration-results reports; the
    # rank correlation between first and second ratings; the second rater's mean shift; and how many second ratings sit below
    # or above the first. Exact agreement and alpha can be low while the ranks agree: a rater who reads every anchor one level
    # higher orders the records the same way and never picks the same anchor. A resample whose ratings all sit on one anchor
    # has no alpha (nothing varies to agree on) and is left out of the interval. Ten records per field make wide intervals.
    rrng = np.random.default_rng(boot_seed + 1)
    agree_rows, confusion = [], []
    for f, v in sorted(pair_stats.items()):
        K = max(max(u) for u in v["units"])
        Cu = np.array([_coincidence(u, K) for u in v["units"]])
        draw = rrng.integers(0, len(Cu), (n_boot, len(Cu)))
        W = np.zeros((n_boot, len(Cu)))
        np.add.at(W, (np.arange(n_boot)[:, None], draw), 1)
        ba = _alpha_ordinal(np.einsum("bu,ukl->bkl", W, Cu))
        ba = ba[np.isfinite(ba)]
        first, second = (np.array(c, float) for c in zip(*v["ordered"]))
        row = {"field": f, "scores": v["scores"], "pairs": v["pairs"], "exact": _r(v["exact"] / v["pairs"], 2), "within_one": _r(v["within_one"] / v["pairs"], 2),
               "kappa": _r(_kappa_quadratic(first, second, K), 2), "alpha": _r(_alpha_ordinal(Cu.sum(0)), 2),
               "alpha_low": _r(np.percentile(ba, q_lo), 2) if len(ba) else None, "alpha_high": _r(np.percentile(ba, q_hi), 2) if len(ba) else None,
               "rank_rho": _r(_spearman(first, second), 2), "shift": _r(float(np.mean(second - first)), 1)}
        for k in ("kappa", "alpha", "alpha_low", "alpha_high", "shift"):
            stats[f"{k}_rater_{f}"] = row[k]
        stats[f"rho_raters_{f}"] = row["rank_rho"]
        stats[f"n_rater_lower_{f}"] = int(np.sum(second < first))
        stats[f"n_rater_higher_{f}"] = int(np.sum(second > first))
        agree_rows.append(row)
        for (x, y), n in sorted(Counter(v["ordered"]).items()):
            confusion.append({"field": f, "first": x, "second": y, "scores": n})
    mech_alpha = [r["alpha"] for r in agree_rows if (rub["scales"].get(r["field"]) or {}).get("applies_to") == "mechanic" and r["alpha"] is not None]
    if mech_alpha:
        stats["alpha_rater_min"], stats["alpha_rater_max"] = min(mech_alpha), max(mech_alpha)
    tables["rater-confusion"] = {"description": "For each field with independent ratings, how often each pair of anchors was chosen: first is the original score "
                                                "(the creating run's), second the independent rating. Rows with no scores are omitted.",
                                 "columns": ["field", "first", "second", "scores"], "rows": confusion}
    stats["n_ratings"] = n_ratings
    # how many raters stand behind the second ratings: distinct runs rating a record their own run did not create
    stats["n_rating_runs"] = len({r["run"] for t in ("mechanic", "game", "technique", "opportunity") for e in live.get(t, [])
                                  for r in e.data.get("ratings") or [] if r["run"] != (e.data.get("provenance") or {}).get("created")})
    # how far the second ratings reach, and how often independent raters agree on each scale (chapter 5)
    stats["n_mechanics_independently_rated"] = len(rated_mechs)
    for f, v in sorted(pair_stats.items()):
        stats[f"pct_rater_exact_{f}"] = int(round(100 * v["exact"] / v["pairs"]))
        stats[f"pct_rater_within_one_{f}"] = int(round(100 * v["within_one"] / v["pairs"]))
    stats["n_scores_independently_rated"] = sum(v["scores"] for v in pair_stats.values())
    stats["n_mechanic_scores"] = sum(1 for m in mechs for f, s in rub["scales"].items() if s.get("applies_to") == "mechanic" and m.data.get(f) is not None)
    n_mech_rated = sum(v["scores"] for f, v in pair_stats.items() if (rub["scales"].get(f) or {}).get("applies_to") == "mechanic")
    stats["pct_mechanic_scores_independently_rated"] = _r(100 * n_mech_rated / max(stats["n_mechanic_scores"], 1), 0)
    # robustness of the legibility-emergence correlation (§5.6): on the mechanics where both fields carry the creating
    # run's original rating and a rating from a run independent of it, the correlation under each rater's scores. Several
    # independent ratings of one field are reduced to their lower median, as a stored score is.
    pair_fields = ("legibility", "emergence_potential")
    orig_sc, second_sc = [], []
    for m in mechs:
        created = runs.get((m.data.get("provenance") or {}).get("created"))
        rs = m.data.get("ratings") or []
        o = {f: [r["value"] for r in rs if r["field"] == f and created is not None and r["run"] == created.id] for f in pair_fields}
        s = {f: [r["value"] for r in rs if r["field"] == f and independent(runs.get(r["run"]), created)] for f in pair_fields}
        if all(o[f] for f in pair_fields) and all(s[f] for f in pair_fields):
            orig_sc.append(tuple(o[f][0] for f in pair_fields))
            second_sc.append(tuple(lower_median(s[f]) for f in pair_fields))
    stats["n_mechanics_second_rated_legibility_emergence"] = len(second_sc)
    for key, sc in (("second_rater", second_sc), ("original_rater", orig_sc)):
        r = p = None
        if len(sc) >= 5 and all(len({x[i] for x in sc}) > 1 for i in range(2)):
            r, p = spearmanr([x[0] for x in sc], [x[1] for x in sc])
        stats[f"rho_legibility_emergence_potential_{key}"] = _r(r, 2)
        stats[f"p_legibility_emergence_potential_{key}"] = _r(p, 3)
    # the same mechanics' stored legibility and emergence potential (the lower median), and the two other ways of combining
    # two ratings that review finding D10 asks about: their mean, and the upper of the two
    combos = {"stored": [], "mean": [], "upper": []}
    for m in mechs:
        rs = m.data.get("ratings") or []
        v = {f: [r["value"] for r in rs if r["field"] == f] for f in pair_fields}
        if all(len(v[f]) > 1 for f in pair_fields):
            combos["stored"].append(tuple(m.data[f] for f in pair_fields))
            combos["mean"].append(tuple(float(np.mean(v[f])) for f in pair_fields))
            combos["upper"].append(tuple(max(v[f]) for f in pair_fields))
    for key, sc in combos.items():
        ok = len(sc) >= 5 and all(len({x[i] for x in sc}) > 1 for i in range(2))
        stats[f"rho_legibility_emergence_potential_{key}_rated"] = _r(spearmanr([x[0] for x in sc], [x[1] for x in sc])[0], 2) if ok else None
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
    # The calibration set as a second, larger comparison (§5.6): its frozen scores are the original rater's, and each calibrated
    # run independent of a mechanic's creating run scored it blind from the sheet, by that run's own account (the frozen
    # scores are public). Per scale, ordinal alpha over the frozen score and every such run's score, and the mean shift; then
    # the legibility-emergence correlation under the frozen scores and under the independent runs' lower median. The set was
    # chosen to span the anchors, which widens each scale's range, and a rater reaches it only by passing, so these numbers
    # compare the two raters on the same mechanics and are not estimates for the full vocabulary.
    cal_scores = {mid: [] for mid in (cal or {}).get("mechanics") or {}}
    for r in sorted(runs.values(), key=lambda r: r.id):
        for mid, sc in (((r.data.get("calibration") or {}).get("scores")) or {}).items():
            m = by_id.get(mid)
            if mid in cal_scores and m is not None and independent(r, runs.get((m.data.get("provenance") or {}).get("created"))):
                cal_scores[mid].append(sc)
    cal_rated = sorted(mid for mid, scs in cal_scores.items() if scs)
    stats["n_calibration_mechanics_second_rated"] = len(cal_rated)
    if len(cal_rated) >= 5:
        gold = cal["mechanics"]
        cal_alpha = {}
        for f in CALIBRATION_SCALES:
            units = [[gold[mid][f]] + [s[f] for s in cal_scores[mid] if isinstance(s.get(f), int)] for mid in cal_rated]
            units = [u for u in units if len(u) > 1]
            if units:
                K = max(max(u) for u in units)
                cal_alpha[f] = _r(_alpha_ordinal(sum(_coincidence(u, K) for u in units)), 2)
                stats[f"alpha_calibration_{f}"] = cal_alpha[f]
                stats[f"shift_calibration_{f}"] = _r(float(np.mean([x - u[0] for u in units for x in u[1:]])), 1)
        for row in agree_rows:
            row["calibration_alpha"] = cal_alpha.get(row["field"])
        if cal_alpha:
            stats["alpha_calibration_min"], stats["alpha_calibration_max"] = min(cal_alpha.values()), max(cal_alpha.values())
        sec = {mid: tuple(lower_median([s.get(f) for s in cal_scores[mid]]) for f in pair_fields) for mid in cal_rated}
        both = [mid for mid in cal_rated if None not in sec[mid]]
        stats["rho_legibility_emergence_potential_calibration_original"] = _r(_spearman([gold[mid][pair_fields[0]] for mid in both], [gold[mid][pair_fields[1]] for mid in both]), 2)
        stats["rho_legibility_emergence_potential_calibration_second"] = _r(_spearman([sec[mid][0] for mid in both], [sec[mid][1] for mid in both]), 2)
    tables["rater-agreement"] = {
        "description": "Agreement between ratings from independent runs (different operator, and different model for agent runs), per scored field. A field "
                       "appears once a second rater has scored it (tasks/rate-scores.md). Exact and within one are shares of rating pairs; kappa is "
                       "quadratic-weighted; alpha is Krippendorff's alpha with the ordinal metric, with alpha low and high bounding a "
                       f"{round(q_hi - q_lo)}% bootstrap interval over the rated records ({n_boot} resamples); rank rho is the Spearman correlation "
                       "between the original and the independent rating; shift is the independent rating minus the original, on average; calibration "
                       "alpha is the same alpha on the calibration set, between its frozen scores and the independent raters who scored it from the score-free sheet. "
                       "Counts per anchor pair are in rater-confusion.csv.",
        "columns": ["field", "scores", "pairs", "exact", "within_one", "kappa", "alpha", "alpha_low", "alpha_high", "rank_rho", "shift", "calibration_alpha"],
        "rows": [{**r, "calibration_alpha": r.get("calibration_alpha")} for r in agree_rows]}

    # ---------------- second coder: agreement on family, admission, and effect codes (review D3, D4, D6; _second_coding)
    _second_coding(ents, vocabs, cfg, stats, tables)

    # ---------------- adoption over time
    by_decade = Counter()
    for m in mechs:
        y = derived[m.id]["earliest_year"]
        if y:
            by_decade[f"{(y // 10) * 10}s"] += 1
    tables["mechanic-origins-by-decade"] = {"description": "Mechanics by decade of earliest appearance in the dataset. The catalog is a sample, so that year is an upper bound on when a mechanic originated: it is at least that old.",
                                            "columns": ["decade", "mechanics"], "rows": [{"decade": k, "mechanics": v} for k, v in sorted(by_decade.items())]}
    late = sorted((m for m in mechs if (derived[m.id]["earliest_year"] or 0) >= 2010),
                  key=lambda m: (m.data["family"], derived[m.id]["earliest_year"], m.id))
    # where a lineage enters the catalog late, its first catalog game takes the credit for parts its unsampled ancestors
    # may have had: each row names the subgenre of the first game and the year the catalog's first game of that subgenre came out
    sub_first = {}
    for g in games:
        if isinstance(year.get(g.id), int):
            s_ = g.data.get("subgenre")
            sub_first[s_] = min(sub_first.get(s_, 9999), year[g.id])
    late_sub = {m.id: by_id[derived[m.id]["earliest_game"]].data.get("subgenre") for m in late}
    tables["mechanics-since-2010"] = {"description": "Mechanics whose earliest appearance in the dataset is 2010 or later, grouped by family. "
                                                     "Subgenre is the earliest game's; sampled from is the release year of the catalog's first game in that subgenre.",
                                      "columns": ["family", "mechanic", "earliest_year", "earliest_game", "subgenre", "sampled_from"],
                                      "rows": [{"family": fam_terms[m.data["family"]]["label"], "mechanic": m.id,
                                                "earliest_year": derived[m.id]["earliest_year"], "earliest_game": derived[m.id]["earliest_game"],
                                                "subgenre": sub_terms.get(late_sub[m.id], {}).get("label", late_sub[m.id]),
                                                "sampled_from": sub_first.get(late_sub[m.id])} for m in late],
                                      "link_columns": ["mechanic", "earliest_game"]}
    stats["n_mechanics_since_2010"] = len(late)
    stats["n_mechanics_since_2010_late_subgenre"] = sum(1 for m in late if sub_first.get(late_sub[m.id], 0) >= 2010)
    stats["year_first_grand_strategy"] = sub_first.get("grand-strategy")
    stats["n_mechanics_since_2010_grand_strategy"] = sum(1 for m in late if late_sub[m.id] == "grand-strategy")
    stats["n_subgenres_sampled_from_2010"] = sum(1 for y in sub_first.values() if y >= 2010)
    total_dated = sum(by_decade.values())
    stats["pct_mechanics_first_seen_1980_1999"] = _r(100 * (by_decade.get("1980s", 0) + by_decade.get("1990s", 0)) / total_dated, 0) if total_dated else None
    stats["peak_origin_decade"] = max(by_decade.items(), key=lambda x: (x[1], x[0]))[0] if by_decade else None
    games_by_decade = Counter(f"{(y // 10) * 10}s" for y in yrs)
    tables["games-by-decade"] = {"description": "Games in the dataset by decade of first release.", "columns": ["decade", "games"],
                                 "rows": [{"decade": k, "games": v} for k, v in sorted(games_by_decade.items())]}
    # Dating exposure (§2.2, §5.2). A game is dated by its first public release, early access included, and decomposed at
    # the feature set its sources describe, which for a game changed after release can include later features. Found from
    # the records: early-access titles (year_full_release set, or design notes that say early access), persistent online
    # worlds (multiplayer persistent-mmo), and games whose use notes date part of a mechanic to a later update, expansion,
    # DLC, or version. The §5.2 counts are recomputed without each kind; a mechanic only exposed games use goes undated.
    import re as _re
    later_a = _re.compile(r"\b(?:update|expansion|dlc|patch|version \d[\d.]*)\b", _re.I)
    later_b = _re.compile(r"\b(?:add(?:s|ed)?|introduc\w*|split|let)\b", _re.I)
    later_c = _re.compile(r"\badded in\b|\bsince version\b", _re.I)
    exposed = {}
    for g in games:
        why = []
        if g.data.get("year_full_release") or _re.search(r"early access", str(g.data.get("design_notes") or ""), _re.I):
            why.append("early access")
        if "persistent-mmo" in (g.data.get("multiplayer") or []):
            why.append("persistent online world")
        later = [u["id"] for u in g.data.get("mechanics", []) if (later_a.search(str(u.get("note") or "")) and later_b.search(str(u.get("note") or "")))
                 or later_c.search(str(u.get("note") or ""))]
        if later:
            why.append("later feature: " + ", ".join(later))
        if why:
            exposed[g.id] = why

    def _dating(drop):
        keep_ = [g.id for g in games if isinstance(year.get(g.id), int) and g.id not in drop]
        first_ = {}
        for gid in keep_:
            for mid in used_by_game[gid]:
                first_[mid] = min(first_.get(mid, 9999), year[gid])
        old_ = {m for m, y in first_.items() if y <= 2000}
        late_ = [gid for gid in keep_ if year[gid] >= 2010]
        uses_ = [mid for gid in late_ for mid in used_by_game[gid]]
        moved_ = sum(1 for m in mechs if derived[m.id].get("earliest_year") and first_.get(m.id) != derived[m.id]["earliest_year"])
        return {"games": len(keep_), "dated": len(first_), "undated": sum(1 for m in mechs if derived[m.id]["prevalence"] > 0 and m.id not in first_),
                "moved": moved_, "pct_by_2000": _r(100 * len(old_) / max(len(first_), 1), 0),
                "since_2010": sum(1 for y in first_.values() if y >= 2010), "first_2020s": sum(1 for y in first_.values() if y >= 2020),
                "pct_reuse": _r(100 * sum(1 for mid in uses_ if mid in old_) / max(len(uses_), 1), 0),
                "games_since_2010": len(late_), "only_pre2001": sum(1 for gid in late_ if used_by_game[gid] and set(used_by_game[gid]) <= old_)}
    kinds = (("early access", lambda w: any(x == "early access" for x in w)), ("persistent online world", lambda w: "persistent online world" in w),
             ("later feature", lambda w: any(x.startswith("later feature") for x in w)))
    date_rows = []
    for label, drop in [("every game", set())] + [(f"without {k} titles", {g for g, w in exposed.items() if f(w)}) for k, f in kinds] + [("without any of these", set(exposed))]:
        d_ = _dating(drop)
        date_rows.append({"games": label, "count": d_["games"], "mechanics_dated": d_["dated"], "first_year_moved": d_["moved"],
                          "pct_seen_by_2000": d_["pct_by_2000"], "first_since_2010": d_["since_2010"], "first_2020s": d_["first_2020s"],
                          "pct_uses_since_2010_on_pre2001": d_["pct_reuse"], "games_since_2010": d_["games_since_2010"],
                          "using_only_pre2001": d_["only_pre2001"]})
    tables["dating-sensitivity"] = {
        "description": "The §5.2 counts with the games whose dating may predate their decomposed features left out: early-access titles, "
                       "persistent online worlds, and games whose use notes date part of a mechanic to a later update, expansion, DLC, or "
                       "version (dating-exposed-games.csv lists them). A mechanic used only by left-out games goes undated, and its "
                       "first year moves when its earliest game is left out.",
        "columns": ["games", "count", "mechanics_dated", "first_year_moved", "pct_seen_by_2000", "first_since_2010", "first_2020s",
                    "pct_uses_since_2010_on_pre2001", "games_since_2010", "using_only_pre2001"],
        "rows": date_rows}
    tables["dating-exposed-games"] = {
        "description": "Games whose release year may predate part of the feature set their record decomposes, and why.",
        "columns": ["game", "year", "year_full_release", "reason"],
        "rows": [{"game": gid, "year": year.get(gid), "year_full_release": by_id[gid].data.get("year_full_release"), "reason": "; ".join(w)}
                 for gid, w in sorted(exposed.items())], "link_columns": ["game"]}
    stats["n_games_dating_exposed"] = len(exposed)
    for k, f in kinds:
        stats["n_games_dating_" + k.replace(" ", "_")] = sum(1 for w in exposed.values() if f(w))
    all_out = date_rows[-1]
    stats["pct_mechanics_seen_by_2000_excl_exposed"] = all_out["pct_seen_by_2000"]
    stats["n_mechanics_since_2010_excl_exposed"] = all_out["first_since_2010"]
    stats["pct_uses_since_2010_on_pre2001_excl_exposed"] = all_out["pct_uses_since_2010_on_pre2001"]
    stats["n_mechanics_undated_excl_exposed"] = sum(1 for m in mechs if derived[m.id]["prevalence"] > 0) - all_out["mechanics_dated"]
    stats["n_mechanics_first_year_moved_excl_exposed"] = all_out["first_year_moved"]

    # ---------------- verification queue
    q = []
    for t in ("technique", "game", "mechanic", "opportunity"):
        for e in sorted(live.get(t, []), key=lambda e: e.id):
            if e.data.get("status") == "asserted":
                q.append({"type": t, "id": e.id, "name": e.data.get("name")})
    tables["verification-queue"] = {"description": "Asserted entities awaiting sources, in triage order.", "columns": ["type", "id", "name"], "rows": q}

    # ---------------- method and definitions (sections 1 and 2, Appendix E). Everything here is read from the structures
    # the analysis above uses or from the files that parameterize it, so the paper's definitions cannot drift from the
    # computation they describe.
    # Evidence by entity type. Status and citing are different counts: an asserted record may already cite a source in a
    # claim without having been promoted, and a contested record cites both sides, so the paper gives both per type.
    ev_rows = []
    for t, label in (("game", "games"), ("mechanic", "mechanics"), ("technique", "techniques"), ("opportunity", "opportunities")):
        es = live.get(t, [])
        st = Counter(e.data.get("status") for e in es)
        cite = [e for e in es if outgoing.get(e.id, {}).get("cites")]
        ev_rows.append({"type": label, "records": len(es), "sourced": st.get("sourced", 0), "verified": st.get("verified", 0),
                        "contested": st.get("contested", 0), "asserted": st.get("asserted", 0), "cite_a_source": len(cite),
                        "asserted_but_citing": sum(1 for e in cite if e.data.get("status") == "asserted")})
        stats[f"n_{t}_sourced_or_verified"] = st.get("sourced", 0) + st.get("verified", 0)
        stats[f"n_{t}_contested"] = st.get("contested", 0)
    ev_rows.append({k: ("all" if k == "type" else sum(r[k] for r in ev_rows)) for k in ev_rows[0]})
    tables["evidence-by-type"] = {"description": "Records by type and evidence status. Status partitions each type; a record cites a source when it or one of its claims names one, so the cite column also counts contested records and asserted records whose sources have not yet been checked for promotion.",
                                  "columns": ["type", "records", "sourced", "verified", "contested", "asserted", "cite_a_source", "asserted_but_citing"], "rows": ev_rows}
    # Relations among mechanics (requires, specializes, synergy, tension): how sparse the vocabulary's typed relations are.
    # A mechanic's relation degree counts every such edge that touches it; density is the share of possible mechanic
    # pairs joined by at least one relation of any type.
    mech_ids = {m.id for m in mechs}
    rel_types = ("requires", "specializes", "synergy", "tension")
    rel_deg, rel_pairs, n_rel = Counter(), set(), 0
    for ed in edges:
        if ed.type in rel_types and ed.source in mech_ids and ed.target in mech_ids:
            n_rel += 1
            rel_deg[ed.source] += 1
            rel_deg[ed.target] += 1
            rel_pairs.add(tuple(sorted((ed.source, ed.target))))
    degs = [rel_deg.get(m.id, 0) for m in mechs] or [0]
    stats["n_relation_edges"] = n_rel
    stats["relation_edges_per_mechanic"] = _r(float(np.mean(degs)), 2)
    stats["median_relation_edges_per_mechanic"] = _r(float(np.median(degs)), 1)
    stats["max_relation_edges_per_mechanic"] = max(degs)
    stats["n_mechanics_no_relation"] = sum(1 for d in degs if d == 0)
    stats["pct_mechanics_no_relation"] = _r(100 * stats["n_mechanics_no_relation"] / max(len(mechs), 1), 0)
    stats["relation_pair_density_pct"] = _r(100 * len(rel_pairs) / max(len(mechs) * (len(mechs) - 1) / 2, 1), 2)
    # The weights behind technique exposure and opportunity priority, as vocab/rubrics.yaml states them.
    mat_terms, eff_terms = vocab_terms(vocabs, "technique_maturity"), vocab_terms(vocabs, "effect")
    tables["exposure-weights"] = {"description": "The weights technique exposure multiplies for each affects edge, from vocab/rubrics.yaml (composites.technique_exposure): one for the technique's maturity in games and one for the edge's effect type, with the effect vocabulary's definition.",
                                  "columns": ["factor", "term", "weight", "definition"],
                                  "rows": [{"factor": "maturity", "term": mat_terms.get(k, {}).get("label", k), "weight": v, "definition": mat_terms.get(k, {}).get("definition", "")}
                                           for k, v in comp["maturity_weights"].items()]
                                  + [{"factor": "effect", "term": eff_terms.get(k, {}).get("label", k), "weight": v, "definition": eff_terms.get(k, {}).get("definition", "")}
                                     for k, v in comp["effect_weights"].items()]}
    for k, v in rub["composites"]["opportunity_priority"]["weights"].items():
        stats[f"priority_{k}"] = v
    stats["clustering_core_weight"] = cl["core_weight"]
    stats["whitespace_max_observed"] = ws["max_observed"]
    # The white-space table numbers its rows, so a reader can match them to the numbered lots of the vacant-lots figure.
    if "whitespace" in tables:
        tables["whitespace"] = {**tables["whitespace"], "columns": ["rank"] + [c for c in tables["whitespace"]["columns"] if c != "rank"],
                                "rows": [{"rank": i + 1, **r} for i, r in enumerate(tables["whitespace"]["rows"])]}
    # How much of the paper's prose the build checks. Numbers reach the prose only through tokens; a sentence that reads
    # a ranking, sign, threshold, or grouping carries {{assert:...}} tokens. Counted per sentence of report/src, split at
    # sentence-ending punctuation (an assertion written after a full stop belongs to the sentence before it), leaving out
    # headings, tables, and lines that hold only a table or figure token.
    # The book (book/src) is counted the same way for its chapter on checks.
    for prefix, folder in (("report", ROOT / "report" / "src"), ("book", ROOT / "book" / "src")):
        n_sent = n_sent_num = n_sent_assert = n_assert = 0
        for p in sorted(folder.glob("*.md")):
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith(("#", "|", "<")) or re.fullmatch(r"(\{\{(table|figure|viz):[^}]+\}\}\s*)+", s):
                    continue
                s = re.sub(r"^(?:[-*]|\d+\.)\s+", "", s)
                n_assert += len(re.findall(r"\{\{assert:", s))
                s = re.sub(r"\{\{assert:[^}]*\}\}", "\x00", s)
                for sent in re.split(r"(?<=[.!?\x00])\s+(?=[A-Z0-9*\[(`\"“_{])", s):
                    if not re.search(r"[A-Za-z]{2}", sent.replace("\x00", "")):
                        continue
                    n_sent += 1
                    n_sent_assert += "\x00" in sent
                    n_sent_num += bool(re.search(r"\{\{(stat|count|derived|rank):", sent))
        stats[f"n_{prefix}_sentences"] = n_sent
        stats[f"n_{prefix}_sentences_with_numbers"] = n_sent_num
        stats[f"n_{prefix}_sentences_asserted"] = n_sent_assert
        stats[f"n_{prefix}_assertions"] = n_assert
    stats["n_record_assertions"] = sum(len(e.data.get("assertions") or []) for lst in live.values() for e in lst)
    stats["n_records_with_assertions"] = sum(1 for lst in live.values() for e in lst if e.data.get("assertions"))
    # What the admission tests leave checkable: the build can count games and levers, not judge atomicity.
    stats["n_mechanics_one_game"] = sum(1 for m in mechs if derived[m.id]["prevalence"] == 1)
    stats["min_design_levers"] = min((len(m.data.get("design_levers") or []) for m in mechs), default=0)
    stats["median_design_levers"] = _r(float(np.median([len(m.data.get("design_levers") or []) for m in mechs])), 1) if mechs else 0

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


# ---------------- rubric-score statistics: rank correlations and agreement between raters

def _spearman(x, y) -> float:
    """Spearman's rho (average ranks for ties); nan when either variable is constant."""
    rx, ry = rankdata(x), rankdata(y)
    rx, ry = rx - rx.mean(), ry - ry.mean()
    den = math.sqrt(float((rx * rx).sum() * (ry * ry).sum()))
    return float((rx * ry).sum() / den) if den else float("nan")


def _spearman_rows(X, Y) -> np.ndarray:
    """Spearman's rho for each row of two equal-shape matrices (bootstrap resamples); nan for a constant row."""
    rx, ry = rankdata(X, axis=1), rankdata(Y, axis=1)
    rx, ry = rx - rx.mean(1, keepdims=True), ry - ry.mean(1, keepdims=True)
    den = np.sqrt((rx * rx).sum(1) * (ry * ry).sum(1))
    return np.divide((rx * ry).sum(1), den, out=np.full(len(den), np.nan), where=den > 0)


def _spearman_within(x, y, groups) -> float:
    """Rank correlation within groups: rank both variables over all items, subtract each group's mean rank, and correlate
    what is left, so that differences between the groups' levels do not count."""
    rx, ry = rankdata(x), rankdata(y)
    for ii in groups:
        rx[ii] -= rx[ii].mean()
        ry[ii] -= ry[ii].mean()
    den = math.sqrt(float((rx * rx).sum() * (ry * ry).sum()))
    return float((rx * ry).sum() / den) if den else float("nan")


def _coincidence(values, K: int) -> np.ndarray:
    """Krippendorff's coincidence matrix for one record's ratings on a 1..K scale: every ordered pair of its ratings,
    weighted 1/(m-1) for m ratings."""
    C = np.zeros((K, K))
    for i, x in enumerate(values):
        for j, y in enumerate(values):
            if i != j:
                C[x - 1, y - 1] += 1 / (len(values) - 1)
    return C


def _alpha_ordinal(O) -> np.ndarray | float:
    """Krippendorff's alpha with the ordinal metric (Krippendorff 2011) from a coincidence matrix, or a stack of them
    (..., K, K). The ordinal distance between anchors c and k is (sum of n_g for g from c to k, minus (n_c + n_k) / 2) squared.
    nan where every rating sits on one anchor. Reproduces the worked example in Krippendorff (2011): 0.815."""
    O = np.asarray(O, float)
    nc = O.sum(-1)
    n = nc.sum(-1)
    c = np.arange(O.shape[-1])
    lo, hi = np.minimum.outer(c, c), np.maximum.outer(c, c)
    cs = np.cumsum(nc, -1)
    d2 = (cs[..., hi] - cs[..., lo] + (nc[..., lo] - nc[..., hi]) / 2) ** 2
    do = (O * d2).sum((-1, -2)) / np.where(n > 0, n, 1)
    de = (nc[..., :, None] * nc[..., None, :] * d2).sum((-1, -2)) / np.where(n > 1, n * (n - 1), 1)
    a = np.where(de > 0, 1 - do / np.where(de > 0, de, 1), np.nan)
    return float(a) if a.ndim == 0 else a


def _kappa_quadratic(a, b, K: int) -> float:
    """Cohen's quadratic-weighted kappa between two raters' ratings on a 1..K scale; nan when chance disagreement is zero."""
    O = np.zeros((K, K))
    np.add.at(O, (np.asarray(a, int) - 1, np.asarray(b, int) - 1), 1)
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    w = (np.subtract.outer(np.arange(K), np.arange(K)) ** 2).astype(float)
    de = float((w * E).sum())
    return 1 - float((w * O).sum()) / de if de else float("nan")


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


def _emi(ra, cb, n) -> float:
    """Expected mutual information of two labelings with cluster sizes ra and cb (hypergeometric model). It depends
    only on the sizes, so every shuffle of one labeling has the same E[MI]."""
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
    return emi


def _ami(a, b, emi=None) -> float:
    """Adjusted mutual information (Vinh, Epps and Bailey 2010), arithmetic-mean normalization like _nmi:
    (MI - E[MI]) / (mean entropy - E[MI]), with E[MI] taken over all labelings with the same cluster sizes.
    Pass `emi` to reuse E[MI] across shuffles of one labeling (same sizes, same E[MI])."""
    C = _contingency(a, b)
    n = C.sum()
    ra, cb = C.sum(1), C.sum(0)
    P = C / n
    pa, pb = ra / n, cb / n
    nz = P > 0
    mi = float((P[nz] * np.log(P[nz] / np.outer(pa, pb)[nz])).sum())
    ha = float(-(pa[pa > 0] * np.log(pa[pa > 0])).sum())
    hb = float(-(pb[pb > 0] * np.log(pb[pb > 0])).sum())
    if emi is None:
        emi = _emi(ra, cb, n)
    den = (ha + hb) / 2 - emi
    return (mi - emi) / den if den else 1.0


def _n_mixed(labels, codes, n_codes, share=1.0) -> int:
    """Clusters whose largest subgenre holds less than `share` of their games (share 1: any second subgenre).
    `codes` are integer subgenre codes, one per game, aligned with `labels`."""
    a = np.asarray(labels) - np.min(labels)
    C = np.bincount(a * n_codes + np.asarray(codes), minlength=(int(a.max()) + 1) * n_codes).reshape(-1, n_codes)
    size = C.sum(1)
    keep = size > 0
    pct = int(round(100 * share))
    return int(np.sum(C.max(1)[keep] * 100 < pct * size[keep]))


def _cluster_jaccard(labels, subs, cuts, restrict=True) -> dict:
    """Mean best-match Jaccard of each cluster of `labels` across subsample clusterings (Hennig's subsetting scheme).

    restrict=True (the stability the paper reports): in each subsample S the full cluster A is restricted to the games
    S keeps and compared with every cluster B of S's clustering, |A n S n B| / |(A n S) u B|; the best B counts, and
    the mean runs over the subsamples that keep at least one game of A (a subsample keeping none is skipped; one
    keeping a single game scores 1 only when that game is alone in its subsample cluster). restrict=False keeps the
    whole of A, |A n B| / |A u B|, so even perfect recovery scores about the subsample fraction, and a subsample
    keeping no game of A scores 0."""
    nc = int(labels.max()) + 1
    full = np.bincount(labels, minlength=nc).astype(float)
    jac = defaultdict(list)
    for sb, lb in zip(subs, cuts):
        ct = np.zeros((nc, int(lb.max()) + 1))
        np.add.at(ct, (labels[sb], lb), 1)
        rows_, cols_ = ct.sum(1), ct.sum(0)
        den = (rows_ if restrict else full)[:, None] + cols_[None, :] - ct
        best = np.max(ct / np.where(den > 0, den, 1.0), axis=1)
        for c in np.flatnonzero(rows_ > 0 if restrict else full > 0):
            if c:
                jac[int(c)].append(float(best[c]))
    return {c: float(np.mean(v)) for c, v in sorted(jac.items())}


def _best_match(labels, other) -> dict:
    """For each cluster of `labels`, the Jaccard overlap with its best-matching cluster of another partition."""
    a = np.asarray(labels) - np.min(labels)
    b = np.asarray(other) - np.min(other)
    nb = int(b.max()) + 1
    ct = np.bincount(a * nb + b, minlength=(int(a.max()) + 1) * nb).reshape(-1, nb).astype(float)
    ra, cb = ct.sum(1), ct.sum(0)
    return {int(c) + int(np.min(labels)): float(np.max(ct[c] / (ra[c] + cb - ct[c]))) for c in range(ct.shape[0]) if ra[c] > 0}


def _wj_distance(gm, gids, core_weight, idf=True):
    """Weighted Jaccard distance between games, built as the clustering builds it (core weight times log(N / prevalence)),
    from {game: {mechanic: role}}. Used for the sensitivity checks, which change the mechanic sets or the weights."""
    n = len(gids)
    pv = Counter(m for g in gids for m in gm[g])
    col = {m: i for i, m in enumerate(sorted(pv))}
    X = np.zeros((n, len(col)))
    for i, g in enumerate(gids):
        for m, role in gm[g].items():
            X[i, col[m]] = (core_weight if role == "core" else 1.0) * (math.log(n / pv[m]) if idf else 1.0)
    D = np.zeros((n, n))
    for i in range(n):
        mn = np.minimum(X[i], X).sum(1)
        mx = np.maximum(X[i], X).sum(1)
        D[i] = 1 - np.divide(mn, mx, out=np.zeros(n), where=mx > 0)
    np.fill_diagonal(D, 0.0)
    return D


def _merge_mechanics(gm, root) -> dict:
    """Relabel each game's mechanics by root[m] (a coarser vocabulary); a merged mechanic is core if any part was."""
    out = {}
    for g, ms in gm.items():
        nm = {}
        for m, role in ms.items():
            r = root.get(m, m)
            nm[r] = "core" if role == "core" or nm.get(r) == "core" else "supporting"
        out[g] = nm
    return out


# ---------------- second coder: agreement on three coding decisions (review findings D3, D4, D6)

def _alpha_nominal(O) -> np.ndarray | float:
    """Krippendorff's alpha with the nominal metric from a coincidence matrix (_coincidence), or a stack of them
    (..., K, K): one minus (n - 1) times the off-diagonal coincidences over the pairs of values that differ by chance.
    nan where every value is the same. Reproduces the worked example in Krippendorff (2011): 0.743 (0.815 ordinal)."""
    O = np.asarray(O, float)
    nc = O.sum(-1)
    n = nc.sum(-1)
    de = n * n - (nc * nc).sum(-1)
    a = np.where(de > 0, 1 - (n - 1) * (n - np.trace(O, axis1=-2, axis2=-1)) / np.where(de > 0, de, 1), np.nan)
    return float(a) if a.ndim == 0 else a


def _kappa_nominal(O) -> np.ndarray | float:
    """Cohen's kappa from a confusion matrix of two coders' codes (rows the first coder's), or a stack of them; nan when
    chance agreement is one. With two categories it equals _kappa_quadratic."""
    O = np.asarray(O, float)
    n = O.sum((-1, -2))
    po = np.trace(O, axis1=-2, axis2=-1) / np.where(n > 0, n, 1)
    pe = (O.sum(-1) * O.sum(-2)).sum(-1) / np.where(n > 0, n * n, 1)
    k = np.where(pe < 1, (po - pe) / np.where(pe < 1, 1 - pe, 1), np.nan)
    return float(k) if k.ndim == 0 else k


def _second_coding(ents, vocabs, cfg, stats, tables):
    """Agreement between the codes each record carries and a second coder's, on the sample in report/analysis.yaml
    (second_coding), from the codes files in report/coding/ (scripts/coding.py checks them, and the build fails on a
    coder who is not independent of the runs that created, reviewed, or proposed a coded record). The sample's size is
    always stated; agreement only once codes exist, so before then there is nothing else to report.

    For each decision, the first code is the record's: a mechanic's family, an edge's effect, and for admission whether
    the vocabulary admits the item (every sampled mechanic does; the candidates are proposals no run took up, which the
    dataset leaves out without a recorded reason, so this compares a coder with the dataset's boundary). A coder admits
    an item that passes all four tests. Cohen's kappa pools every (first, coder) pair; Krippendorff's alpha (nominal)
    takes each item's first code and every coder's as one unit. Intervals resample the coded items within each stratum
    of the draw (the first code), as the sample was drawn. Per category, kappa is that category against the rest."""
    import coding  # local import: scripts/coding.py owns the sample and the codes format
    sc = cfg.get("second_coding") or {}
    sp = sc.get("sample") or {}
    items = coding.sample_items(ents, sc)
    stats["n_second_coding_mechanics"] = len(items["family"])
    stats["n_second_coding_families"] = len(set(items["family"].values()))
    stats["n_second_coding_candidates"] = sum(1 for i in sp.get("candidates") or [] if i in items["admission"])
    stats["n_second_coding_edges"] = len(items["effect"])
    stats["n_second_coding_effects"] = len(set(items["effect"].values()))
    stats["n_second_coding_techniques"] = len({i.split("/")[0] for i in items["effect"]})
    stats["n_family_terms"] = len(vocab_terms(vocabs, "mechanic_family"))  # so the prose can say the sample covers them all
    stats["n_effect_terms"] = len(vocab_terms(vocabs, "effect"))
    codings = coding.load_codings(ents, vocabs, sc)
    stats["n_second_coding_runs"] = len(codings)
    if not codings:
        return
    n_boot = int(sc.get("bootstrap", 2000))
    q = 100 * (1 - float(sc.get("interval", 0.95))) / 2
    rng = np.random.default_rng(int(sc.get("seed", 0)) + 1)
    fam, eff = vocab_terms(vocabs, "mechanic_family"), vocab_terms(vocabs, "effect")
    labels = {"family": {k: t["label"] for k, t in fam.items()}, "effect": {k: t["label"] for k, t in eff.items()},
              "admission": {"admit": "admitted", "reject": "left as a proposal"}}

    def code(d, v):
        return ("admit" if all(v[t] == "pass" for t in coding.TESTS) else "reject") if d == "admission" else v

    agree_rows, cat_rows, test_rows = [], [], []
    for d in coding.DECISIONS:
        cats = list(labels[d])
        ix = {c: i for i, c in enumerate(cats)}
        K = len(cats)
        units = [(item, first, [c["codes"][d][item] for c in codings if item in c["codes"][d]]) for item, first in sorted(items[d].items())]
        units = [u for u in units if u[2]]
        if not units:
            continue
        P, C = np.zeros((len(units), K, K)), np.zeros((len(units), K, K))
        for u, (_, first, vals) in enumerate(units):
            for v in vals:
                P[u, ix[first], ix[code(d, v)]] += 1
            C[u] = _coincidence([ix[first] + 1] + [ix[code(d, v)] + 1 for v in vals], K)
        strata = defaultdict(list)
        for u, (_, first, _vals) in enumerate(units):
            strata[first].append(u)
        W = np.zeros((n_boot, len(units)))
        for _, us in sorted(strata.items()):
            np.add.at(W, (np.arange(n_boot)[:, None], np.asarray(us)[rng.integers(0, len(us), (n_boot, len(us)))]), 1)
        bk = _kappa_nominal(np.einsum("bu,ukl->bkl", W, P))
        ba = _alpha_nominal(np.einsum("bu,ukl->bkl", W, C))
        bk, ba = bk[np.isfinite(bk)], ba[np.isfinite(ba)]
        Ps = P.sum(0)
        row = {"decision": d, "coders": sum(1 for c in codings if c["codes"][d]), "items": len(units), "pairs": int(Ps.sum()),
               "agree": _r(np.trace(Ps) / Ps.sum(), 2), "kappa": _r(_kappa_nominal(Ps), 2),
               "kappa_low": _r(np.percentile(bk, q), 2) if len(bk) else None, "kappa_high": _r(np.percentile(bk, 100 - q), 2) if len(bk) else None,
               "alpha": _r(_alpha_nominal(C.sum(0)), 2),
               "alpha_low": _r(np.percentile(ba, q), 2) if len(ba) else None, "alpha_high": _r(np.percentile(ba, 100 - q), 2) if len(ba) else None}
        agree_rows.append(row)
        for k in ("kappa", "kappa_low", "kappa_high", "alpha", "alpha_low", "alpha_high"):
            base, _, bound = k.partition("_")  # kappa_second_coding_family, kappa_second_coding_family_low, ...
            stats[f"{base}_second_coding_{d}" + (f"_{bound}" if bound else "")] = row[k]
        stats[f"pct_second_coding_agree_{d}"] = int(round(100 * np.trace(Ps) / Ps.sum()))
        stats[f"n_second_coded_{d}"] = len(units)
        stats[f"n_second_coding_pairs_{d}"] = int(Ps.sum())
        n = Ps.sum()
        for c in cats:
            i = ix[c]
            both, first, second = Ps[i, i], Ps[i].sum(), Ps[:, i].sum()
            if first or second:
                T = np.array([[both, first - both], [second - both, n - first - second + both]])
                cat_rows.append({"decision": d, "category": labels[d][c], "first": int(first), "second": int(second), "both": int(both),
                                 "kappa": _r(_kappa_nominal(T), 2)})
        if d == "admission":
            # how often the coder upholds each test on the admitted mechanics, and passes it on the candidates
            by = {s: [v for _, first, vals in units if first == s for v in vals] for s in ("admit", "reject")}
            for t in coding.TESTS:
                test_rows.append({"test": t, "admitted": len(by["admit"]), "admitted_pass": sum(v[t] == "pass" for v in by["admit"]),
                                  "candidates": len(by["reject"]), "candidates_pass": sum(v[t] == "pass" for v in by["reject"])})
                if by["admit"]:
                    stats[f"pct_second_coding_upheld_{t}"] = int(round(100 * test_rows[-1]["admitted_pass"] / len(by["admit"])))
            if by["admit"]:
                stats["pct_second_coding_upheld"] = int(round(100 * sum(code(d, v) == "admit" for v in by["admit"]) / len(by["admit"])))
            stats["n_second_coding_candidates_admitted"] = sum(code(d, v) == "admit" for v in by["reject"])
    desc = (f"{round(100 - 2 * q)}% interval over {n_boot} resamples of the coded items within each stratum of the draw (report/analysis.yaml "
            "second_coding)")
    tables["second-coding-agreement"] = {
        "description": "Agreement between the code a record carries and a second coder's, per decision, on the seeded stratified sample "
                       "(scripts/coding.py). First codes: the mechanic's family, the edge's effect, and for admission whether the vocabulary "
                       "admits the item; the coder admits an item that passes all four tests. Agree is the share of pairs that match; kappa is "
                       f"Cohen's (unweighted) and alpha Krippendorff's with the nominal metric, each low and high bounding a {desc}. The sample "
                       "allocates every category equally, so these values describe it, not the catalog's unequal mix.",
        "columns": ["decision", "coders", "items", "pairs", "agree", "kappa", "kappa_low", "kappa_high", "alpha", "alpha_low", "alpha_high"],
        "rows": agree_rows}
    tables["second-coding-categories"] = {
        "description": "Per category of each coding decision: how many pairs the record's code (first) and the second coder (second) put in "
                       "it, how many both did, and Cohen's kappa for that category against the rest.",
        "columns": ["decision", "category", "first", "second", "both", "kappa"], "rows": cat_rows}
    if test_rows:
        tables["second-coding-tests"] = {
            "description": "The four admission tests as the second coder applied them: on the sampled mechanics the vocabulary admits, how many "
                           "codes pass each test, and the same on the candidates it left as proposals.",
            "columns": ["test", "admitted", "admitted_pass", "candidates", "candidates_pass"], "rows": test_rows}


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
