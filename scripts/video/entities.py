"""Entity index from the built dataset: games, mechanics, techniques, opportunities, with matchers for narration text."""
import json, os, re
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'dist', 'entities') + os.sep
SUBG = lambda s: (s or '').replace('-', ' ')
STOP_GAMES = {'foundation', 'eco'}
# Record aliases too broad for narration: "AI research" is not a tech tree, "shares a family" not equity buyouts, "gets the credit" not a loan.
STOP_ALIASES = {'research', 'shares', 'supply', 'reports', 'event log', 'letters', 'graphs', 'logistics', 'credit'}


EXTRA = {  # informal names the narration uses -> (kind, id)
 "storyteller": ("mechanic","storyteller-director"), "drama manager": ("mechanic","storyteller-director"),
 "mood breaks": ("mechanic","mood-breakdown"), "mood break": ("mechanic","mood-breakdown"), "breakdown": ("mechanic","mood-breakdown"),
 "injuries by body part": ("mechanic","injury-body-model"), "body-part injuries": ("mechanic","injury-body-model"), "bodies made of parts": ("mechanic","injury-body-model"), "bodies made of layered tissue": ("mechanic","injury-body-model"),
 "pause button": ("mechanic","variable-speed"), "placing buildings": ("mechanic","free-placement"), "building placement": ("mechanic","free-placement"), "free placement": ("mechanic","free-placement"),
 "mod support": ("mechanic","modding-api"), "mods": ("mechanic","modding-api"), "tech tree": ("mechanic","tech-tree"), "technology tree": ("mechanic","tech-tree"),
 "scenario goals": ("mechanic","scenario-objectives"), "needs that decay": ("mechanic","needs-decay"), "needs run down": ("mechanic","needs-decay"),
 "conveyor belts": ("mechanic","conveyor-transport"), "conveyor belt": ("mechanic","conveyor-transport"), "belts": ("mechanic","conveyor-transport"),
 "crop growing": ("mechanic","crop-cultivation"), "crops": ("mechanic","crop-cultivation"), "pollution": ("mechanic","pollution-spread"),
 "traffic": ("mechanic","traffic-congestion"), "crime": ("mechanic","crime-policing"), "gossip": ("mechanic","gossip-propagation"),
 "work grid": ("mechanic","work-priorities"), "generated terrain": ("mechanic","procedural-terrain"), "friendship": ("mechanic","relationship-values"),
 "dynasties": ("mechanic","dynasty-succession"), "religious conversion": ("mechanic","culture-religion-conversion"), "war score": ("mechanic","war-score-peace"),
 "document checks": ("mechanic","rule-checking-inspection"), "threat budget": ("mechanic","adaptive-threat-scaling"), "danger that grows with wealth": ("mechanic","adaptive-threat-scaling"),
 "memories": ("mechanic","memories-thoughts"), "work priorities": ("mechanic","work-priorities"), "zoning": ("mechanic","zoning"),
 "language model": ("technique","llm-game-master"), "language models": ("technique","llm-game-master"), "world model": ("technique","genie-world-models"), "world models": ("technique","genie-world-models"),
 "tree search": ("technique","monte-carlo-tree-search"), "neural upscaling": ("technique","neural-rendering-shaders"), "frame generation": ("technique","neural-rendering-shaders"),
 "wave function collapse": ("technique","wave-function-collapse"), "Generative Agents": ("game","generative-agents-smallville"),
}

def load():
    live = lambda name: [x for x in json.load(open(D + name)) if not x.get('deprecated')]  # deprecated records stay in the data, not on screen
    G = live('games.json'); M = live('mechanics.json'); T = live('techniques.json'); O = live('opportunities.json')
    mech = {m['id']: m for m in M}
    order = sorted(M, key=lambda m: (-m['_derived'].get('prevalence', 0), m['id']))
    col = {m['id']: i for i, m in enumerate(order)}
    games = {}
    for g in G:
        row = [(col[x['id']], x.get('role') == 'core') for x in g.get('mechanics', []) if x['id'] in col]
        core = [x['id'] for x in g.get('mechanics', []) if x.get('role') == 'core']
        rare = sorted(core, key=lambda i: mech[i]['_derived'].get('prevalence', 0))[:3]
        games[g['id']] = {'kind': 'game', 'id': g['id'], 'name': g['name'], 'year': g.get('year'), 'dev': g.get('developer', ''),
                          'sub': SUBG(g.get('subgenre')), 'n': len(g.get('mechanics', [])), 'core': len(core), 'row': row,
                          'rare': [[mech[i]['name'], mech[i]['_derived'].get('prevalence', 0)] for i in rare], 'summary': g.get('summary', '')}
    mechs = {}
    first_name = {g['id']: g['name'] for g in G}
    for m in M:
        d = m['_derived']
        mechs[m['id']] = {'kind': 'mechanic', 'id': m['id'], 'name': m['name'], 'family': m['family'].replace('-', ' '),
                          'n': d.get('prevalence', 0), 'year': d.get('earliest_year'), 'first': first_name.get(d.get('earliest_game'), ''),
                          'col': col[m['id']], 'summary': m.get('summary', '')}
    techs = {t['id']: {'kind': 'technique', 'id': t['id'], 'name': t['name'], 'maturity': t.get('maturity', '').replace('-', ' '),
                       'year': t.get('year'), 'det': t.get('determinism_impact', ''), 'cat': t.get('category', '').replace('-', ' '), 'summary': t.get('summary', '')} for t in T}
    rank = {o['id']: i + 1 for i, o in enumerate(sorted(O, key=lambda o: (-o['_derived'].get('priority', 0), o['id'])))}
    opps = {o['id']: {'kind': 'bet', 'id': o['id'], 'name': o['name'], 'rank': rank[o['id']], 'n': len(O), 'priority': o['_derived'].get('priority'),
                      'horizon': o.get('horizon', ''), 'impact': o.get('impact'), 'feas': o.get('feasibility'), 'nov': o.get('novelty'), 'summary': o.get('summary', '')} for o in O}
    pats = []
    for g in G:
        for nm in [g['name']] + list(g.get('aliases') or []):
            if nm.lower() in STOP_GAMES or len(nm) < 4: continue
            pats.append((nm, False, 'game', g['id']))
    for t in T:
        for nm in [t['name']] + [a for a in (t.get('aliases') or []) if a.lower() not in STOP_ALIASES]:
            if len(nm) >= 5: pats.append((nm, False, 'technique', t['id']))
    for m in M:
        for nm in [m['name']] + [a for a in (m.get('aliases') or []) if a.lower() not in STOP_ALIASES]:
            if len(nm) >= 6: pats.append((nm, True, 'mechanic', m['id']))
    for nm,(kind,i) in EXTRA.items(): pats.append((nm, kind != 'game', kind, i))
    pats.sort(key=lambda p: -len(p[0]))
    rx = [(re.compile(r'(?<![\w-])' + re.escape(nm) + r"(?![\w-])", re.I if ci else 0), kind, i) for nm, ci, kind, i in pats]
    return {'game': games, 'mechanic': mechs, 'technique': techs, 'bet': opps, 'rx': rx, 'ncol': len(M), 'ngame': len(G)}

def grid(E):
    """Catalog grid for render.html: one row per game, oldest first; columns are mechanics, most used first."""
    gs = sorted(E['game'].values(), key=lambda g: (g['year'] or 0, g['name']))
    return {'rows': [g['row'] for g in gs], 'ids': [g['id'] for g in gs], 'years': [g['year'] for g in gs],
            'ncol': E['ncol'], 'maxn': max(m['n'] for m in E['mechanic'].values())}

def find(E, text):
    """Mentions in order of first position: [(pos, kind, id)], longest names win, no overlaps."""
    taken, out, seen = [], [], set()
    for rx, kind, i in E['rx']:
        for m in rx.finditer(text):
            a, b = m.span()
            if any(a < y and x < b for x, y in taken): continue
            taken.append((a, b))
            if (kind, i) not in seen: out.append((a, kind, i)); seen.add((kind, i))
    out.sort()
    # keep first mention per entity
    res, s2 = [], set()
    for p, k, i in out:
        if (k, i) in s2: continue
        s2.add((k, i)); res.append((p, k, i))
    return res

if __name__ == '__main__':
    E = load()
    t = "The storyteller is in 3 catalog games. Mood breaks in 8. Injuries by body part in 7. Dwarf Fortress, from 2006, and Façade. The pause button, Factorio, conveyor belts, AI Dungeon, GT Sophy, wave function collapse."
    print(find(E, t))
