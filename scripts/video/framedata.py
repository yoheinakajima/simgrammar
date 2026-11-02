"""Resolve a **Frame.** line into what render.html's templates draw (ADR-0006).

Every number a frame shows is read here from dist/entities, dist/analysis, the run records, or vocab/, and every frame
carries a source line saying where, in words a viewer reads: record names, not ids, file paths, or field names.
Labels the script gives (a panel caption, "Zone growth") are prose and are linted with the script. The grammar is
scripts/visual/frames.py; scripts/visual/check.py validates the same lines (E040).
"""
import csv, io, json, os, re, sys, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from visual import frames as FR, toysim, dither  # noqa: E402
import yaml  # noqa: E402
import numpy as np  # noqa: E402

DIST = os.path.join(ROOT, 'dist')
_cache = {}
_built = {}
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


def use_build(outs):
    """Read dist/ files from a build's in-memory outputs instead of the disk (scripts/build.py runs E042 before writing)."""
    _built.clear()
    _built.update(outs)
    _cache.clear()


def dist_text(rel):
    v = _built.get(rel)
    if v is None:
        return open(os.path.join(DIST, rel), encoding='utf-8').read()
    return v.decode('utf-8') if isinstance(v, bytes) else v


def data():
    if 'd' not in _cache:
        live = lambda n: {x['id']: x for x in json.loads(dist_text('entities/' + n)) if not x.get('deprecated')}
        voc = lambda n: {str(t['id']): t for t in yaml.safe_load(open(os.path.join(ROOT, 'vocab', n + '.yaml'), encoding='utf-8'))['terms']}
        clusters = {r['cluster']: r for r in csv.DictReader(io.StringIO(dist_text('analysis/game-clusters.csv')))}
        runs = {}
        for fn in sorted(os.listdir(os.path.join(ROOT, 'log', 'runs'))):
            if fn.endswith('.yaml'):
                r = yaml.safe_load(open(os.path.join(ROOT, 'log', 'runs', fn), encoding='utf-8'))
                runs[r['id']] = r
        _cache['d'] = {
            'G': live('games.json'), 'M': live('mechanics.json'), 'T': live('techniques.json'), 'B': live('opportunities.json'),
            'S': {x['id']: x for x in json.loads(dist_text('entities/sources.json'))},
            'stats': json.loads(dist_text('analysis/stats.json')),
            'icons': json.loads(dist_text('visual/icons.json')),
            'rubrics': yaml.safe_load(open(os.path.join(ROOT, 'vocab', 'rubrics.yaml'), encoding='utf-8')),
            'family': voc('mechanic_family'), 'subgenre': voc('subgenre'), 'category': voc('technique_category'),
            'vocab': {n: voc(n) for n in ('technique_maturity', 'determinism_impact', 'effect', 'status', 'risk', 'horizon', 'opportunity_type', 'runtime')},
            'clusters': clusters, 'runs': runs,
        }
    return _cache['d']


def label(i):
    D = data(); ic = D['icons'].get(i, {})
    if ic.get('label'):
        return ic['label']
    if i in D['M']:
        return D['M'][i]['name']
    if i in D['T']:
        return D['T'][i]['name']
    for k in ('family', 'subgenre', 'category'):
        if i in D[k]:
            return D[k][i].get('label', i)
    return i


def rec(i):
    """A record's name for a frame's source line: the game, mechanic, technique, bet, or source a viewer would recognize."""
    D = data()
    for k in ('G', 'M', 'T', 'B', 'S'):
        if i in D[k]:
            return D[k][i]['name']
    return label(i)


def the(i):
    n = rec(i)
    return n if n.startswith('The ') else 'the ' + n


FIELD_WORDS = {'falsifiable_signal': 'prediction', 'involves': 'mechanics', 'applies': 'techniques', 'validation_experiment': 'experiment',
               'key_risks': 'risks', 'determinism_impact': 'reproducibility', 'deployed_in': 'shipped in', 'design_sketch': 'design sketch'}


def fields_words(fields):
    return ', '.join(FIELD_WORDS.get(x, x.replace('_', ' ')) for x in fields)


def names(i, extra=()):
    """Words in narration that point at element i (its label, record name and aliases, the vocab aliases)."""
    D = data(); out = {label(i)} | set(extra)
    if i in D['G']:
        out |= {D['G'][i]['name']} | {a for a in D['G'][i].get('aliases') or [] if len(a) >= 5}
    if i in D['M']:
        out |= {D['M'][i]['name']} | {a for a in D['M'][i].get('aliases') or [] if len(a) >= 5}
    if i in D['T']:
        out |= {D['T'][i]['name']} | {a for a in D['T'][i].get('aliases') or [] if len(a) >= 5}
    out |= set(D['icons'].get(i, {}).get('aliases') or [])
    from entities import EXTRA, STOP_ALIASES
    out |= {k for k, (kind, eid) in EXTRA.items() if eid == i}
    return sorted(n for n in out if n and n.lower() not in STOP_ALIASES)


def icon_of(i):
    """The icon that draws element i: its own, else a technique's category icon, else none (a type tile)."""
    D = data()
    if i in D['icons']:
        return i
    if i in D['T'] and D['T'][i].get('category') in D['icons']:
        return D['T'][i]['category']
    return None


def el(i, lab='', **kw):
    D = data()
    m = D['M'].get(i)
    ic = icon_of(i)
    return dict({'id': i, 'icon': ic, 'label': lab or label(i), 'size': D['icons'].get(ic, {}).get('size', 48) if ic else 48,
                 'mname': m['name'] if m and lab and lab != m['name'] else ''}, **kw)


def prev(i):
    return data()['M'][i]['_derived'].get('prevalence', 0)


def game_meta(g):
    D = data()
    sub = D['subgenre'].get(g.get('subgenre'), {}).get('label', g.get('subgenre', '')).lower()
    return f"{g.get('year')} · {str(g.get('developer', '')).lower()} · {sub}"


def chip_game(gid):
    g = data()['G'][gid]
    core = sum(1 for u in g['mechanics'] if u.get('role') == 'core')
    return f"game · {g['name']} · {game_meta(g)} · {len(g['mechanics'])} parts, {core} core"


def chip_mech(mid):
    D = data(); m = D['M'][mid]
    return f"mechanic · {m['name']} · {D['family'][m['family']]['label'].lower()} · in {m['_derived'].get('prevalence', 0)} of {len(D['G'])} games"


def chip_tech(tid):
    D = data(); t = D['T'][tid]
    return f"ai technique · {t['name']} · {D['vocab']['technique_maturity'][t['maturity']]['label'].lower()} · {t.get('year')}"


def chip_bet(bid):
    D = data(); b = D['B'][bid]
    return f"bet · {b['name']} · rank {bet_rank(bid)} of {len(D['B'])} · resolves {fmt_date(str(b['falsifiable_signal']['resolve_by']))}"


def bet_rank(bid):
    D = data()
    order = sorted(D['B'], key=lambda k: (-D['B'][k]['_derived'].get('priority', 0), k))
    return order.index(bid) + 1


def fmt_date(d):
    y, m, dd = d.split('-')
    return f"{int(dd)} {MONTHS[int(m) - 1]} {y}"


def use_note(gid, mid):
    g = data()['G'].get(gid) or {}
    for u in g.get('mechanics', []):
        if u['id'] == mid:
            return u.get('note') or ''
    return ''


def first_sentence(v):
    return re.split(r'(?<=[.;])\s', str(v))[0]


def clip(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0].rstrip(',;:') + ' …'


def in_play(t):
    return bool(set(t.get('runtime') or []) & {'server-realtime', 'client-realtime'})


TERM_ICON = {'maturity': 'maturity-', 'determinism_impact': 'determinism-', 'status': 'status-', 'effect': 'effect-', 'risks': 'risk-', 'horizon': 'horizon-'}
VOCAB_OF = {'maturity': 'technique_maturity', 'determinism_impact': 'determinism_impact', 'status': 'status', 'effect': 'effect',
            'risks': 'risk', 'horizon': 'horizon', 'opportunity_type': 'opportunity_type', 'runtime': 'runtime'}


def tally(of, field, where=''):
    """[(term id, label, count, [names])] in vocab order, for a field of techniques, bets, every record, or technique links."""
    D = data()
    if of == 'technique':
        pool = [t for t in D['T'].values() if (where != 'in-play' or in_play(t)) and (where != 'shipped' or t['maturity'].startswith('shipped'))]
        vals = [(t, v) for t in pool for v in (t.get(field) if isinstance(t.get(field), list) else [t.get(field)])]
    elif of == 'opportunity':
        vals = [(b, b.get(field)) for b in D['B'].values()]
    elif of == 'link':
        vals = [(t, a['effect']) for t in D['T'].values() for a in t.get('affects', [])]
    else:
        pool = list(D['G'].values()) + list(D['M'].values()) + list(D['T'].values()) + list(D['B'].values()) + list(D['S'].values())
        vals = [(x, x.get('status')) for x in pool if x.get('status')]
    voc = D['vocab'].get(VOCAB_OF.get(field, ''), {})
    order = list(voc) or sorted({v for _, v in vals})
    out = []
    for term in order:
        hits = [x for x, v in vals if v == term]
        out.append((term, voc.get(term, {}).get('label', term), len(hits), [x.get('name', x.get('id')) for x in hits]))
    return out, len({id(x) for x, _ in vals}) if of != 'link' else len(vals)


def games_with(*mids):
    D = data()
    return sorted((g for g in D['G'].values() if all(any(u['id'] == m for u in g['mechanics']) for m in mids)), key=lambda g: (g['year'], g['id']))


def game_side(gid):
    D = data(); g = D['G'][gid]
    cl = g['_derived'].get('cluster', '')
    return {'id': gid, 'name': g['name'], 'meta': game_meta(g), 'emblem': el(g['subgenre']) if g.get('subgenre') else None,
            'cluster': cl, 'family': D['clusters'].get(cl, {}).get('label', ''),
            'core': [u['id'] for u in g['mechanics'] if u.get('role') == 'core'], 'all': [u['id'] for u in g['mechanics']]}


def plates(name, shots, key, out_dir):
    files = []
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for k, s in enumerate(shots):
            rgba = dither.tonal(s)
            for sc in (3, 4):
                p = os.path.join(out_dir, f'{name}-{key}-{k}@{sc}x.png')
                if not os.path.exists(p):
                    open(p, 'wb').write(dither.png(rgba, sc))
            files.append(os.path.join(out_dir, f'{name}-{key}-{k}'))
    return files


def resolve(text, scene_onscreen='', out_dir=None):
    t, a = FR.parse(text)
    D = data(); NG = len(D['G'])
    f = {'t': t, 'current': [], 'elements': [], 'chip': '', 'source': '', 'label': ''}
    cur = [i for i, _ in FR.items(a.get('current', ''))]

    if t == 'anatomy' and 'game' in a:
        g = D['G'][a['game']]
        want = a.get('parts', 'core')
        if want in ('core', 'all'):
            ids = [u['id'] for u in g['mechanics'] if want == 'all' or u.get('role') == 'core']
        elif want == 'firsts':
            ids = sorted((m for m in D['M'] if D['M'][m]['_derived'].get('earliest_game') == a['game']), key=lambda m: (-prev(m), m))
        else:
            ids = [i for i, _ in FR.items(want)]
        ncore = sum(1 for u in g['mechanics'] if u.get('role') == 'core')
        nfirst = sum(1 for m in D['M'].values() if m['_derived'].get('earliest_game') == a['game'])
        counts = f"{len(g['mechanics'])} parts · {ncore} core · {len(g['mechanics']) - ncore} supporting"
        if want == 'firsts':
            counts = f"first catalog game for {nfirst} of its {len(g['mechanics'])} parts"
        parts = []
        for i in ids:
            d = D['M'][i]['_derived']
            parts.append(el(i, n=prev(i), year=d.get('earliest_year'), first=D['G'].get(d.get('earliest_game'), {}).get('name', '')))
        f.update(t='anatomy', name=g['name'], meta=game_meta(g), N=NG, counts=counts, dates=bool(a.get('dates')), firsts=want == 'firsts',
                 subject=el(g['subgenre']) if g.get('subgenre') in D['icons'] else None, parts=parts, chip=chip_game(a['game']),
                 source=f"counts: catalog games using each part · {the(a['game'])} record" + (" · years: each part's first catalog game" if a.get('dates') or want == 'firsts' else ''))
        f['elements'] = ids
    elif t == 'anatomy' and 'hub' in a:
        sp = FR.items(a['spokes'])
        gid, _, mid = a.get('from', ':').partition(':')
        f.update(t='hub', hub=el(a['hub']), spokes=[el(i, label(i), need=lab, w=len(sp) - k) for k, (i, lab) in enumerate(sp)],
                 weights='line weight: offer × need (illustrative)' if a.get('weights') else '', note=use_note(gid, mid) if mid else '',
                 chip=chip_mech(mid) if mid in D['M'] else '', source=f"objects and needs: {the(gid)} record, {rec(mid)}" if mid else '')
        f['elements'] = [i for i, _ in sp]
    elif t == 'anatomy':
        f.update(t='blank', slots=6, label='your game', dates=bool(a.get('dates')))
    elif t == 'chain':
        gid = a.get('from', '')
        rows = FR.rows(a['nodes'])
        sg = [r.split(',') for r in a.get('signs', '').split('|')] if a.get('signs') else [[] for _ in rows]
        verbs = [v for r in a.get('verbs', '').split('|') for v, _ in FR.items(r)]
        loops = [x for x, _ in FR.items(a.get('loops', ''))]
        vi = 0; out_rows = []
        for r, row in enumerate(rows):
            nodes = []
            for k, (i, lab) in enumerate(row):
                note = use_note(gid, i) if gid and i in D['M'] else ''
                nodes.append(el(i, lab, note=note, n=prev(i) if i in D['M'] else None))
            links = []
            nlinks = len(row) - 1 if not a.get('fan') else len(row) - 1
            for k in range(nlinks + (1 if r < len(loops) and loops[r] else 0)):
                s = (sg[r][k] if r < len(sg) and k < len(sg[r]) else '').strip()
                links.append({'sign': {'-': '−', '+': '+'}.get(s, s), 'verb': verbs[vi] if vi < len(verbs) else ''}); vi += 1
            out_rows.append({'nodes': nodes, 'links': links, 'loop': loops[r] if r < len(loops) else ''})
        strip = []
        if a.get('strip'):
            items = [x.strip().rstrip('.') for x in re.split(r'(?<=\.)\s+', scene_onscreen) if x.strip()]
            strip = [{'text': x.lower(), 'on': x.lower().startswith(a['strip'].lower())} for x in items]
        g = D['G'].get(gid)
        f.update(rows=out_rows, strip=strip, title=f"{g['name'].lower()} · {g['year']}" if g else '', N=NG, fan=bool(a.get('fan')),
                 chip=chip_game(gid) if g else '', source=(f"rules: {the(gid)} record" + (" · counts: catalog games" if any(n['n'] for r in out_rows for n in r['nodes']) else '')) if g else ('counts: catalog games' if any(n['n'] for r in out_rows for n in r['nodes']) else ''))
        f['elements'] = [n['id'] for r in out_rows for n in r['nodes']]
    elif t == 'compare' and 'games' in a:
        ga, gb = [i for i, _ in FR.items(a['games'])]
        A, B = game_side(ga), game_side(gb)
        show = a.get('show', 'family')
        shared = sorted(set(A['all']) & set(B['all']), key=lambda m: (-prev(m), m))
        for side, other in ((A, B), (B, A)):
            own = [m for m in side['core'] if m not in other['all']]
            side['own'] = [el(m, n=prev(m)) for m in own]
        f.update(t='games', a=A, b=B, show=show, same=A['cluster'] == B['cluster'] and bool(A['cluster']), N=NG,
                 shared=[el(m, n=prev(m)) for m in shared], nshared=len(shared),
                 source=f"families: the catalog's game clusters · parts: {the(ga)} and {rec(gb)} records" + (" · counts: catalog games" if show != 'family' else ''))
        f['elements'] = [m['id'] for m in f['shared']] if show == 'shared' else [m['id'] for m in A['own'] + B['own']] if show == 'own' else []
    elif t == 'compare':
        gid, _, mid = a.get('from', ':').partition(':')
        f.update(a={'title': a['a'], 'items': [el(i, lab) for i, lab in FR.items(a['a_items'])]},
                 b={'title': a['b'], 'items': [el(i, lab) for i, lab in FR.items(a['b_items'])]},
                 note=use_note(gid, mid) if mid else '', chip=chip_game(gid) if gid in D['G'] else '',
                 source=f"{the(gid)} record, {rec(mid)}" if mid else '')
        f['elements'] = [i for i, _ in FR.items(a['a_items']) + FR.items(a['b_items'])]
    elif t == 'count':
        count(f, a, D, NG, scene_onscreen, out_dir)
    elif t == 'timeline':
        timeline(f, a, D, NG)
    elif t == 'formula':
        gid, _, mid = a.get('from', ':').partition(':')
        r = FR.items(a['result'])[0]
        w = D['rubrics']['composites'][a['rule']]['weights'] if a.get('rule') else {}
        terms = []
        for op, i, lab in FR.terms(a['terms']):
            sym = ''.join({'-': '−', '+': '+', '×': '×'}.get(c, '') for c in op)
            if FR.numeric(i):
                terms.append({'op': sym, 'open': '(' in op, 'close': ')' in op, 'const': i.replace('-', '−'), 'unit': lab})
            else:
                key = 'w_' + i.replace('score-', '')
                terms.append({'op': sym, 'open': '(' in op, 'close': ')' in op, 'pow': w.get(key), **el(i, lab)})
        src = f"rule: {the(gid)} record, {rec(mid)}" if mid else f"rule: {the(gid)} record" if gid else ''
        if a.get('rule'):
            src = f"rule: the scoring rubric's {a['rule'].replace('_', ' ')} formula, a weighted geometric mean"
        f.update(result=el(*r), terms=terms, note=use_note(gid, mid) if mid else '', chip=chip_game(gid) if gid in D['G'] else '', source=src)
        f['elements'] = [x['id'] for x in terms if x.get('id')] + [r[0]]
    elif t == 'scale' and 'field' in a:
        mid, _, fld = a['field'].partition('.')
        sc = D['rubrics']['scales'][fld]; m = D['M'][mid]
        f.update(mech=el(mid), field=fld.replace('_', ' '), question=sc['question'], value=m[fld],
                 levels=[{'n': int(k), 'text': v} for k, v in sorted(sc['levels'].items(), key=lambda kv: int(kv[0]))],
                 chip=chip_mech(mid), source=f"score: {the(mid)} record, {fld.replace('_', ' ')} · anchors: the scoring rubric's written anchors")
        f['elements'] = [mid]
    elif t == 'scale':
        ids = [i for i, _ in FR.items(a['ids'])]
        rulers = []
        for fld, _ in FR.items(a['fields']):
            sc = D['rubrics']['scales'][fld]
            lv = {int(k): v for k, v in sc['levels'].items()}
            rulers.append({'field': fld.replace('_', ' '), 'question': sc['question'], 'lo': lv[min(lv)], 'hi': lv[max(lv)], 'n': max(lv),
                           'marks': [dict(el(i), v=D['M'][i][fld]) for i in ids]})
        f.update(t='rulers', rulers=rulers, source=f"scores: the {', '.join(rec(i) for i in ids)} records · anchors: the scoring rubric's written anchors")
        f['elements'] = ids
    elif t == 'record':
        record(f, a, D, NG, scene_onscreen)
    elif t == 'moment':
        f.update(panels=[{'icons': [el(i) for i in ics], 'caption': cap} for ics, cap in FR.panels(a['panels'])],
                 subject=el(a['subject']) if a.get('subject') else None, label='drawn from the narration, not game footage')
        f['elements'] = sorted({i for ics, _ in FR.panels(a['panels']) for i in ics})
    elif t == 'toysim':
        src, _, mid = a['from'].partition(':')
        num = lambda k, d: float(a[k].replace(',', '').rstrip('%')) / (100 if a[k].endswith('%') else 1) if k in a else d
        sim = a['sim']
        key = hashlib.sha256(text.encode()).hexdigest()[:12]
        memo = _cache.setdefault('toysim', {})
        if key not in memo:
            memo[key] = {'heat': lambda: toysim.heat(tick=num('tick', 0.2)), 'chunks': lambda: toysim.chunks(rate=num('rate', 0.02), threshold=num('threshold', 15.0)),
                         'flow': lambda: toysim.flow(levels=int(num('levels', 7))), 'life': lambda: toysim.life(gens=int(num('gens', 1103))),
                         'sand': lambda: toysim.sand(), 'wfc': lambda: toysim.wfc()}[sim]()
        shots = memo[key]
        caps = {'life': ['generation 0', 'generation 120', f"generation {a.get('gens', '1103')}"], 'wfc': ['one placed tile', 'a third of the grid', 'every cell decided']}.get(sim, ['start', 'later', 'much later'])
        if src in D['T']:
            mech, note, chip, source = el(src), first_sentence(D['T'][src].get('mechanism', '')), chip_tech(src), f"rule: {the(src)} record · drawn by a toy simulation of that rule"
        else:
            mech, note = el(mid), use_note(src, mid)
            chip, source = (chip_game(src) if src in D['G'] else ''), f"rule: {the(src)} record, {rec(mid)} · drawn by a toy simulation of that rule, not the game"
        f.update(plates=plates(sim, shots, key, out_dir), w=int(shots[0].shape[1]), h=int(shots[0].shape[0]), caps=caps,
                 mech=mech, note=note, chip=chip, source=source, label='toy simulation of the rule')
    elif t == 'mockup':
        mockup(f, a, D)
    elif t == 'site':
        page = a['page']
        if 'web' + page + 'index.html' not in _built and not os.path.exists(os.path.join(DIST, 'web', page.strip('/'), 'index.html')):
            raise KeyError(f"no page {page} in the built site")
        dom = yaml.safe_load(open(os.path.join(ROOT, 'report', 'meta.yaml'), encoding='utf-8'))['site']['domain']
        f.update(page=page, scroll=int(a.get('scroll', 0)), url=dom + page.rstrip('/'), source=f"screenshot of {dom} as this build renders it")
    f['current'] = cur
    cues = f.pop('cues', None)
    f['names'] = cues or {i: names(i) for i in f['elements']}
    return f


def count(f, a, D, NG, onscreen, out_dir):
    k = a['kind']
    if k == 'bars':
        ids = [i for i, _ in FR.items(a['ids'])]
        by_exp = a.get('rank_by') == 'exposure'
        exp_order = sorted(D['M'], key=lambda m: (-D['M'][m]['_derived'].get('technique_exposure', 0), m))
        withs = [[D['G'][g]['name'] for g, _ in FR.items(r)] for r in a['with'].split('|')] if a.get('with') else [[] for _ in ids]
        f.update(t='bars', N=NG, rank=bool(a.get('rank') or a.get('rank_by')),
                 items=[el(i, lab, n=prev(i), rank=(exp_order.index(i) + 1) if by_exp else D['M'][i]['_derived'].get('prevalence_rank'), games=w)
                        for (i, lab), w in zip(FR.items(a['ids']), withs)],
                 source='counts: catalog games using each mechanic · ranked by ' + ('how many techniques reach it' if by_exp else 'how many games use it')
                 + (' · named: catalog games that use it' if a.get('with') else ''))
        f['elements'] = ids
    elif k == 'tiles':
        fam = a['family']
        ms = sorted((m for m in D['M'].values() if m['family'] == fam), key=lambda m: (-prev(m['id']), m['id']))
        hit = {x['id'] for tq in D['T'].values() for x in tq.get('affects', [])}
        lits = a.get('lit', 'affected') != 'none'
        tiles = [{'label': m['name'], 'lit': m['id'] in hit if lits else False, 'n': prev(m['id']), 'year': m['_derived'].get('earliest_year') if a.get('dates') else None} for m in ms]
        summary = f"{sum(1 for x in tiles if not x['lit'])} of {len(tiles)} have no AI technique pointed at them" if lits else f"{len(tiles)} mechanics"
        if a.get('dates'):
            summary += f" · the first in {min(x['year'] for x in tiles)}"
        f.update(t='tiles', family=D['family'][fam]['label'], icon=fam if fam in D['icons'] else None, tiles=tiles, lits=lits, summary=summary,
                 source='mechanics of the family' + (', and the techniques linked to them' if lits else '') + (' · years: first catalog game' if a.get('dates') else ''))
    elif k == 'roles':
        prevs = {'core': [], 'supporting': []}
        for g in D['G'].values():
            for u in g['mechanics']:
                if u['id'] in D['M']:
                    prevs['core' if u.get('role') == 'core' else 'supporting'].append(prev(u['id']))
        bins = [(1, 5), (6, 10), (11, 20), (21, 40), (41, 999)]
        hist = {kk: [sum(1 for p in v if lo <= p <= hi) for lo, hi in bins] for kk, v in prevs.items()}
        med = {kk: D['stats'][f'median_prevalence_{kk}_uses'] for kk in prevs}
        f.update(t='roles', bins=[f"{lo}–{hi}" if hi < 999 else f"{lo}+" for lo, hi in bins], hist=hist, med=med,
                 uses={kk: len(v) for kk, v in prevs.items()},
                 source='uses of each mechanic, by how many catalog games use it · medians: core and supporting uses')
    elif k == 'venn':
        A, B = a['a'], a['b']
        both = games_with(A, B)
        f.update(t='venn', a=el(A, n=prev(A)), b=el(B, n=prev(B)), both=[g['name'] for g in both], nboth=len(both), N=NG,
                 source=f"games using {rec(A)}, {rec(B)}, and both: catalog game records")
        f['elements'] = [A, B]
    elif k == 'set':
        groups = [g for g, _ in FR.items(a.get('groups', ''))] if a.get('groups') else []
        rows = []
        for r in a['ids'].split('|'):
            row = []
            for i, lab in FR.items(r):
                e = el(i, lab)
                if a.get('dates') and i in D['M']:
                    d = D['M'][i]['_derived']; e.update(year=d.get('earliest_year'), first=D['G'].get(d.get('earliest_game'), {}).get('name', ''))
                if a.get('dates') and i in D['T']:
                    e.update(year=D['T'][i].get('year'), first=D['vocab']['technique_maturity'][D['T'][i]['maturity']]['label'].lower())
                row.append(e)
            rows.append(row)
        f.update(t='set', rows=rows, groups=groups, dates=bool(a.get('dates')),
                 source=('years: first catalog game of each mechanic; year and maturity of each technique' if a.get('dates') else ''))
        f['elements'] = [e['id'] for r in rows for e in r]
    elif k == 'units':
        labels = [x for x, _ in FR.items(a.get('labels', ''))]
        gid, _, mid = a['from'].partition(':')
        f.update(t='units', total=int(a['total']), on=int(a['on']), also=int(a['also']) if a.get('also') else None,
                 unit=el(a.get('unit', 'person')), labels=labels, chip=chip_game(gid) if gid in D['G'] else '',
                 source=f"numbers: {the(gid)} record, {rec(mid)}" if mid else f"numbers: {the(gid)} record")
    elif k == 'figures':
        cols = [c for c, _ in FR.items(a['cols'])]
        rows = []
        for r in FR.lines(a['rows']):
            lab, _, vals = r.rpartition(':')
            rows.append({'label': lab.strip(), 'vals': [v.strip() for v in vals.split(',')]})
        srcs = [s for s, _ in FR.items(a['from'])]
        f.update(t='figures', cols=cols, rows=rows, source='figures: ' + ', '.join(rec(s) for s in srcs))
    elif k == 'tally':
        rows, n = tally(a['of'], a['field'], a.get('where', ''))
        pre = TERM_ICON.get(a['field'], '')
        items = [dict(el(pre + term) if pre and (pre + term) in D['icons'] else {'id': term, 'icon': None, 'label': lab, 'size': 48}, label=lab, n=c, names=nm if a.get('names') else []) for term, lab, c, nm in rows]
        what = {'technique': 'techniques', 'opportunity': 'bets', 'record': 'records', 'link': 'technique links'}[a['of']]
        scope = {'in-play': ' that can run during play', 'shipped': ' shipped in a game'}.get(a.get('where', ''), '')
        f.update(t='tally', items=items, N=n, of=what + scope, ordered=a['field'] in ('risks',),
                 source=f"{a['field'].replace('_', ' ')} of every {what[:-1]}{scope}: {('technique' if a['of'] == 'link' else 'catalog' if a['of'] == 'record' else a['of'])} records · terms: the {VOCAB_OF.get(a['field'], a['field']).replace('_', ' ')} vocabulary")
        f['elements'] = [x['id'] for x in items]
    elif k == 'piles':
        side = lambda ids: [dict(el(i), mat=D['vocab']['technique_maturity'][D['T'][i]['maturity']]['label'].lower()) for i, _ in FR.items(ids)]
        f.update(t='piles', a={'title': a['a'], 'items': side(a['a_ids'])}, b={'title': a['b'], 'items': side(a['b_ids'])},
                 source='techniques and their maturity: technique records')
        f['elements'] = [i for i, _ in FR.items(a['a_ids']) + FR.items(a['b_ids'])]
    elif k == 'spread':
        mid = a['id']; d = D['M'][mid]['_derived']
        users = sorted((g for g in D['G'].values() if any(u['id'] == mid for u in g['mechanics'])), key=lambda g: (g['year'], g['id']))
        f.update(t='spread', mech=el(mid), years=[g['year'] for g in users], games=[g['name'] for g in users], fifth=d.get('year_fifth_game'),
                 n=len(users), N=NG, chip=chip_mech(mid), source=f"games using {rec(mid)}, by release year: catalog game records")
        f['elements'] = [mid]
    elif k == 'stat':
        key = a['stat']
        if key not in D['stats']:
            raise KeyError(f"no stat '{key}' in dist/analysis/stats.json")
        v = D['stats'][key]
        shown = f"{v:g}%" if key.startswith('pct_') else (f"ρ = {v:.2f}" if key.startswith('rho_') else f"{v:g}")
        f.update(t='stat', value=shown, label=a.get('label', ''), source='computed from the catalog records')
    elif k == 'ranked':
        n = int(a.get('n', 6))
        order = sorted(D['B'], key=lambda b: (-D['B'][b]['_derived'].get('priority', 0), b))[:n]
        f.update(t='ranked', rows=[{'id': b, 'rank': i + 1, 'name': D['B'][b]['name'], 'priority': D['B'][b]['_derived'].get('priority'),
                                     'horizon': D['vocab']['horizon'].get(D['B'][b].get('horizon'), {}).get('label', D['B'][b].get('horizon')),
                                     'outcome': D['B'][b]['_derived'].get('prediction_status', '')} for i, b in enumerate(order)],
                 N=len(D['B']), source='bets by priority: the ranked bets · outcome: each prediction\'s status')
        f['elements'] = order
    elif k == 'totals':
        yrs = [g['year'] for g in D['G'].values()]
        due = sorted(str(b['falsifiable_signal']['resolve_by']) for b in D['B'].values())
        fams = {m['family'] for m in D['M'].values()}
        links = sum(len(tq.get('affects') or []) for tq in D['T'].values())
        f.update(t='totals', cells=[
            {'id': 'game', 'n': NG, 'label': 'simulation games', 'sub': f"released {min(yrs)} to {max(yrs)}"},
            {'id': 'mechanic', 'n': len(D['M']), 'label': 'mechanics', 'sub': f"in {len(fams)} families"},
            {'id': 'technique', 'n': len(D['T']), 'label': 'AI and ML techniques', 'sub': f"{links} links to mechanics"},
            {'id': 'prediction', 'n': len(D['B']), 'label': 'predictions', 'sub': f"due {due[0][:4]} to {due[-1][:4]}" if due else ''}],
                 source='counts: the catalog records · years: release years and the predictions\' resolve-by dates')
        f['elements'] = ['game', 'mechanic', 'technique', 'prediction']
        f['cues'] = {g: [w] for g, w in FR.items(a.get('cues', ''))}
    elif k == 'icons':
        order = {'mechanic': 0, 'family': 0, 'subgenre': 1, 'technique-category': 2, 'technique': 2, 'noun': 3, 'term': 4}
        fam = lambda i: D['M'][i]['family'] if i in D['M'] else i
        ics = sorted(D['icons'], key=lambda i: (order.get(D['icons'][i]['kind'], 9), fam(i) if D['icons'][i]['kind'] in ('mechanic', 'family') else '',
                                               D['icons'][i]['kind'] != 'family', i))
        kinds = {}
        for i in ics:
            kinds[D['icons'][i]['kind']] = kinds.get(D['icons'][i]['kind'], 0) + 1
        group = lambda kd: {'technique-category': 'technique', 'family': 'mechanic'}.get(kd, kd)
        # tiles name their picture 'ic': the map shows the vocabulary, not each record (publish.py counts 'id' and 'icon')
        f.update(t='iconmap', icons=[{'ic': i, 'group': group(D['icons'][i]['kind'])} for i in ics], N=len(ics),
                 counts=[f"{kinds.get('mechanic', 0)} mechanics", f"{kinds.get('family', 0)} families", f"{kinds.get('subgenre', 0)} genres",
                         f"{kinds.get('technique', 0) + kinds.get('technique-category', 0)} techniques and their kinds",
                         f"{kinds.get('noun', 0) + kinds.get('term', 0)} other subjects"],
                 source='every icon in the visual vocabulary, drawn for this project · grouped by what it names')
        f['elements'] = sorted({group(D['icons'][i]['kind']) for i in ics})
        f['cues'] = {g: [w] for g, w in FR.items(a.get('cues', ''))}
    elif k == 'packages':
        rows = []
        for r in FR.rows(a['rows']):
            ids = [i for i, _ in r]
            rows.append({'items': [el(i, lab) for i, lab in r], 'n': len(games_with(*ids))})
        f.update(t='packages', rows=rows, source='games using every mechanic of each package: catalog game records')
        f['elements'] = [e['id'] for r in rows for e in r['items']]


def timeline(f, a, D, NG):
    kind = a.get('kind', 'first')
    if kind == 'first':
        ids = [i for i, _ in FR.items(a['ids'])]
        items = []
        for i in ids:
            d = D['M'][i]['_derived']
            items.append(el(i, year=d.get('earliest_year'), first=D['G'].get(d.get('earliest_game'), {}).get('name', '')))
        ys = [x['year'] for x in items]
        f.update(items=items, lo=(min(ys) // 10) * 10, hi=(max(ys) // 10 + 1) * 10, source='first catalog game for each mechanic, and its year')
        f['elements'] = ids
    elif kind == 'gap':
        ids = [i for i, _ in FR.items(a['ids'])]
        rows = []
        for i in ids:
            d = D['M'][i]['_derived']
            rows.append(el(i, y1=d.get('earliest_year'), g1=D['G'].get(d.get('earliest_game'), {}).get('name', ''),
                           y2=d.get('second_year'), g2=D['G'].get(d.get('second_game'), {}).get('name', '')))
        ys = [r['y1'] for r in rows] + [r['y2'] for r in rows if r['y2']]
        f.update(t='gap', rows=rows, lo=(min(ys) // 10) * 10, hi=(max(ys) // 10 + 1) * 10, source='first and second catalog game for each mechanic')
        f['elements'] = ids
    elif kind == 'due':
        date = a.get('date') or str(D['B'][a['bet']]['falsifiable_signal']['resolve_by'])
        due = sorted((b for b in D['B'].values() if str(b['falsifiable_signal']['resolve_by']) == date), key=lambda b: (-b['_derived'].get('priority', 0), b['id']))
        f.update(t='due', date=fmt_date(date), cards=[{'id': b['id'], 'name': b['name'], 'rank': bet_rank(b['id']), 'pred': b['falsifiable_signal']['prediction']} for b in due],
                 n=len(due), source=f"bets whose predictions resolve on {date}")
        f['elements'] = [b['id'] for b in due]
        if a.get('bet'):
            f['chip'] = chip_bet(a['bet'])
    elif kind == 'due-years':
        ys = {}
        for b in D['B'].values():
            y = int(str(b['falsifiable_signal']['resolve_by'])[:4]); ys[y] = ys.get(y, 0) + 1
        run = 0; rows = []
        for y in sorted(ys):
            run += ys[y]; rows.append({'year': y, 'n': ys[y], 'cum': run})
        last = max(str(b['falsifiable_signal']['resolve_by']) for b in D['B'].values())
        f.update(t='dueyears', rows=rows, N=len(D['B']), last=fmt_date(last), source='bets by the year their predictions resolve')
    elif kind == 'games':
        ids = [i for i, _ in FR.items(a['ids'])]
        G = sorted(D['G'].values(), key=lambda g: (g['year'], g['id']))
        # each square keeps its game under 'g', not 'id': only the named games count as records on screen (publish.py)
        f.update(t='gameyears', games=[{'g': g['id'], 'year': g['year'], 'on': g['id'] in ids} for g in G],
                 named=[el(i, D['G'][i]['name'], year=D['G'][i]['year']) for i in ids], lo=G[0]['year'], hi=G[-1]['year'], N=NG,
                 source='every catalog game by release year · named: catalog game records')
        for x in f['named']:
            x.pop('icon')   # a game is drawn as its name and a mark on the axis, not as a picture
        f['elements'] = ids
    elif kind == 'techniques':
        by = {}
        for tq in sorted(D['T'].values(), key=lambda x: (x.get('year') or 0, x['id'])):
            by.setdefault(int(tq.get('year') or 0), []).append({'id': tq['id'], 'cat': tq.get('category'), 'name': tq['name']})
        n_recent = sum(len(v) for y, v in by.items() if y >= 2023)
        f.update(t='techyears', years=sorted(by), by=by, N=len(D['T']), recent=n_recent,
                 cats={c: D['category'][c]['label'] for c in D['category']}, source='each technique by its year: technique records')
        f['elements'] = list(D['category'])


def record(f, a, D, NG, onscreen):
    if 'mechanic' in a:
        mid = a['mechanic']; m = D['M'][mid]
        fields = [x for x, _ in FR.items(a.get('fields', 'definition,design_levers'))]
        rows = []
        for fl in fields:
            v = m.get(fl)
            if isinstance(v, list):
                rows.append([fl.replace('_', ' '), [str(x) for x in v]])
            elif v:
                rows.append([fl.replace('_', ' '), [first_sentence(v)]])
        stamps = [x.strip().rstrip('.') for x in re.split(r'(?<=\.)\s+', a['stamps'] if a.get('stamps') and a['stamps'] != 'onscreen' else onscreen) if x.strip()] if a.get('stamps') else []
        f.update(mech=el(mid), kicker='mechanic · ' + D['family'][m['family']]['label'].lower(), rows=rows, stamps=stamps, chip=chip_mech(mid), source=f"{the(mid)} record: " + fields_words(fields))
        f['elements'] = [mid]
    elif 'bet' in a:
        bid = a['bet']; b = D['B'][bid]
        fields = [x for x, _ in FR.items(a.get('fields', 'summary'))]
        rows = [bet_field(b, fl, D) for fl in fields]
        f.update(mech={'id': bid, 'icon': 'dataset-record' if 'dataset-record' in D['icons'] else None, 'label': b['name'], 'size': 48},
                 kicker=f"bet · rank {bet_rank(bid)} of {len(D['B'])} · {D['vocab']['horizon'].get(b.get('horizon'), {}).get('label', b.get('horizon'))}",
                 rows=[r for r in rows if r], stamps=[], cols=len(fields) == 2, chip=chip_bet(bid), source=f"{the(bid)} record: " + fields_words(fields))
    elif 'bets' in a:
        cards = []
        for bid, _ in FR.items(a['bets']):
            b = D['B'][bid]; fs = b['falsifiable_signal']
            cards.append({'id': bid, 'name': b['name'], 'pred': fs['prediction'], 'crit': [c.strip() for c in re.split(r';\s|(?<=\.)\s', fs['criteria']) if c.strip()][:3],
                          'due': fmt_date(str(fs['resolve_by']))})
        f.update(t='cards', cards=cards, source='predictions: the ' + ', '.join(c['name'] for c in cards) + (' bets' if len(cards) > 1 else ' bet'))
        f['elements'] = [c['id'] for c in cards]
    elif 'technique' in a:
        tid = a['technique']; tq = D['T'][tid]
        fields = [x for x, _ in FR.items(a.get('fields', 'summary,limitations'))]
        rows = []
        for fl in fields:
            v = tq.get(fl)
            if fl == 'maturity':
                rows.append(['maturity', [D['vocab']['technique_maturity'][v]['label'].lower()]])
            elif fl == 'determinism_impact':
                rows.append(['reproducibility', [D['vocab']['determinism_impact'][v]['label'].lower() + ': ' + D['vocab']['determinism_impact'][v].get('definition', '').rstrip('.').lower()]])
            elif fl == 'deployed_in':
                rows.append(['shipped in', [D['G'][g]['name'] for g in v or [] if g in D['G']] or ['no catalog game']])
            elif fl == 'risks':
                rows.append(['risks', [D['vocab']['risk'][r]['label'].lower() for r in v or []]])
            elif isinstance(v, list):
                rows.append([fl.replace('_', ' '), [str(x) for x in v]])
            elif v:
                rows.append([fl.replace('_', ' '), [first_sentence(v)]])
        f.update(mech=el(tid), kicker=f"ai technique · {D['category'][tq['category']]['label'].lower()} · {tq.get('year')}", rows=rows, stamps=[],
                 chip=chip_tech(tid), source=f"{the(tid)} record: " + fields_words(fields))
        f['elements'] = [tid]
    elif 'run' in a:
        r = D['runs'][a['run']]
        ag = r.get('agent') or {}
        rows = [['id', [r['id']]], ['kind', [r.get('kind', '')]], ['date', [str(r.get('date', ''))]], ['actor', [r.get('actor', '')]], ['operator', [r.get('operator', '')]],
                ['model', [ag.get('model', '') if isinstance(ag, dict) else str(ag)]], ['purpose', [first_sentence(r.get('purpose', ''))]],
                ['method', [clip(first_sentence(r.get('method', '')), 220)]]]
        f.update(mech={'id': r['id'], 'icon': 'event-log' if 'event-log' in D['icons'] else None, 'label': 'Run record', 'size': 48}, kicker='run · log/runs',
                 rows=rows, stamps=[], source=f"the run record {r['id']}")
    elif 'game' in a:
        g = D['G'][a['game']]
        rows = [['year', [str(g['year'])]], ['status', [g.get('status', '')]]]
        for c in g.get('claims') or []:
            if c.get('disputes'):
                rows.append(['disputed', [first_sentence(c['disputes'])]])
                rows.append(['sources', [D['S'][s]['name'] if s in D['S'] else s for s in c.get('sources', [])]])
        f.update(mech=el(g['subgenre']) if g.get('subgenre') else {'id': g['id'], 'icon': None, 'label': g['name'], 'size': 48},
                 kicker=f"game · {game_meta(g)}", rows=rows, stamps=[g['status']] if g.get('status') == 'contested' else [], chip=chip_game(a['game']),
                 source=f"{the(a['game'])} record: year, status, claims")
        f['mech'] = dict(f['mech'], label=g['name'])
    elif 'script' in a:
        path = os.path.join(ROOT, 'media', a['script'])
        line = next(ln for ln in open(path, encoding='utf-8').read().splitlines() if a['find'] in ln)
        parts = re.split(r'(\{\{[^}]*\}\})', line)
        f.update(t='source', title=a.get('title', ''), parts=[{'tok': p.startswith('{{'), 'text': p} for p in parts if p], file=f"media/{a['script']}",
                 source='the script as written, before the build fills in its numbers')
    else:
        f.update(t='card', title=a.get('title', ''), lines=FR.lines(a['lines']), numbered=bool(a.get('numbered')), source='')


def bet_field(b, fl, D):
    v = b.get(fl)
    if fl == 'falsifiable_signal':
        fs = v
        return ['prediction', [fs['prediction'], 'criteria: ' + fs['criteria'], 'resolves by ' + fmt_date(str(fs['resolve_by']))]]
    if fl == 'involves':
        return ['mechanics', [D['M'][m]['name'] if m in D['M'] else m for m in v or []]]
    if fl == 'applies':
        return ['techniques', [D['T'][t]['name'] if t in D['T'] else t for t in v or []]]
    if fl == 'precedent':
        return ['precedent', [D['G'][g]['name'] if g in D['G'] else g for g in v or []]]
    if fl == 'validation_experiment':
        return ['experiment', [s for s in re.split(r'(?<=\.)\s', str(v)) if s][-2:]]
    if fl == 'key_risks':
        return ['risks', [str(x) for x in v or []]]
    if isinstance(v, list):
        return [fl.replace('_', ' '), [str(x) for x in v]]
    return [fl.replace('_', ' '), [first_sentence(v)]] if v else None


def mockup(f, a, D):
    kind = a['kind']
    lab = a.get('label') or {'terminal': 're-enactment', 'standin': 'stand-in'}.get(kind, 'mock-up')
    items = [el(i, l) for i, l in FR.items(a.get('items', ''))]
    src = a.get('from', '') or a.get('bet', '')
    srcname = ''
    if a.get('bet'):
        srcname = f"design: {the(a['bet'])} record, design sketch"
        f['chip'] = chip_bet(a['bet'])
    elif src in D['T']:
        srcname = f"numbers: {the(src)} record"
        f['chip'] = chip_tech(src)
    elif src.partition(':')[0] in D['G']:
        srcname = f"{the(src.partition(':')[0])} record"
    f.update(t='mockup', kind=kind, tag=lab, title=a.get('title', ''), lines=FR.lines(a.get('lines', '')), items=items, subject=a.get('subject', ''),
             chart=a.get('chart', ''), button=a.get('button', ''),
             label={'mock-up': 'mock-up, not a game screen', 're-enactment': 're-enactment, not a recording', 'stand-in': 'stand-in, not footage'}[lab],
             source=srcname)
    f['elements'] = [e['id'] for e in items]
