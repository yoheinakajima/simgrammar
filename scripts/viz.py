"""Interactive figures for the paper site, rendered statically first.

Each figure is a complete SVG computed here, deterministically, from the same structures
analyze.py uses. Every mark carries data attributes and every alternate layout is precomputed,
so the site's script only toggles, highlights, and reads out; it never lays anything out.
Colors are Register tokens with default-skin fallbacks (`var(--ink,#171717)`), so the same SVG
renders inside the site (themed) and as a standalone file next to paper.md.

build() returns {name: {"title", "head", "svg", "caption", "source", "controls", "data", "twin"}}.
The report places a figure with {{viz:<name>}}.
"""
from __future__ import annotations

import json
import math
from collections import Counter, defaultdict

import numpy as np

from lib import counted, vocab_terms

T = {
    "paper": "var(--paper,#fafaf7)", "paper2": "var(--paper-2,#f3f3ee)", "paper3": "var(--paper-3,#ebebe4)",
    "ink": "var(--ink,#171717)", "ink2": "var(--ink-2,#3d3d38)", "muted": "var(--muted,#696961)", "faint": "var(--faint,#97978e)",
    "rule": "var(--rule,#dcdcd4)", "rule2": "var(--rule-2,#bdbdb4)", "accent": "var(--accent,#0550ae)",
    "open": "var(--open,#a96512)", "stop": "var(--stop,#9a2d25)", "s1": "var(--s1,#2a78d6)",
}
MONO = "var(--mono,'IBM Plex Mono',ui-monospace,Menlo,monospace)"
CW = 0.6  # mono advance per font-size unit, for label fitting


def esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def f1(x) -> str:
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s


def svg_open(name, W, H, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" class="plot" id="svg-{name}" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'role="img" aria-labelledby="t-{name} d-{name}" style="max-width:100%;height:auto;font-family:{MONO};font-size:9px">'
            f'<title id="t-{name}">{esc(title)}</title><desc id="d-{name}">{esc(desc)}</desc>'
            f'<rect width="{W}" height="{H}" style="fill:{T["paper"]}"/>')


def text(x, y, s, size=9, fill="faint", anchor="start", weight=None, extra=""):
    w = f";font-weight:{weight}" if weight else ""
    return f'<text x="{f1(x)}" y="{f1(y)}" text-anchor="{anchor}" style="fill:{T[fill]};font-size:{size}px{w}"{extra}>{esc(s)}</text>'


def spread(targets, gap, lo, hi):
    """Place labels at preferred y positions with a minimum gap, inside [lo, hi]. Deterministic."""
    order = sorted(range(len(targets)), key=lambda i: (targets[i], i))
    ys = [0.0] * len(targets)
    prev = lo - gap
    for i in order:
        ys[i] = max(targets[i], prev + gap)
        prev = ys[i]
    over = prev - hi
    if over > 0:
        nxt = hi + gap
        for i in reversed(order):
            ys[i] = min(ys[i], nxt - gap)
            nxt = ys[i]
    return ys


def legend(items):
    """items: (label, kind, opacity). kind: square | dashed | slash | outline | outline-dashed | line."""
    out = []
    for label, kind, op in items:
        if kind == "square":
            st = f"background:{T['ink']};opacity:{op}"
        elif kind == "series":
            st = f"background:{T['s1']};opacity:{op}"
        elif kind == "dashed":
            st = f"background:transparent;border:1px dashed {T['open']}"
        elif kind == "slash":
            out.append(f'<span><svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><rect width="10" height="10" style="fill:{T["paper3"]}"/>'
                       f'<path d="M1.5 8.5L8.5 1.5" style="stroke:{T["stop"]};stroke-width:1.4"/></svg>{esc(label)}</span>')
            continue
        elif kind == "outline":
            st = f"background:{T['paper2']};border:1px solid {T['rule2']}"
        elif kind == "outline-dashed":
            st = f"background:{T['paper2']};border:1px dashed {T['rule2']}"
        else:
            st = f"background:{T['accent']}"
        out.append(f'<span><i style="{st}"></i>{esc(label)}</span>')
    return '<div class="legend">' + "".join(out) + "</div>"


def data_script(name, obj):
    return f'<script type="application/json" id="viz-data-{name}">{json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")}</script>'


# ======================================================================= build
def build(shared, live, by_id, derived, tables, stats, vocabs, cfg) -> dict:
    if not shared.get("games") or "game_distance" not in shared:
        return {}
    fam = vocab_terms(vocabs, "mechanic_family")
    sub = vocab_terms(vocabs, "subgenre")
    out = {}
    out["matrix"] = matrix(shared, live, by_id, derived, tables, fam)
    out["strata"] = strata(shared, live, by_id, derived, fam)
    out["design-map"] = design_map(shared, live, by_id, derived, tables, sub, cfg)
    if "cluster-stability" in tables:
        out["cluster-k-curve"] = cluster_k_curve(tables, cfg)
    out["vacant-lots"] = vacant_lots(shared, live, by_id, derived, tables, fam, cfg)
    out["technique-flows"] = technique_flows(live, by_id, derived, vocabs, fam)
    out["layer-profile"] = layer_profile(tables, fam, sub, cfg)
    out["constraint-profile"] = constraint_profile(live, fam)
    out["technique-landscape"] = technique_landscape(live, vocabs)
    out["determinism-runtime"] = determinism_runtime(live, vocabs)
    out["opportunity-priorities"] = opportunity_priorities(live, tables)
    out["prediction-timeline"] = prediction_timeline(live)
    out["pipeline"] = pipeline(live, stats)
    return out


# ======================================================================= 1. matrix
def matrix(shared, live, by_id, derived, tables, fam):
    gm = shared["gm"]
    games = shared["games"]
    mechs = [m for m in sorted(live["mechanic"], key=lambda m: m.id) if derived[m.id]["prevalence"] > 0]
    fam_order = list(fam)
    clusters = tables["game-clusters"]["rows"]

    # orders and groups
    rows_by_cluster = [(r["cluster"].lower(), r["members"]) for r in clusters]
    gyear = {g.id: g.data.get("year") or 0 for g in games}
    by_dec = defaultdict(list)
    for g in sorted(games, key=lambda g: (gyear[g.id], g.id)):
        by_dec[f"{(gyear[g.id] // 10) * 10}s"].append(g.id)
    rows_by_year = sorted(by_dec.items())
    cols_by_family = []
    for f in fam_order:
        ms = sorted((m for m in mechs if m.data["family"] == f), key=lambda m: (-derived[m.id]["prevalence"], m.id))
        if ms:
            cols_by_family.append((fam[f]["label"].lower(), [m.id for m in ms]))
    cdec = defaultdict(list)
    for m in sorted(mechs, key=lambda m: (derived[m.id]["earliest_year"] or 9999, m.id)):
        cdec[f"{((derived[m.id]['earliest_year'] or 0) // 10) * 10}s"].append(m.id)
    cols_by_first = sorted(cdec.items())

    row_ids = [g.id for g in games]
    col_ids = [m.id for m in mechs]
    ri = {g: i for i, g in enumerate(row_ids)}
    ci = {m: i for i, m in enumerate(col_ids)}

    P, S, G = 4, 3, 4  # pitch, cell size, group gap
    LM, TM = 40, 150

    def lay(groups, index, start, gap):
        pos = [0.0] * len(index)
        spans = []
        cur = start
        for label, ids in groups:
            s0 = cur
            for x in ids:
                pos[index[x]] = cur
                cur += P
            spans.append((label, s0, cur - P + S))
            cur += gap
        return pos, spans, cur - gap

    ry = {}
    rspans = {}
    cx = {}
    cspans = {}
    ry["cluster"], rspans["cluster"], hc = lay(rows_by_cluster, ri, TM, G)
    ry["year"], rspans["year"], hy = lay(rows_by_year, ri, TM, G)
    cx["family"], cspans["family"], wf = lay(cols_by_family, ci, LM, G)
    cx["first"], cspans["first"], wfi = lay(cols_by_first, ci, LM, G)
    RM = 6
    W = int(max(wf, wfi) + RM)
    H = int(max(hc, hy) + 8)

    body = [svg_open("matrix", W, H, "Every mechanic use in the catalog",
                     f"A grid of {counted(len(row_ids), 'game')} by {counted(len(col_ids), 'mechanic')}. Filled squares are core uses, light squares supporting uses. "
                     "Rows are grouped by cluster, columns by mechanic family.")]
    # band shading for alternate row groups
    for mode, spans in rspans.items():
        hide = "" if mode == "cluster" else ' display="none"'
        body.append(f'<g data-layer="rows-{mode}"{hide}>')
        for k, (label, y0, y1) in enumerate(spans):
            if k % 2 == 0:
                body.append(f'<rect x="{LM - 4}" y="{f1(y0 - 1)}" width="{W - LM + 2}" height="{f1(y1 - y0 + 2)}" style="fill:{T["paper2"]}"/>')
            if y1 - y0 >= 9:
                body.append(text(LM - 8, y0 + 7, label, 9, "muted", "end"))
        body.append("</g>")
    for mode, spans in cspans.items():
        hide = "" if mode == "family" else ' display="none"'
        body.append(f'<g data-layer="cols-{mode}"{hide}>')
        for label, x0, x1 in spans:
            xm = (x0 + x1) / 2
            body.append(f'<line x1="{f1(x0)}" y1="{TM - 6}" x2="{f1(x1)}" y2="{TM - 6}" style="stroke:{T["rule2"]}"/>')
            body.append(f'<text transform="translate({f1(xm + 3)},{TM - 10}) rotate(-90)" style="fill:{T["muted"]};font-size:9px">{esc(label)}</text>')
        body.append("</g>")
    # cells
    cells = []
    for g in games:
        for mid, role in sorted(gm[g.id].items()):
            if mid in ci:
                cells.append((ri[g.id], ci[mid], 2 if role == "core" else 1))
    for role, op in ((1, "0.32"), (2, "1")):
        body.append(f'<g data-cells="{role}" style="fill:{T["ink"]}" fill-opacity="{op}">')
        for r, c, rl in cells:
            if rl == role:
                body.append(f'<rect x="{f1(cx["family"][c])}" y="{f1(ry["cluster"][r])}" width="{S}" height="{S}" data-r="{r}" data-c="{c}"/>')
        body.append("</g>")
    body.append(f'<rect data-hl="row" x="{LM - 4}" y="0" width="{W - LM + 2}" height="{P}" style="fill:{T["accent"]}" fill-opacity="0.16" display="none"/>')
    body.append(f'<rect data-hl="col" x="0" y="{TM - 4}" width="{P}" height="{H - TM}" style="fill:{T["accent"]}" fill-opacity="0.16" display="none"/>')
    body.append("</svg>")

    data = {
        "rows": [{"id": g.id, "name": g.data["name"], "year": gyear[g.id], "cluster": derived[g.id].get("cluster")} for g in games],
        "cols": [{"id": m.id, "name": m.data["name"], "family": fam[m.data["family"]]["label"], "first": derived[m.id]["earliest_year"],
                  "prevalence": derived[m.id]["prevalence"]} for m in mechs],
        "cells": cells, "rowY": {k: [round(v, 1) for v in vv] for k, vv in ry.items()}, "colX": {k: [round(v, 1) for v in vv] for k, vv in cx.items()},
        "pitch": P, "size": S, "left": LM, "top": TM,
    }
    controls = ('<div class="cluster" data-controls="matrix">'
                '<div class="segmented" role="group" aria-label="Order rows"><button type="button" data-set="rows" data-value="cluster" aria-pressed="true">rows by cluster</button>'
                '<button type="button" data-set="rows" data-value="year" aria-pressed="false">rows by year</button></div>'
                '<div class="segmented" role="group" aria-label="Order columns"><button type="button" data-set="cols" data-value="family" aria-pressed="true">columns by family</button>'
                '<button type="button" data-set="cols" data-value="first" aria-pressed="false">columns by first use</button></div></div>')
    trows = []
    for g in sorted(games, key=lambda g: (derived[g.id].get("cluster") or "", g.id)):
        core = [m for m, r in sorted(gm[g.id].items()) if r == "core"]
        trows.append({"game": g.id, "year": gyear[g.id], "cluster": derived[g.id].get("cluster"), "core": core,
                      "supporting": sum(1 for r in gm[g.id].values() if r != "core")})
    n_core = sum(1 for c in cells if c[2] == 2)
    return {
        "title": "Every use: the catalog as a grid",
        "head": f"{counted(len(row_ids), 'game')} × {counted(len(col_ids), 'mechanic')} · {counted(len(cells), 'use')}",
        "svg": "".join(body),
        "caption": f"Each square is one game using one mechanic: {n_core} core uses (dark) and {len(cells) - n_core} supporting uses (light). "
                   "Rows are grouped into the clusters of §5.4 and columns into mechanic families. Hover or tap to read a cell; reorder rows by release year or columns by first use.",
        "source": "dist/tables/game_mechanic_matrix.csv · clusters from dist/analysis/game-clusters.csv",
        "controls": controls,
        "legend": legend([("core use", "square", "1"), ("supporting use", "square", "0.32")]),
        "min_width": 760,
        "data": data_script("matrix", data),
        "twin": {"columns": ["game", "year", "cluster", "core", "supporting"], "rows": trows, "link_columns": ["game", "core"],
                 "note": "Every game with its cluster, core mechanics, and number of supporting mechanics. The full grid is game_mechanic_matrix.csv."},
    }


# ======================================================================= 2. strata
def strata(shared, live, by_id, derived, fam):
    games = shared["games"]
    mechs = [m for m in sorted(live["mechanic"], key=lambda m: m.id) if derived[m.id]["earliest_year"]]
    years = [g.data.get("year") for g in games if isinstance(g.data.get("year"), int)]
    y0, y1 = min(years), max(years)
    first = {m.id: derived[m.id]["earliest_year"] for m in mechs}
    fams = sorted({m.data["family"] for m in mechs}, key=lambda f: (float(np.mean([first[m.id] for m in mechs if m.data["family"] == f])), f))
    n = len(mechs)
    W, H = 880, 470
    L, R, TOP, BOT = 40, 690, 40, 400
    sx = lambda y: L + (y - y0) / (y1 - y0 + 1) * (R - L)
    sy = lambda c: BOT - c / n * (BOT - TOP)
    yrs = list(range(y0, y1 + 2))
    cum = {f: [sum(1 for m in mechs if m.data["family"] == f and first[m.id] <= y) for y in yrs] for f in fams}
    base = [0] * len(yrs)
    body = [svg_open("strata", W, H, "The vocabulary, year by year",
                     f"Cumulative count of the {n} mechanics by the year of their first catalog game, stacked by family from oldest (bottom) to newest (top).")]
    # grid
    for dec in range((y0 // 10 + 1) * 10, y1 + 1, 10):
        body.append(f'<line x1="{f1(sx(dec))}" y1="{TOP}" x2="{f1(sx(dec))}" y2="{BOT}" style="stroke:{T["rule"]}"/>')
        body.append(text(sx(dec), BOT + 14, dec, 9, "faint", "middle"))
    for c in range(0, n + 1, 50):
        body.append(text(L - 6, sy(c) + 3, c, 9, "faint", "end"))
    layers = []
    label_targets = []
    for k, f in enumerate(fams):
        top = [b + c for b, c in zip(base, cum[f])]
        pts_top = []
        pts_bot = []
        for i, y in enumerate(yrs):
            xa, xb = sx(y), sx(y + 1) if i < len(yrs) - 1 else sx(y)
            pts_top += [(xa, sy(top[i])), (xb, sy(top[i]))]
            pts_bot += [(xa, sy(base[i])), (xb, sy(base[i]))]
        poly = pts_top + list(reversed(pts_bot))
        d = "M" + "L".join(f"{f1(x)},{f1(y)}" for x, y in poly) + "Z"
        fill_op = "0.13" if k % 2 == 0 else "0.05"
        cnt = cum[f][-1]
        fm = sorted((m for m in mechs if m.data["family"] == f), key=lambda m: (first[m.id], m.id))
        layers.append(f'<path d="{d}" data-family="{f}" data-label="{esc(fam[f]["label"])}" data-count="{cnt}" '
                      f'data-first="{first[fm[0].id]}" fill-opacity="{fill_op}" style="fill:{T["ink"]};stroke:{T["rule2"]};stroke-width:0.6"/>')
        label_targets.append(((sy(top[-1]) + sy(base[-1])) / 2, f, cnt))
        base = top
    body.append('<g data-layer="strata">' + "".join(layers) + "</g>")
    # labels on the right with leaders
    ys = spread([t[0] for t in label_targets], 10.5, TOP, BOT)
    for (ty, f, cnt), ly in zip(label_targets, ys):
        body.append(f'<path d="M{R + 2},{f1(ty)} L{R + 14},{f1(ty)} L{R + 22},{f1(ly)} L{R + 26},{f1(ly)}" style="fill:none;stroke:{T["rule2"]};stroke-width:0.6"/>')
        body.append(text(R + 30, ly + 3, f'{fam[f]["label"].lower()} · {cnt}', 9, "muted"))
    # annotations: years with the most new mechanics, credited to the game that introduced most of them
    intro = defaultdict(list)
    for m in mechs:
        intro[first[m.id]].append(m)
    by_game = Counter(derived[m.id]["earliest_game"] for m in mechs)
    top_years = sorted(intro, key=lambda y: (-len(intro[y]), y))[:6]
    total = [sum(cum[f][i] for f in fams) for i in range(len(yrs))]
    ann = []
    for y in sorted(top_years):
        gid = Counter(derived[m.id]["earliest_game"] for m in intro[y]).most_common(1)[0][0]
        ann.append((y, by_id[gid].data["name"], len(intro[y])))
    rows_end = []  # greedy rows: each label goes in the lowest row where it does not overlap
    for y, gname, cnt in ann:
        x = sx(y) + 1
        ty = sy(total[yrs.index(y)])
        lab = f"{y} {gname.lower()} +{cnt}"
        w = len(lab) * 9 * CW
        x0 = min(x - 4, R - w)
        row = next((r for r, end in enumerate(rows_end) if x0 > end + 8), len(rows_end))
        if row == len(rows_end):
            rows_end.append(0)
        rows_end[row] = x0 + w
        ly = ty - 14 - row * 12
        body.append(f'<line x1="{f1(x)}" y1="{f1(ty - 2)}" x2="{f1(x)}" y2="{f1(ly + 3)}" style="stroke:{T["rule2"]};stroke-width:0.6"/>')
        body.append(text(x0, ly, lab, 9, "ink2"))
    # rug of game releases
    body.append('<g data-layer="rug">')
    for g in sorted(games, key=lambda g: ((g.data.get("year") or 0), g.id)):
        gy = g.data.get("year")
        x = sx(gy) + 0.5 + (hash_unit(g.id) * (R - L) / (y1 - y0 + 1) * 0.8)
        body.append(f'<line x1="{f1(x)}" y1="{BOT + 22}" x2="{f1(x)}" y2="{BOT + 32}" data-game="{g.id}" style="stroke:{T["faint"]};stroke-width:0.8"/>')
    body.append("</g>")
    body.append(text(L, BOT + 46, "game releases", 9, "faint"))
    body.append(f'<line data-hl="year" x1="0" y1="{TOP}" x2="0" y2="{BOT + 32}" style="stroke:{T["accent"]};stroke-width:1" display="none"/>')
    body.append("</svg>")
    data = {
        "y0": y0, "y1": y1, "left": L, "right": R, "years": yrs, "total": total,
        "added": {str(y): [[m.id, m.data["name"], fam[m.data["family"]]["label"], derived[m.id]["earliest_game"],
                            by_id[derived[m.id]["earliest_game"]].data["name"]] for m in sorted(ms, key=lambda m: m.id)] for y, ms in sorted(intro.items())},
        "games": {g.id: [g.data["name"], g.data.get("year")] for g in games},
    }
    controls = ('<div class="cluster" data-controls="strata"><label class="field" style="min-width:220px"><span>year</span>'
                f'<input type="range" min="{y0}" max="{y1}" step="1" value="{y1}" data-set="year" aria-label="Year"></label></div>')
    trows = [{"year": first[m.id], "mechanic": m.id, "family": fam[m.data["family"]]["label"], "first_game": derived[m.id]["earliest_game"]}
             for m in sorted(mechs, key=lambda m: (first[m.id], m.id))]
    return {
        "title": "The vocabulary, year by year",
        "head": f"{counted(n, 'mechanic')} · {y0} to {y1}",
        "svg": "".join(body),
        "caption": "Cumulative mechanics by the year of their first catalog game, one layer per family, oldest families at the bottom. "
                   "Labels mark the years that added the most mechanics and the game that introduced most of them. Drag the year control, or hover or tap the chart, to read what each year added.",
        "source": "derived.earliest_year per mechanic · dist/entities/mechanics.json",
        "controls": controls,
        "legend": "",
        "min_width": 680,
        "data": data_script("strata", data),
        "twin": {"columns": ["year", "mechanic", "family", "first_game"], "rows": trows, "link_columns": ["mechanic", "first_game"],
                 "note": "Every mechanic in order of first appearance in the catalog. First appearance is an upper bound on the year a mechanic originated: it is at least that old."},
    }


def hash_unit(s: str) -> float:
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) % 1000003
    return (h % 1000) / 1000


# ======================================================================= 3. design-space map
def _fr(pos, ei, ej, ew, iters, k=1.0, gravity=0.02, radii=None, temp0=1.0):
    """Deterministic Fruchterman-Reingold with optional disc collisions; positions rounded each step."""
    n = len(pos)
    for it in range(iters):
        disp = np.zeros_like(pos)
        if n > 1:
            delta = pos[:, None, :] - pos[None, :, :]
            dist2 = (delta ** 2).sum(-1) + 1e-6
            disp = ((k * k / dist2)[..., None] * delta).sum(1)
        if len(ei):
            dv = pos[ei] - pos[ej]
            dl = np.sqrt((dv ** 2).sum(-1)) + 1e-9
            fa = (dl / k * ew)[:, None] * dv
            np.subtract.at(disp, ei, fa)
            np.add.at(disp, ej, fa)
        disp -= gravity * pos
        temp = temp0 * (1 - it / iters) + 0.01
        ln = np.sqrt((disp ** 2).sum(-1)) + 1e-9
        pos = pos + disp / ln[:, None] * np.minimum(ln, temp)[:, None]
        if radii is not None:
            for _ in range(4):
                for a in range(n):
                    for b in range(a + 1, n):
                        d = pos[b] - pos[a]
                        dist = math.sqrt(float(d[0] ** 2 + d[1] ** 2)) + 1e-9
                        need = radii[a] + radii[b]
                        if dist < need:
                            push = (need - dist) / 2 * d / dist
                            pos[a] = pos[a] - push
                            pos[b] = pos[b] + push
        pos = np.round(pos, 4)
    return pos


def design_map(shared, live, by_id, derived, tables, sub, cfg):
    ids = shared["game_ids"]
    D = np.asarray(shared["game_distance"], dtype=float)
    N = len(ids)
    vc = cfg.get("viz", {}).get("design_map", {})
    k = int(vc.get("neighbors", 4))
    idx = {g: i for i, g in enumerate(ids)}
    clusters = tables["game-clusters"]["rows"]
    stable = float(cfg.get("clustering", {}).get("stability", {}).get("stable_cluster", 0.75))
    C = len(clusters)
    members = [[idx[g] for g in r["members"]] for r in clusters]
    gcl_i = {}
    for c, ms in enumerate(members):
        for i in ms:
            gcl_i[i] = c
    # k nearest neighbours (ties broken by index)
    nbrs = []
    for i in range(N):
        order = sorted((j for j in range(N) if j != i), key=lambda j: (round(D[i, j], 9), j))
        nbrs.append(order[:k])
    E = sorted({(min(i, j), max(i, j)) for i in range(N) for j in nbrs[i]})
    # 1. islands: cluster positions from mean similarity, discs that may not overlap
    S = np.zeros((C, C))
    for a in range(C):
        for b in range(a + 1, C):
            S[a, b] = S[b, a] = round(float(np.mean([1 - D[i, j] for i in members[a] for j in members[b]])), 6)
    unit = float(vc.get("island_unit", 1.0))
    radii = [unit * (0.9 + 0.55 * math.sqrt(len(ms))) for ms in members]
    golden = math.pi * (3 - math.sqrt(5))
    cpos = np.array([[2.2 * math.sqrt(c + 0.5) * math.cos(c * golden), 2.2 * math.sqrt(c + 0.5) * math.sin(c * golden)] for c in range(C)])
    cpairs = [(a, b) for a in range(C) for b in range(a + 1, C)]
    smax = max(S[a, b] for a, b in cpairs) or 1
    cei = np.array([a for a, b in cpairs])
    cej = np.array([b for a, b in cpairs])
    cew = np.array([(S[a, b] / smax) ** 2 * 0.6 for a, b in cpairs])
    cpos = _fr(np.round(cpos, 4), cei, cej, cew, int(vc.get("island_iterations", 300)), k=2.4, gravity=0.06, radii=radii, temp0=0.8)
    # 2. members inside each island: kNN within the cluster, scaled into the disc
    pos = np.zeros((N, 2))
    for c, ms in enumerate(members):
        if len(ms) == 1:
            pos[ms[0]] = cpos[c]
            continue
        loc = {i: n for n, i in enumerate(ms)}
        p0 = np.array([[0.6 * math.sqrt(n + 0.5) * math.cos(n * golden), 0.6 * math.sqrt(n + 0.5) * math.sin(n * golden)] for n in range(len(ms))])
        intra = sorted({(min(loc[i], loc[j]), max(loc[i], loc[j])) for i in ms for j in nbrs[i] if j in loc})
        if not intra:
            intra = [(n, n + 1) for n in range(len(ms) - 1)]
        ei = np.array([a for a, b in intra])
        ej = np.array([b for a, b in intra])
        ew = np.array([max(0.05, 1 - D[ms[a], ms[b]]) for a, b in intra])
        p = _fr(np.round(p0, 4), ei, ej, ew, 200, k=0.5, gravity=0.15, temp0=0.4)
        p = p - p.mean(0)
        rmax = float(np.sqrt((p ** 2).sum(-1)).max()) or 1
        p = p / rmax * (radii[c] - 0.45 * unit)
        pos[ms] = cpos[c] + p
    W, Hmax, pad, MW = 600, 640, 24, 600
    allp = np.vstack([pos, cpos + np.array(radii)[:, None], cpos - np.array(radii)[:, None]])
    mn, mx = allp.min(0), allp.max(0)
    sc = min((MW - 2 * pad) / (mx[0] - mn[0]), (Hmax - 2 * pad - 16) / (mx[1] - mn[1]))
    H = int(math.ceil((mx[1] - mn[1]) * sc + 2 * pad + 30))  # crop to the islands so narrow screens waste no height
    ox = (MW - (mx[0] - mn[0]) * sc) / 2
    oy = pad + 16
    tx = lambda p: (round((p[0] - mn[0]) * sc + ox, 1), round((p[1] - mn[1]) * sc + oy, 1))
    xy = [tx(p) for p in pos]
    cxy = [tx(p) for p in cpos]
    crad = [r * sc for r in radii]
    body = [svg_open("design-map", W, H, "A map of the design space",
                     f"{N} games drawn as islands, one per cluster from section 5.4. Islands sit near the clusters whose games they most resemble; "
                     f"inside an island, games sit near the games whose mechanics they share.")]
    # bridges: one line per pair of islands joined by nearest-neighbour links, width by count
    bridges = Counter()
    for i, j in E:
        a, b = gcl_i[i], gcl_i[j]
        if a != b:
            bridges[(min(a, b), max(a, b))] += 1
    body.append(f'<g data-layer="bridges" style="stroke:{T["rule2"]};stroke-linecap:round">')
    min_b = int(vc.get("min_bridge_links", 2))
    for (a, b), cnt in sorted(bridges.items()):
        if cnt < min_b:
            continue
        (x1, y1), (x2, y2) = cxy[a], cxy[b]
        body.append(f'<line x1="{f1(x1)}" y1="{f1(y1)}" x2="{f1(x2)}" y2="{f1(y2)}" style="stroke-width:{f1(0.5 * cnt)}" data-n="{cnt}"/>')
    body.append("</g>")
    body.append('<g data-layer="islands">')
    for c, row in enumerate(clusters):
        pts = []
        for i in members[c]:
            x, y = xy[i]
            for a in range(24):
                pts.append((x + 12 * math.cos(a * math.pi / 12), y + 12 * math.sin(a * math.pi / 12)))
        hull = convex_hull(pts)
        d = "M" + "L".join(f"{f1(x)},{f1(y)}" for x, y in hull) + "Z"
        dash = "" if row.get("stability", 1) >= stable else ";stroke-dasharray:3 2"
        body.append(f'<path d="{d}" data-cluster="{row["cluster"]}" style="fill:{T["paper2"]};stroke:{T["rule2"]};stroke-width:1;stroke-linejoin:round{dash}"/>')
    body.append("</g>")
    body.append(f'<g data-layer="edges" style="stroke:{T["rule2"]};stroke-width:0.7">')
    for i, j in E:
        if gcl_i[i] == gcl_i[j]:
            body.append(f'<line x1="{f1(xy[i][0])}" y1="{f1(xy[i][1])}" x2="{f1(xy[j][0])}" y2="{f1(xy[j][1])}"/>')
    body.append("</g>")
    body.append(f'<g data-layer="links" style="stroke:{T["accent"]};stroke-width:1.2"></g>')
    body.append(f'<g data-layer="nodes" style="fill:{T["ink"]};stroke:{T["paper2"]};stroke-width:1.5;paint-order:stroke">')
    for i, gid in enumerate(ids):
        x, y = xy[i]
        body.append(f'<rect x="{f1(x - 3)}" y="{f1(y - 3)}" width="6" height="6" data-i="{i}"/>')
    body.append("</g>")
    # labels: island id and signature under each island, the most central game beside its square
    body.append('<g data-layer="labels">')
    halo = f"paint-order:stroke;stroke:{T['paper']};stroke-width:3px"
    for c, row in enumerate(clusters):
        ys = [xy[i][1] for i in members[c]]
        xs = [xy[i][0] for i in members[c]]
        lx, ly = (min(xs) + max(xs)) / 2, min(ys) - 15
        body.append(f'<text x="{f1(lx)}" y="{f1(ly)}" text-anchor="middle" data-cluster="{row["cluster"]}" style="fill:{T["ink"]};font-size:9px;font-weight:600;{halo}">'
                    f'{esc(row["cluster"].lower())}</text>')
    body.append("</g>")
    body.append(f'<rect data-hl="node" x="0" y="0" width="12" height="12" style="fill:none;stroke:{T["accent"]};stroke-width:1.5" display="none"/>')
    body.append("</svg>")
    gcl = {gid: derived[gid].get("cluster") for gid in ids}
    subs = Counter(by_id[g].data.get("subgenre") for g in ids)
    data = {
        "nodes": [{"id": gid, "name": by_id[gid].data["name"], "year": by_id[gid].data.get("year"), "sub": by_id[gid].data.get("subgenre"),
                   "cluster": gcl[gid], "x": xy[i][0], "y": xy[i][1], "n": nbrs[i]} for i, gid in enumerate(ids)],
        "subgenres": [[s, sub.get(s, {}).get("label", s), c] for s, c in sorted(subs.items(), key=lambda x: (-x[1], x[0]))],
        "clusters": {r["cluster"]: r["label"] for r in clusters},
    }
    key = "".join(f'<dt data-key="{r["cluster"]}"><b>{esc(r["cluster"].lower())}</b> · {r["size"]}</dt><dd data-key="{r["cluster"]}">{esc(r["label"].lower())}'
                  + ("" if r.get("stability", 1) >= stable else " <span class=\"faint\">· unstable</span>") + "</dd>" for r in clusters)
    aside = f'<dl class="receipt" data-style="bare" aria-label="Key to the islands">{key}</dl>'
    opts = "".join(f'<option value="{esc(s)}">{esc(lab)} · {c}</option>' for s, lab, c in data["subgenres"])
    controls = ('<div class="cluster" data-controls="design-map"><label class="field" style="min-width:240px"><span>highlight a subgenre</span>'
                f'<select data-set="subgenre"><option value="">none</option>{opts}</select></label></div>')
    trows = [{"cluster": r["cluster"], "label": r["label"], "size": r["size"], "stability": r.get("stability"), "dominant_subgenres": r["dominant_subgenres"], "members": r["members"]} for r in clusters]
    n_mixed = stats_cross(clusters, by_id)
    return {
        "title": "A map of the design space",
        "head": f"{counted(N, 'game')} · {counted(C, 'island')} · {k} nearest neighbours each",
        "svg": "".join(body),
        "caption": f"One island per cluster ({n_mixed} of {C} mix subgenres). Inside an island, lines join games to their nearest neighbours by shared mechanics "
                   "(inverse-prevalence weighted Jaccard, the measure behind the clustering); bridges join islands whose games are each other's nearest neighbours, wider for more links. "
                   f"Islands sit near the islands they most resemble. A dashed outline marks an island whose games regroup when subsets of the catalog are re-clustered (stability below {stable}). "
                   "Hover or tap a game to see its neighbours; highlight a subgenre to see it spread across islands.",
        "source": "derived.cluster · report/analysis.yaml (clustering, viz.design_map)",
        "controls": controls,
        "legend": legend([("game", "square", "1"), ("island (cluster)", "outline", "1"), ("island not stable under resampling", "outline-dashed", "1"), ("highlighted: neighbours or subgenre", "accent", "1")]),
        "aside": aside,
        "min_width": 520,
        "data": data_script("design-map", data),
        "twin": {"columns": ["cluster", "label", "size", "stability", "dominant_subgenres", "members"], "rows": trows, "link_columns": ["members"],
                 "note": "The clusters behind the islands, members in order of centrality."},
    }


def stats_cross(clusters, by_id):
    return sum(1 for r in clusters if len({by_id[g].data.get("subgenre") for g in r["members"]}) > 1)


def convex_hull(pts):
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


# ======================================================================= 4. vacant lots
def vacant_lots(shared, live, by_id, derived, tables, fam, cfg):
    ws = cfg["whitespace"]
    N = shared["N"]
    prev = shared["prev"]
    pc = shared["pair_count"]
    tension = shared["tension_pairs"]
    excl = set(ws.get("exclude_families", []))
    fam_order = list(fam)
    ms = [m for m in shared["common"] if by_id[m].data["family"] not in excl]
    ms.sort(key=lambda m: (fam_order.index(by_id[m].data["family"]), -prev[m], m))
    vac_all = {(r["mechanic_a"], r["mechanic_b"]): r for r in shared["whitespace_all"]}
    rank = {(r["mechanic_a"], r["mechanic_b"]): i + 1 for i, r in enumerate(shared["whitespace_all"])}
    P, S, AV = 15, 13, 5
    L, TOP = 10, 30
    pos = []
    cur = 0.0
    for i, m in enumerate(ms):
        if i and by_id[m].data["family"] != by_id[ms[i - 1]].data["family"]:
            cur += AV
        pos.append(cur)
        cur += P
    n = len(ms)
    W = int(L + pos[-1] + 200)
    H = int(TOP + pos[-1] + P + 40)
    body = [svg_open("vacant-lots", W, H, "Built and vacant pairs",
                     f"A lower-triangle grid of the {n} most common mechanics. Each lot is a pair: shade shows how often the pair is built relative to chance; "
                     "dashed lots are white space, common mechanics that almost never meet.")]
    lots = []
    pairs = {}
    for i in range(n):
        for j in range(i):
            a, b = sorted((ms[i], ms[j]))
            obs = pc.get((a, b), 0)
            exp = prev[a] * prev[b] / N
            lift = obs / exp if exp else 0
            x, y = L + pos[j], TOP + pos[i]
            key = f"{i}-{j}"
            vac = (a, b) in vac_all
            pairs[key] = [obs, round(exp, 2), round(lift, 2), 1 if vac else 0, rank.get((a, b)) if vac else None, 1 if (a, b) in tension else 0]
            if vac:
                lots.append(f'<rect x="{f1(x + 0.5)}" y="{f1(y + 0.5)}" width="{S - 1}" height="{S - 1}" data-k="{key}" '
                            f'style="fill:{T["paper"]};stroke:{T["open"]};stroke-width:1;stroke-dasharray:2 1.5"/>')
                rk = rank[(a, b)]
                if rk <= 10:
                    lots.append(text(x + S / 2, y + S / 2 + 3, rk, 8, "open", "middle", 600, ' pointer-events="none"'))
            elif (a, b) in tension:
                lots.append(f'<rect x="{f1(x)}" y="{f1(y)}" width="{S}" height="{S}" data-k="{key}" style="fill:{T["paper3"]}"/>'
                            f'<path d="M{f1(x + 2)},{f1(y + S - 2)}L{f1(x + S - 2)},{f1(y + 2)}" pointer-events="none" style="stroke:{T["stop"]};stroke-width:1.2"/>')
            else:
                op = 0.1 if lift < 0.5 else 0.28 if lift < 1 else 0.55 if lift < 2 else 0.9
                lots.append(f'<rect x="{f1(x)}" y="{f1(y)}" width="{S}" height="{S}" data-k="{key}" style="fill:{T["ink"]}" fill-opacity="{op}"/>')
    body.append('<g data-layer="lots">' + "".join(lots) + "</g>")
    # labels along the diagonal: the name of mechanic i sits where row i ends and column i begins
    for i, m in enumerate(ms):
        x = L + (pos[i - 1] + P if i else 0) + 4
        y = TOP + pos[i] + S / 2 + 3
        body.append(f'<text x="{f1(x)}" y="{f1(y)}" data-m="{i}" style="fill:{T["ink2"]};font-size:9px">{esc(by_id[m].data["name"].lower())}</text>')
    # family avenues named once, at the bottom edge
    spans = []
    for i, m in enumerate(ms):
        f = by_id[m].data["family"]
        if not spans or spans[-1][0] != f:
            spans.append([f, i, i])
        spans[-1][2] = i
    body.append(f'<rect data-hl="lot" x="0" y="0" width="{S + 4}" height="{S + 4}" style="fill:none;stroke:{T["accent"]};stroke-width:1.5" display="none"/>')
    body.append("</svg>")
    data = {"m": [[m, by_id[m].data["name"], fam[by_id[m].data["family"]]["label"], prev[m]] for m in ms], "pairs": pairs, "N": N,
            "pos": [round(p, 1) for p in pos], "left": L, "top": TOP, "pitch": P, "size": S}
    controls = ('<div class="cluster" data-controls="vacant-lots"><div class="segmented" role="group" aria-label="Show lots">'
                '<button type="button" data-set="show" data-value="all" aria-pressed="true">all lots</button>'
                '<button type="button" data-set="show" data-value="vacant" aria-pressed="false">vacant only</button></div></div>')
    leg = legend([("built 2x chance or more", "square", "0.9"), ("built 1-2x chance", "square", "0.55"), ("built 0.5-1x", "square", "0.28"),
                  ("built under 0.5x", "square", "0.1"), ("vacant (white space)", "dashed", "1"), ("in design tension", "slash", "1")])
    n_vac = sum(1 for v in pairs.values() if v[3])
    return {
        "title": "Built and vacant lots",
        "head": f"{n} common mechanics · {n * (n - 1) // 2} pairs · {n_vac} vacant",
        "svg": "".join(body),
        "caption": f"Every pair of the {n} mechanics used by at least {ws['min_prevalence_games']} games, laid out like a plan: each lot is a pair, "
                   "darker lots are built more often than chance would predict, dashed lots are white space (different families, no recorded tension, "
                   f"co-occurring at most {ws['max_observed']} time), and slashed lots are pairs recorded as being in design tension. "
                   "Numbers mark the ten largest gaps in the white-space table. Names sit on the diagonal: read a lot by following its row and its column back to the staircase.",
        "source": "dist/analysis/whitespace.csv · dist/analysis/cooccurrence-all.csv · report/analysis.yaml (whitespace)",
        "controls": controls,
        "legend": leg,
        "min_width": 640,
        "data": data_script("vacant-lots", data),
        "twin": {"table": "whitespace", "note": "The white-space pairs ranked by gap. All built pairs with their lift are in cooccurrence-all.csv."},
    }


# ======================================================================= 5. technique flows
def technique_flows(live, by_id, derived, vocabs, fam):
    comp = vocabs["rubrics"]["composites"]["technique_exposure"]
    mat_order = ["shipped-mainstream", "shipped-niche", "prototype", "research"]
    mat_label = vocab_terms(vocabs, "technique_maturity")
    eff_terms = vocab_terms(vocabs, "effect")
    eff_order = list(eff_terms)
    techs = sorted(live["technique"], key=lambda t: t.id)
    flows = Counter()
    wflows = defaultdict(float)
    for t in techs:
        mw = comp["maturity_weights"][t.data["maturity"]]
        for a in t.data.get("affects", []):
            if a["id"] not in by_id:
                continue
            key = (t.id, a["effect"], by_id[a["id"]].data["family"])
            flows[key] += 1
            wflows[key] += mw * comp["effect_weights"][a["effect"]]
    keys = sorted(flows)
    modes = {"edges": {k: float(flows[k]) for k in keys}, "exposure": {k: wflows[k] for k in keys}}
    t_tot = {m: Counter() for m in modes}
    for m, fl in modes.items():
        for (t, e, f), v in fl.items():
            t_tot[m][t] += v
    t_order = sorted(techs, key=lambda t: (mat_order.index(t.data["maturity"]), -t_tot["edges"][t.id], t.id))
    t_ids = [t.id for t in t_order]
    f_tot_e = Counter()
    for (t, e, f), v in modes["edges"].items():
        f_tot_e[f] += v
    f_ids = sorted(fam, key=lambda f: (-f_tot_e[f], list(fam).index(f)))
    e_tot = Counter()
    for (t, e, f), v in modes["edges"].items():
        e_tot[e] += v
    e_ids = sorted(eff_order, key=lambda e: (-e_tot[e], eff_order.index(e)))

    W, H = 880, 820
    XL, XM, XR, NW = 214, 444, 662, 8
    TOP, BOT = 30, 800
    gaps = {"t": 2.5, "e": 10, "f": 5}

    def layout(fl):
        tot_t, tot_e, tot_f = Counter(), Counter(), Counter()
        for (t, e, f), v in fl.items():
            tot_t[t] += v
            tot_e[e] += v
            tot_f[f] += v
        total = sum(fl.values())
        avail = min(BOT - TOP - gaps["t"] * (len(t_ids) - 1), BOT - TOP - gaps["f"] * (len(f_ids) - 1), BOT - TOP - gaps["e"] * (len(e_ids) - 1))
        k = avail / total

        def stack(ids, tot, gap):
            h = sum(tot[i] * k for i in ids) + gap * (len(ids) - 1)
            y = TOP + (BOT - TOP - h) / 2
            out = {}
            for i in ids:
                out[i] = (y, tot[i] * k)
                y += tot[i] * k + gap
            return out
        nt, ne, nf = stack(t_ids, tot_t, gaps["t"]), stack(e_ids, tot_e, gaps["e"]), stack(f_ids, tot_f, gaps["f"])
        # slot order: left by (t, e, f); middle by (e, f, t); right by (f, e, t)
        ks = sorted(fl)
        slot = {}
        cur = {i: nt[i][0] for i in t_ids}
        for key in sorted(ks, key=lambda q: (t_ids.index(q[0]), e_ids.index(q[1]), f_ids.index(q[2]))):
            h = fl[key] * k
            slot[(key, "L")] = (cur[key[0]], h)
            cur[key[0]] += h
        cur = {i: ne[i][0] for i in e_ids}
        for key in sorted(ks, key=lambda q: (e_ids.index(q[1]), f_ids.index(q[2]), t_ids.index(q[0]))):
            h = fl[key] * k
            slot[(key, "M")] = (cur[key[1]], h)
            cur[key[1]] += h
        cur = {i: nf[i][0] for i in f_ids}
        for key in sorted(ks, key=lambda q: (f_ids.index(q[2]), e_ids.index(q[1]), t_ids.index(q[0]))):
            h = fl[key] * k
            slot[(key, "R")] = (cur[key[2]], h)
            cur[key[2]] += h
        paths = {}
        for key in ks:
            (yl, h), (ym, _), (yr, _) = slot[(key, "L")], slot[(key, "M")], slot[(key, "R")]
            a0, a1 = XL + NW, XM
            b0, b1 = XM + NW, XR
            ca, cb = (a1 - a0) * 0.5, (b1 - b0) * 0.5
            d = (f"M{f1(a0)},{f1(yl)}C{f1(a0 + ca)},{f1(yl)} {f1(a1 - ca)},{f1(ym)} {f1(a1)},{f1(ym)}L{f1(b0)},{f1(ym)}"
                 f"C{f1(b0 + cb)},{f1(ym)} {f1(b1 - cb)},{f1(yr)} {f1(b1)},{f1(yr)}L{f1(b1)},{f1(yr + h)}"
                 f"C{f1(b1 - cb)},{f1(yr + h)} {f1(b0 + cb)},{f1(ym + h)} {f1(b0)},{f1(ym + h)}L{f1(a1)},{f1(ym + h)}"
                 f"C{f1(a1 - ca)},{f1(ym + h)} {f1(a0 + ca)},{f1(yl + h)} {f1(a0)},{f1(yl + h)}Z")
            paths[key] = d
        return nt, ne, nf, paths, tot_t, tot_e, tot_f

    lay = {m: layout(fl) for m, fl in modes.items()}
    nt, ne, nf, paths, tot_t, tot_e, tot_f = lay["edges"]
    nt2, ne2, nf2, paths2, tot_t2, tot_e2, tot_f2 = lay["exposure"]
    op = {"shipped-mainstream": "0.75", "shipped-niche": "0.5", "prototype": "0.3", "research": "0.16"}
    tmat = {t.id: t.data["maturity"] for t in techs}
    body = [svg_open("technique-flows", W, H, "Where the techniques land",
                     "Parallel sets: each ribbon is a technique's effect on a family of mechanics, running from the technique (left) through the kind of effect (middle) to the mechanic family (right). "
                     "Ribbon shade shows the technique's maturity in games.")]
    body.append(f'<g data-layer="ribbons" style="fill:{T["s1"]}">')
    for key in sorted(paths, key=lambda q: (-mat_order.index(tmat[q[0]]), q)):
        t, e, f = key
        body.append(f'<path d="{paths[key]}" data-d2="{paths2[key]}" data-t="{t}" data-e="{e}" data-f="{f}" data-v="{int(modes["edges"][key])}" '
                    f'data-v2="{round(modes["exposure"][key], 3)}" fill-opacity="{op[tmat[t]]}"/>')
    body.append("</g>")
    # nodes
    body.append('<g data-layer="nodes">')
    for t in t_ids:
        (y, h), (y2, h2) = nt[t], nt2[t]
        body.append(f'<rect x="{XL}" y="{f1(y)}" width="{NW}" height="{f1(max(h, 0.6))}" data-node="t:{t}" data-y2="{f1(y2)}" data-h2="{f1(max(h2, 0.6))}" '
                    f'style="fill:{T["s1"]}" fill-opacity="{op[tmat[t]]}"/>')
    for e in e_ids:
        (y, h), (y2, h2) = ne[e], ne2[e]
        body.append(f'<rect x="{XM}" y="{f1(y)}" width="{NW}" height="{f1(max(h, 0.6))}" data-node="e:{e}" data-y2="{f1(y2)}" data-h2="{f1(max(h2, 0.6))}" style="fill:{T["ink"]}"/>')
    for f in f_ids:
        (y, h), (y2, h2) = nf[f], nf2[f]
        body.append(f'<rect x="{XR}" y="{f1(y)}" width="{NW}" height="{f1(max(h, 0.6))}" data-node="f:{f}" data-y2="{f1(y2)}" data-h2="{f1(max(h2, 0.6))}" style="fill:{T["ink"]}"/>')
    body.append("</g>")
    # labels
    body.append('<g data-layer="labels">')
    ty = spread([nt[t][0] + nt[t][1] / 2 for t in t_ids], 10, TOP, BOT)
    ty2 = spread([nt2[t][0] + nt2[t][1] / 2 for t in t_ids], 10, TOP, BOT)
    for t, a, b in zip(t_ids, ty, ty2):
        nm = by_id[t].data["name"]
        nm = nm if len(nm) <= 40 else nm[:39].rstrip() + "…"
        body.append(f'<text x="{XL - 6}" y="{f1(a + 3)}" data-y2="{f1(b + 3)}" data-node="t:{t}" text-anchor="end" style="fill:{T["ink2"]};font-size:8.5px">{esc(nm)}</text>')
    for e in e_ids:
        (y, h), (y2, h2) = ne[e], ne2[e]
        body.append(f'<text x="{XM + NW / 2}" y="{f1(y - 4)}" data-y2="{f1(y2 - 4)}" data-node="e:{e}" text-anchor="middle" '
                    f'style="fill:{T["ink"]};font-size:9px;font-weight:600;paint-order:stroke;stroke:{T["paper"]};stroke-width:4px">{esc(eff_terms[e]["label"].lower())}</text>')
    fy = spread([nf[f][0] + nf[f][1] / 2 for f in f_ids], 10.5, TOP, BOT + 10)
    fy2 = spread([nf2[f][0] + nf2[f][1] / 2 for f in f_ids], 10.5, TOP, BOT + 10)
    for f, a, b in zip(f_ids, fy, fy2):
        v, v2 = int(tot_f[f]), round(tot_f2[f], 2)
        body.append(f'<text x="{XR + NW + 6}" y="{f1(a + 3)}" data-y2="{f1(b + 3)}" data-node="f:{f}" data-v="{v}" data-v2="{v2}" style="fill:{T["ink2"]};font-size:9px">'
                    f'{esc(fam[f]["label"].lower())} · <tspan style="fill:{T["faint"]}">{v}</tspan></text>')
    body.append("</g>")
    body.append("</svg>")
    data = {
        "t": {t: [by_id[t].data["name"], mat_label[tmat[t]]["label"], int(tot_t[t]), round(tot_t2[t], 2)] for t in t_ids},
        "e": {e: [eff_terms[e]["label"], int(tot_e[e]), round(tot_e2[e], 2)] for e in e_ids},
        "f": {f: [fam[f]["label"], int(tot_f[f]), round(tot_f2[f], 2)] for f in f_ids},
    }
    controls = ('<div class="cluster" data-controls="technique-flows"><div class="segmented" role="group" aria-label="Ribbon width">'
                '<button type="button" data-set="weight" data-value="edges" aria-pressed="true">width: edges</button>'
                '<button type="button" data-set="weight" data-value="exposure" aria-pressed="false">width: maturity-weighted</button></div></div>')
    leg = legend([(mat_label[m]["label"].lower(), "series", op[m]) for m in mat_order])
    trows = [{"technique": t, "maturity": mat_label[tmat[t]]["label"], "effect": eff_terms[e]["label"], "family": fam[f]["label"], "edges": flows[(t, e, f)]}
             for (t, e, f) in sorted(keys, key=lambda q: (t_ids.index(q[0]), e_ids.index(q[1]), f_ids.index(q[2])))]
    zero = [fam[f]["label"].lower() for f in f_ids if tot_f[f] == 0]
    return {
        "title": "Where the techniques land",
        "head": f"{counted(len(t_ids), 'technique')} · {counted(int(sum(modes['edges'].values())), 'affects edge')} · {counted(len(f_ids), 'family')}",
        "svg": "".join(body),
        "caption": "Each ribbon follows one technique's edges to one mechanic family, through the kind of change it makes. Darker ribbons come from techniques that have shipped in games. "
                   "Hover or tap a technique, an effect, or a family to isolate its ribbons; switch the width to weight each edge by maturity and effect, the exposure measure of §8.2."
                   + (f" Families with no ribbon: {', '.join(zero)}." if zero else ""),
        "source": "affects edges in data/techniques/*.yaml · weights vocab/rubrics.yaml (technique_exposure)",
        "controls": controls,
        "legend": leg,
        "min_width": 760,
        "data": data_script("technique-flows", data),
        "twin": {"columns": ["technique", "maturity", "effect", "family", "edges"], "rows": trows, "link_columns": ["technique"],
                 "note": "Every ribbon: technique, kind of effect, mechanic family, and the number of affects edges it carries."},
    }


# ======================================================================= book figures (chapters 2, 6, 7, 10, 11, 12, 13)
# Static figures: every value is printed or carried in a <title> tooltip, so they need no site script.

def short(name: str, n: int = 40) -> str:
    s = name.split(" (")[0]
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _plain(title, head, svg, caption, source, twin, min_width=640, legend_html=""):
    return {"title": title, "head": head, "svg": svg, "caption": caption, "source": source, "controls": "", "legend": legend_html,
            "min_width": min_width, "data": "", "twin": twin}


def _key(items):
    """items: (label, svg-mark) pairs for a legend row."""
    return '<div class="legend">' + "".join(f'<span><svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">{mark}</svg>{esc(lab)}</span>'
                                             for lab, mark in items) + "</div>"


DET_MARK = {
    "preserves": lambda x, y: f'<circle cx="{f1(x)}" cy="{f1(y)}" r="3.2" style="fill:{T["ink"]}"/>',
    "mitigable": lambda x, y: f'<circle cx="{f1(x)}" cy="{f1(y)}" r="3" style="fill:{T["paper"]};stroke:{T["accent"]};stroke-width:1.3"/>',
    "breaks": lambda x, y: f'<rect x="{f1(x - 3)}" y="{f1(y - 3)}" width="6" height="6" style="fill:{T["stop"]}"/>',
}
DET_LABEL = {"preserves": "preserves reproducibility", "mitigable": "reproducible if seeded, cached, or logged", "breaks": "breaks reproducibility"}


def layer_profile(tables, fam, sub, cfg):
    smin = (cfg.get("book") or {}).get("subgenre_min_games", 6)
    t = tables["family-by-subgenre"]
    rows = sorted((r for r in t["rows"] if r["games"] >= smin), key=lambda r: (-r["games"], r["subgenre"]))
    fams = [f for f in fam]
    overall = {f: float(np.mean([r.get(f, 0) or 0 for r in rows])) for f in fams}
    fams = sorted(fams, key=lambda f: (-overall[f], fams.index(f)))
    fams = [f for f in fams if max((r.get(f, 0) or 0) for r in rows) > 0]
    vmax = max((r.get(f, 0) or 0) for r in rows for f in fams)
    LBL, TOP, CW_, RH = 190, 150, 31, 24
    W = LBL + CW_ * len(fams) + 150
    H = TOP + RH * len(rows) + 30
    body = [svg_open("layer-profile", W, H, "Where each subgenre spends its mechanics",
                     "Grid of subgenres by mechanic family; shading is the share of the subgenre's mechanic uses in that family.")]
    for j, f in enumerate(fams):
        x = LBL + j * CW_ + CW_ / 2
        body.append(f'<text transform="translate({f1(x + 3)},{TOP - 8}) rotate(-50)" style="fill:{T["muted"]};font-size:9px">{esc(fam[f]["label"].lower())}</text>')
    for i, r in enumerate(rows):
        y = TOP + i * RH
        lab = sub.get(r["subgenre"], {}).get("label", r["subgenre"])
        body.append(text(LBL - 10, y + RH / 2 + 3, f"{lab.lower()} · {r['games']}", 9, "ink2", "end"))
        for j, f in enumerate(fams):
            v = r.get(f, 0) or 0
            x = LBL + j * CW_
            op = 0.04 + 0.86 * (v / vmax) if v > 0 else 0
            tip = f"{lab}: {fam[f]['label']} {round(100 * v)}% of mechanic uses"
            body.append(f'<rect x="{f1(x + 1)}" y="{f1(y + 1)}" width="{CW_ - 2}" height="{RH - 2}" data-subgenre="{r["subgenre"]}" data-family="{f}" '
                        f'style="fill:{T["ink"]};fill-opacity:{op:.3f};stroke:{T["rule"]};stroke-width:0.5"><title>{esc(tip)}</title></rect>')
            if v >= 0.10:
                fill = "paper" if v / vmax > 0.55 else "ink"
                body.append(text(x + CW_ / 2, y + RH / 2 + 3, round(100 * v), 9, fill, "middle"))
    body.append(text(LBL, H - 10, "printed: share of uses, in percent, where 10 or more", 9, "faint"))
    body.append("</svg>")
    return _plain("Where each subgenre spends its mechanics", f"{counted(len(rows), 'subgenre')} · {counted(len(fams), 'family')}", "".join(body),
                  f"Share of each subgenre's mechanic uses that falls in each mechanic family, for subgenres with at least {smin} catalog games. "
                  "Darker cells take a larger share; shares of 10 percent or more are printed. Families are ordered by their average share.",
                  "tables family-by-subgenre · dist/analysis/family-by-subgenre.csv",
                  {"table": "subgenre-spend", "note": "The three families that take the largest share of each subgenre's mechanic uses. Every share is in family-by-subgenre.csv."},
                  min_width=720)


def constraint_profile(live, fam):
    mechs = [m for m in sorted(live["mechanic"], key=lambda m: m.id) if not m.data.get("deprecated")]
    scores = [("authoring_cost", "authoring cost", "higher costs more to author"), ("compute_cost", "compute cost", "higher costs more to run"),
              ("tuning_difficulty", "tuning difficulty", "higher is harder to balance"), ("legibility", "legibility", "higher is easier to read")]
    fams = [f for f in fam if any(m.data["family"] == f for m in mechs)]
    means = {f: {s: float(np.mean([m.data[s] for m in mechs if m.data["family"] == f])) for s, _, _ in scores} for f in fams}
    count = {f: sum(1 for m in mechs if m.data["family"] == f) for f in fams}
    fams = sorted(fams, key=lambda f: (-means[f]["compute_cost"] - means[f]["authoring_cost"], f))
    LBL, TOP, PW, GAP, RH = 200, 52, 146, 26, 19
    W = LBL + len(scores) * (PW + GAP) + 10
    H = TOP + RH * len(fams) + 24
    body = [svg_open("constraint-profile", W, H, "Ceiling scores by family",
                     "Mean rubric score of each family's mechanics on authoring cost, compute cost, tuning difficulty, and legibility, on a 1 to 5 scale.")]
    for k, (s, lab, note) in enumerate(scores):
        x0 = LBL + k * (PW + GAP)
        sx = lambda v, x0=x0: x0 + (v - 1) / 4 * PW
        body.append(text(x0, 18, lab, 9, "ink2", weight="600"))
        body.append(text(x0, 31, note, 8, "faint"))
        for v in range(1, 6):
            body.append(f'<line x1="{f1(sx(v))}" y1="{TOP - 8}" x2="{f1(sx(v))}" y2="{H - 22}" style="stroke:{T["rule"]};stroke-width:{0.9 if v == 3 else 0.5}"/>')
            body.append(text(sx(v), H - 10, v, 8, "faint", "middle"))
        for i, f in enumerate(fams):
            y = TOP + i * RH + RH / 2
            v = means[f][s]
            body.append(f'<line x1="{f1(sx(1))}" y1="{f1(y)}" x2="{f1(sx(v))}" y2="{f1(y)}" style="stroke:{T["rule2"]};stroke-width:1"/>')
            hot = (s != "legibility" and v >= 3) or (s == "legibility" and v < 3.3)
            body.append(f'<circle cx="{f1(sx(v))}" cy="{f1(y)}" r="3.6" style="fill:{T["accent"] if hot else T["ink"]}">'
                        f'<title>{esc(fam[f]["label"])}: mean {lab} {v:.1f} over {counted(count[f], 'mechanic')}</title></circle>')
    for i, f in enumerate(fams):
        y = TOP + i * RH + RH / 2
        body.append(text(LBL - 10, y + 3, f'{fam[f]["label"].lower()} · {count[f]}', 9, "ink2", "end"))
    body.append("</svg>")
    trows = [{"family": fam[f]["label"], "mechanics": count[f], **{s: round(means[f][s], 2) for s, _, _ in scores}} for f in fams]
    return _plain("Ceiling scores by family", f"{counted(len(fams), 'family')} · {counted(len(mechs), 'mechanic')}", "".join(body),
                  "Mean rubric score of each family's mechanics on four of the five ceilings; determinism is a property of techniques and has its own figure. "
                  "Blue marks a family at 3 or above on a cost, or below 3.3 on legibility. Families are ordered by combined compute and authoring cost.",
                  "mechanic rubric scores · dist/entities/mechanics.json",
                  {"columns": ["family", "mechanics"] + [s for s, _, _ in scores], "rows": trows, "link_columns": [],
                   "note": "Mean score per family, 1 to 5."}, min_width=720)


def technique_landscape(live, vocabs):
    techs = [t for t in sorted(live["technique"], key=lambda t: t.id) if not t.data.get("deprecated")]
    mat_label = vocab_terms(vocabs, "technique_maturity")
    order = ["research", "prototype", "shipped"]
    grp = lambda t: "shipped" if t.data["maturity"].startswith("shipped") else t.data["maturity"]
    cols = {m: sorted((t for t in techs if grp(t) == m), key=lambda t: (t.data.get("year") or 0, t.id)) for m in order}
    mat_label = {**mat_label, "shipped": {"label": "Shipped in games"}}
    CWID, TOP, RH = 296, 46, 15
    W = CWID * len(order) + 10
    H = TOP + RH * max(len(v) for v in cols.values()) + 16
    body = [svg_open("technique-landscape", W, H, "Techniques by maturity in games",
                     "Every technique in the dataset listed under how far it has got in games, oldest result first, marked by its effect on reproducibility.")]
    for k, m in enumerate(order):
        x0 = 8 + k * CWID
        body.append(text(x0, 18, f'{mat_label.get(m, {}).get("label", m).lower()} · {len(cols[m])}', 9, "ink2", weight="600"))
        body.append(f'<line x1="{x0}" y1="26" x2="{x0 + CWID - 14}" y2="26" style="stroke:{T["rule2"]}"/>')
        for i, t in enumerate(cols[m]):
            y = TOP + i * RH
            det = t.data.get("determinism_impact", "preserves")
            body.append(DET_MARK[det](x0 + 4, y - 3))
            body.append(f'<text x="{x0 + 12}" y="{y}" style="fill:{T["ink2"] if m.startswith("shipped") else T["muted"]};font-size:8.5px">'
                        f'<title>{esc(t.data["name"])} ({t.data.get("year")}, {t.data["maturity"]}): {DET_LABEL[det]}</title>{esc(t.data.get("year"))} {esc(short(t.data["name"], 44))}'
                        f'{" · norm" if t.data["maturity"] == "shipped-mainstream" else ""}</text>')
    body.append("</svg>")
    trows = [{"technique": t.id, "year": t.data.get("year"), "maturity": t.data["maturity"], "determinism": t.data.get("determinism_impact")} for m in order for t in cols[m]]
    n_ship = len(cols["shipped"])
    key = _key([(DET_LABEL[d], DET_MARK[d](5, 5)) for d in ("preserves", "mitigable", "breaks")])
    return _plain("Techniques by maturity in games", f"{counted(len(techs), 'technique')} · {n_ship} shipped", "".join(body),
                  "Every technique in the dataset under how far it has got in games, each with the year of the result the dataset cites, oldest first; the one shipped technique that is a norm across studios is marked. "
                  "The mark shows what the technique does to reproducibility when it runs.",
                  "technique records · dist/entities/techniques.json", {"columns": ["technique", "year", "maturity", "determinism"], "rows": trows,
                                                                        "link_columns": ["technique"], "note": "Every technique with its maturity in games and its effect on reproducibility."},
                  min_width=860, legend_html=key)


def determinism_runtime(live, vocabs):
    rt = {"server-realtime", "client-realtime"}
    techs = [t for t in sorted(live["technique"], key=lambda t: t.id) if not t.data.get("deprecated") and set(t.data.get("runtime", [])) & rt]
    mat_rank = {"shipped-mainstream": 0, "shipped-niche": 1, "prototype": 2, "research": 3}
    order = ["preserves", "mitigable", "breaks"]
    cols = {d: sorted((t for t in techs if t.data.get("determinism_impact") == d), key=lambda t: (mat_rank[t.data["maturity"]], t.id)) for d in order}
    CWID, TOP, RH = 290, 46, 15
    W = CWID * 3 + 10
    H = TOP + RH * max(len(v) for v in cols.values()) + 16
    body = [svg_open("determinism-runtime", W, H, "What runtime techniques do to reproducibility",
                     "Techniques that can run during play, grouped by their effect on reproducibility; shipped ones first and in dark text.")]
    for k, d in enumerate(order):
        x0 = 8 + k * CWID
        body.append(DET_MARK[d](x0 + 4, 15))
        body.append(text(x0 + 12, 18, f"{DET_LABEL[d]} · {len(cols[d])}", 9, "ink2", weight="600"))
        body.append(f'<line x1="{x0}" y1="26" x2="{x0 + CWID - 14}" y2="26" style="stroke:{T["rule2"]}"/>')
        for i, t in enumerate(cols[d]):
            y = TOP + i * RH
            shipped = t.data["maturity"].startswith("shipped")
            tag = "shipped" if shipped else t.data["maturity"]
            body.append(f'<text x="{x0}" y="{y}" style="fill:{T["ink"] if shipped else T["muted"]};font-size:8.5px{";font-weight:600" if shipped else ""}">'
                        f'<title>{esc(t.data["name"])}: {tag}</title>{esc(short(t.data["name"], 44))}</text>')
    body.append("</svg>")
    trows = [{"technique": t.id, "determinism": d, "maturity": t.data["maturity"]} for d in order for t in cols[d]]
    return _plain("What runtime techniques do to reproducibility", f"{counted(len(techs), 'technique')} that run during play", "".join(body),
                  "Techniques that can run during play, on a server or the player's device, grouped by what they do to reproducibility. "
                  "Within each group, shipped techniques come first and are set in dark text.",
                  "technique records · runtime and determinism_impact", {"columns": ["technique", "determinism", "maturity"], "rows": trows, "link_columns": ["technique"],
                                                                        "note": "Runtime techniques by effect on reproducibility and maturity."}, min_width=860)


def opportunity_priorities(live, tables):
    rows = {r["opportunity"]: r for r in tables["opportunities-ranked"]["rows"]}
    opps = [o for o in sorted(live["opportunity"], key=lambda o: o.id) if not o.data.get("deprecated") and o.id in rows]
    cells = defaultdict(list)
    for o in opps:
        cells[(o.data["impact"], o.data["feasibility"])].append(o)
    imps = sorted({k[0] for k in cells}, reverse=True)
    feas = sorted({k[1] for k in cells})
    for k in cells:
        cells[k].sort(key=lambda o: (-rows[o.id]["priority"], o.id))
    LBL, TOP, CWID, RH = 60, 40, 205, 13
    hts = {i: max(len(cells.get((i, f), [])) for f in feas) for i in imps}
    W = LBL + CWID * len(feas) + 10
    H = TOP + sum(hts[i] * RH + 22 for i in imps) + 30
    top8 = sorted(opps, key=lambda o: (-rows[o.id]["priority"], o.id))[:8]
    body = [svg_open("opportunity-priorities", W, H, "Where the bets sit on impact and feasibility",
                     "Opportunities placed by their impact and feasibility scores; each cell lists its opportunities with their novelty score.")]
    for j, f in enumerate(feas):
        body.append(text(LBL + j * CWID + CWID / 2, TOP - 14, f"feasibility {f}", 9, "ink2", "middle", "600"))
    y = TOP
    for i in imps:
        h = hts[i] * RH + 22
        body.append(text(LBL - 10, y + 14, f"impact {i}", 9, "ink2", "end", "600"))
        for j, f in enumerate(feas):
            x = LBL + j * CWID
            body.append(f'<rect x="{x + 2}" y="{y}" width="{CWID - 4}" height="{h - 4}" style="fill:{T["paper2"]};stroke:{T["rule"]};stroke-width:0.6"/>')
            for k, o in enumerate(cells.get((i, f), [])):
                lead = o in top8
                body.append(f'<text x="{x + 8}" y="{f1(y + 14 + k * RH)}" style="fill:{T["accent"] if lead else T["ink2"]};font-size:8.5px{";font-weight:600" if lead else ""}">'
                            f'<title>{esc(o.data["name"])}: priority {rows[o.id]["priority"]}, novelty {o.data["novelty"]}, horizon {o.data["horizon"]}</title>'
                            f'{o.data["novelty"]} {esc(short(o.data["name"], 33))}</text>')
        y += h
    body.append(text(LBL, H - 10, "number before each name: novelty score · blue: the eight highest priorities", 9, "faint"))
    body.append("</svg>")
    return _plain("Where the bets sit on impact and feasibility", f"{counted(len(opps), 'opportunity')}", "".join(body),
                  "Each opportunity placed by its impact and feasibility scores, with its novelty score before its name. "
                  "Blue names are the eight highest priorities, the weighted geometric mean of the three scores. Scores come from one rater's reading of anchor text.",
                  "tables opportunities-ranked · dist/analysis/opportunities-ranked.csv",
                  {"table": "opportunities-ranked", "note": "Every opportunity with its scores and composite priority."}, min_width=860)


def prediction_timeline(live):
    opps = [o for o in sorted(live["opportunity"], key=lambda o: o.id) if not o.data.get("deprecated")]
    by = defaultdict(list)
    for o in opps:
        by[str(o.data["falsifiable_signal"]["resolve_by"])].append(o)
    dates = sorted(by)
    for d in dates:
        by[d].sort(key=lambda o: o.data["name"])
    CWID, TOP, RH, PER = 292, 52, 14, 3
    W = CWID * PER + 10
    bands = [dates[i:i + PER] for i in range(0, len(dates), PER)]
    band_h = [TOP + RH * max(len(by[d]) for d in b) + 10 for b in bands]
    H = sum(band_h) + 10
    body = [svg_open("prediction-timeline", W, H, "When the predictions come due",
                     "Every opportunity's prediction placed under its resolve-by date.")]
    y0 = 0
    for b, bh in zip(bands, band_h):
        for k, d in enumerate(b):
            x0 = 8 + k * CWID
            body.append(text(x0, y0 + 18, d, 9, "ink2", weight="600"))
            body.append(text(x0, y0 + 31, f"{len(by[d])} due", 8, "faint"))
            body.append(f'<line x1="{x0}" y1="{y0 + 38}" x2="{x0 + CWID - 14}" y2="{y0 + 38}" style="stroke:{T["rule2"]}"/>')
            for i, o in enumerate(by[d]):
                out = (o.data.get("falsifiable_signal", {}).get("resolution") or {}).get("outcome", "open")
                body.append(f'<text x="{x0}" y="{y0 + TOP + i * RH}" style="fill:{T["ink2"]};font-size:8.5px"><title>{esc(o.data["name"])}: '
                            f'{esc(o.data["falsifiable_signal"]["prediction"])} ({out})</title>{esc(short(o.data["name"], 46))}</text>')
        y0 += bh
    body.append("</svg>")
    trows = [{"resolve_by": d, "opportunity": o.id} for d in dates for o in by[d]]
    return _plain("When the predictions come due", f"{counted(len(opps), 'prediction')} · {dates[0]} to {dates[-1]}", "".join(body),
                  "Every opportunity's prediction under the date by which it must be resolved. None has been resolved yet; a resolution needs a run by a different operator and model from the one that wrote the bet.",
                  "opportunity records · falsifiable_signal.resolve_by", {"columns": ["resolve_by", "opportunity"], "rows": trows, "link_columns": ["opportunity"],
                                                                         "note": "Each prediction's resolve-by date."}, min_width=860)


def pipeline(live, stats):
    n = {t: sum(1 for e in live.get(t, []) if not e.data.get("deprecated")) for t in ("game", "mechanic", "technique", "opportunity", "source")}
    W, H = 880, 300
    body = [svg_open("pipeline", W, H, "From records to every product",
                     "Records in plain text pass the validator, feed the analysis, and render into the paper, the site, the wiki, the book, and the video scripts; assertions in the prose are checked on every build.")]

    def box(x, y, w, h, title, sub, strong=False):
        st = f"fill:{T['paper2']};stroke:{T['ink'] if strong else T['rule2']};stroke-width:{1.2 if strong else 0.8}"
        return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" style="{st}"/>' + text(x + 10, y + 18, title, 10, "ink", weight="600")
                + "".join(text(x + 10, y + 32 + 12 * i, s, 8.5, "muted") for i, s in enumerate(sub)))

    def arrow(x1, y1, x2, y2):
        return (f'<path d="M{x1},{y1} L{x2},{y2}" style="fill:none;stroke:{T["ink2"]};stroke-width:1"/>'
                f'<path d="M{x2},{y2} l-6,-3 l0,6 z" transform="rotate({f1(math.degrees(math.atan2(y2 - y1, x2 - x1)))} {x2} {y2})" style="fill:{T["ink2"]}"/>')

    body.append(box(10, 40, 180, 110, "records", [counted(n[t], t) for t in ("game", "mechanic", "technique", "opportunity", "source")], True))
    body.append(box(10, 175, 180, 70, "run log", ["who operated each change", "model, harness, method", "append-only"]))
    body.append(box(240, 40, 170, 95, "validator", ["schemas and vocabularies", "provenance and independence", "sources and quotes", "fails the build"]))
    body.append(box(460, 40, 170, 95, "analysis", ["prevalence, clusters", "white space, exposure", "priorities, figures", "deterministic"]))
    body.append(box(460, 175, 170, 70, "assertions", ["every interpretive sentence", "checked against the data", "fails the build"], True))
    outs = ["paper", "site and wiki", "book", "episode scripts", "shorts and film"]
    for i, o in enumerate(outs):
        y = 22 + i * 52
        body.append(box(690, y, 180, 40, o, []))
        body.append(arrow(632, 88, 686, y + 20))
    body.append(arrow(192, 88, 236, 88))
    body.append(arrow(412, 88, 456, 88))
    body.append(arrow(100, 172, 100, 154))
    body.append(arrow(545, 172, 545, 139))
    body.append(text(240, 280, "every edition names the dataset version it was built from", 9, "faint"))
    body.append("</svg>")
    trows = [{"stage": "records", "what": ", ".join(counted(v, k) for k, v in n.items())}, {"stage": "validator", "what": "schemas, vocabularies, provenance, sources"},
             {"stage": "analysis", "what": "derived values, tables, figures"}, {"stage": "assertions", "what": "prose checked against the data on every build"},
             {"stage": "outputs", "what": ", ".join(outs)}]
    return _plain("From records to every product", "one dataset · five products", "".join(body),
                  "Records pass the validator and feed one deterministic analysis; the paper, the site, the wiki, the book, and the scripts all render from it, and every interpretive sentence in them carries an assertion the build checks.",
                  "scripts/build.py · CONTRACT.md", {"columns": ["stage", "what"], "rows": trows, "link_columns": [], "note": "The stages of the build."}, min_width=760)


def cluster_k_curve(tables, cfg):
    """How well subsample re-clusterings agree with the full clustering at each k, with the spread across subsamples
    and the share of games in the largest cluster, marking the selection threshold and the configured k (review G5)."""
    rows = tables["cluster-stability"]["rows"]
    st = cfg["clustering"]["stability"]
    thr, k_cfg = float(st["min_mean_ari"]), int(cfg["clustering"]["k"])
    ks = [r["k"] for r in rows]
    L, R, TOP, BOT, W, H = 56, 16, 22, 44, 680, 300
    lo = min(0.0, math.floor(min(r["p10_ari"] for r in rows) * 10) / 10)
    sx = lambda k: L + (k - ks[0]) / max(ks[-1] - ks[0], 1) * (W - L - R)  # noqa: E731
    sy = lambda v: TOP + (1.0 - v) / (1.0 - lo) * (H - TOP - BOT)  # noqa: E731
    body = [svg_open("cluster-k-curve", W, H, "Agreement under resampling, by number of clusters",
                     "Mean adjusted Rand index between the full clustering and subsample re-clusterings for each k, with the 10th to 90th "
                     "percentile band, the share of games in the largest cluster, the selection threshold, and the configured k.")]
    for v in [x / 4 for x in range(int(math.ceil(lo * 4)), 5)]:
        body.append(f'<line x1="{L}" y1="{f1(sy(v))}" x2="{W - R}" y2="{f1(sy(v))}" style="stroke:{T["rule"]};stroke-width:0.6"/>')
        body.append(text(L - 8, sy(v) + 3, f"{v:g}", 9, "faint", "end"))
    for k in ks:
        if k % 2 == 0:
            body.append(text(sx(k), H - BOT + 14, k, 9, "faint", "middle"))
    band = [(sx(r["k"]), sy(r["p90_ari"])) for r in rows] + [(sx(r["k"]), sy(r["p10_ari"])) for r in reversed(rows)]
    body.append(f'<polygon points="{" ".join(f"{f1(x)},{f1(y)}" for x, y in band)}" style="fill:{T["ink"]};fill-opacity:0.1;stroke:none"/>')
    body.append(f'<line x1="{L}" y1="{f1(sy(thr))}" x2="{W - R}" y2="{f1(sy(thr))}" style="stroke:{T["accent"]};stroke-width:1;stroke-dasharray:4 3"/>')
    body.append(text(L + 4, sy(thr) - 5, f"selection threshold {thr:g}", 9, "accent"))
    if k_cfg in ks:
        body.append(f'<line x1="{f1(sx(k_cfg))}" y1="{TOP}" x2="{f1(sx(k_cfg))}" y2="{H - BOT}" style="stroke:{T["ink2"]};stroke-width:0.8"/>')
        body.append(text(sx(k_cfg) + 4, TOP + 10, f"configured k = {k_cfg}", 9, "ink2"))
    share = " ".join(f"{f1(sx(r['k']))},{f1(sy(r['largest_cluster_share']))}" for r in rows)
    body.append(f'<polyline points="{share}" style="fill:none;stroke:{T["open"]};stroke-width:1.2;stroke-dasharray:2 2"/>')
    # label the dotted line in the plot itself, so the static figure reads without the site's legend
    lab_r = min(rows, key=lambda r: (abs(r["k"] - (ks[0] + ks[-1]) / 3), r["k"]))
    body.append(text(sx(lab_r["k"]), sy(lab_r["largest_cluster_share"]) - 6, "largest cluster's share of games", 9, "open"))
    mean = " ".join(f"{f1(sx(r['k']))},{f1(sy(r['mean_ari']))}" for r in rows)
    body.append(f'<polyline points="{mean}" style="fill:none;stroke:{T["ink"]};stroke-width:1.6"/>')
    for r in rows:
        body.append(f'<circle cx="{f1(sx(r["k"]))}" cy="{f1(sy(r["mean_ari"]))}" r="2.4" style="fill:{T["ink"]}">'
                    f'<title>k = {r["k"]}: mean ARI {r["mean_ari"]}, 10th to 90th percentile {r["p10_ari"]} to {r["p90_ari"]}, '
                    f'largest cluster {round(100 * r["largest_cluster_share"])}% of games</title></circle>')
    body.append(text((L + W - R) / 2, H - 10, "number of clusters, k", 9, "muted", "middle"))
    body.append(f'<text transform="translate(14,{f1((TOP + H - BOT) / 2)}) rotate(-90)" text-anchor="middle" style="fill:{T["muted"]};font-size:9px">'
                f'adjusted Rand index, or share of games</text>')
    body.append("</svg>")
    key = _key([("mean ARI, subsample against full clustering", f'<path d="M0 5H10" style="stroke:{T["ink"]};stroke-width:1.6"/>'),
                ("10th to 90th percentile across subsamples", f'<rect width="10" height="10" style="fill:{T["ink"]};fill-opacity:0.15"/>'),
                ("share of games in the largest cluster", f'<path d="M0 5H10" style="stroke:{T["open"]};stroke-width:1.2;stroke-dasharray:2 2"/>'),
                ("selection threshold", f'<path d="M0 5H10" style="stroke:{T["accent"]};stroke-width:1;stroke-dasharray:4 3"/>')])
    return _plain("Agreement under resampling, by number of clusters", f"k = {ks[0]} to {ks[-1]} · {st['subsamples']} subsamples", "".join(body),
                  f"For each number of clusters k, the adjusted Rand index between the full clustering and the re-clustering of each of {st['subsamples']} subsamples "
                  f"of about {round(100 * float(st['fraction']))} percent of the games: the line is the mean, the band runs from the 10th to the 90th percentile. "
                  f"The dotted line is the share of games in the largest cluster. The rule picks the smallest k whose mean reaches {thr:g} (dashed line); the vertical line marks the configured k.",
                  "tables cluster-stability · dist/analysis/cluster-stability.csv · report/analysis.yaml (clustering)",
                  {"table": "cluster-stability", "note": "Mean, 10th and 90th percentile ARI and the largest cluster's share of games, for every k."},
                  min_width=640, legend_html=key)
