"""Render the video series from the scripts in media/ and the narration takes listed in media/narration.yaml.

    make build                                   # dist/media (scripts with figures resolved) and dist/paper/figures
    python scripts/video/assemble.py ep1         # or short1 .. short12, film, intro, all
    -> video-out/final/<name>.mp4               (intro: intro.mp4 at 16:9 and intro-vertical.mp4 at 9:16)   (video-out/ is gitignored; make build prunes anything it did not write in dist/)

Each scene becomes stills (headless Chromium via Playwright, scripts/video/render.html) held for the length of its
narration take; the takes are read from video-out/audio (or $SIMGRAMMAR_AUDIO) and normalized to -16 LUFS.
Pictures show only the project's own graphics: frames chosen by the scripts' **Frame.** lines and drawn from the icons in
dist/visual (ADR-0006), and, for pictures with no Frame line, entity cards from dist/entities, the catalog grid, and paper figures.
A scene with no take on disk is timed at 135 words a minute and left silent (scripts/video/narration.py missing lists them).
The film swaps in the Film wording from media/mega/the-film.md for the episode scenes it re-voices. Needs ffmpeg and node with playwright.
The published lengths come from ffmpeg 6.1, which ends a file with -shortest where the narration ends; ffmpeg 9.0 ended 14 of the
25 videos up to 0.2 s later from the same stills and track. $SIMGRAMMAR_FFMPEG names the binary (on macOS: brew install ffmpeg@6,
then SIMGRAMMAR_FFMPEG=/opt/homebrew/opt/ffmpeg@6/bin/ffmpeg)."""
import json, os, subprocess, sys, re, wave
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from timeline import build
HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.normpath(os.path.join(HERE, '..', '..', 'dist'))
V = os.environ.get('SIMGRAMMAR_VIDEO_OUT', os.path.normpath(os.path.join(HERE, '..', '..', 'video-out')))
AUD = os.environ.get('SIMGRAMMAR_AUDIO', V + '/audio')
FFMPEG = os.environ.get('SIMGRAMMAR_FFMPEG', 'ffmpeg')
SR = 44100
from parse import parse_all, film_wording
sys.path.insert(0, os.path.join(HERE, '..'))
from lib import ROOT, read_yaml
DOMAIN = read_yaml(ROOT / 'report' / 'meta.yaml')['site']['domain']   # the end slates name the site
from entities import load, grid
S = parse_all()
os.makedirs(V, exist_ok=True)
json.dump(grid(load()), open(V + '/grid.json', 'w'))

def afile(key):
    return os.path.join(AUD, re.sub(r'[/#]', '__', key.replace('.md', '')) + '.mp3')

def pcm(path):
    out = subprocess.run([FFMPEG, '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16)

def silence(sec): return np.zeros(int(round(sec * SR)), dtype=np.int16)

def title_of(key):
    t = S[key]['title']; return t.split('. ', 1)[1] if '. ' in t else t

def film_take(key, n):
    """Narration key for an episode scene re-voiced in the film: mega/the-film.md#ep10.4."""
    return f"{FILM}#ep{os.path.basename(key)[:2]}.{n}"

def reword(key, sc, over):
    """Copy of a parsed script with the film's wording swapped into the listed scenes, paragraph for paragraph."""
    sc = json.loads(json.dumps(sc))
    for s in sc['scenes']:
        if s['n'] not in over: continue
        vb = [b for b in s['blocks'] if b['kind'] == 'voice']
        if len(vb) != len(over[s['n']]):
            raise ValueError(f"{key} scene {s['n']}: film wording has {len(over[s['n']])} Voice lines, the episode has {len(vb)}")
        for b, text in zip(vb, over[s['n']]): b['orig'], b['text'] = b['text'], text
    return sc

def segment_script(seg, states, chunks, vertical):
    key = seg['key']; over = seg.get('over') or {}
    sc = reword(key, S[key], over) if over else S[key]
    durs, pcms = {}, {}
    for s in sc['scenes']:
        k = f"{key}#{s['n']}"
        src = film_take(key, s['n']) if s['n'] in over else k
        if any(b['kind'] == 'voice' for b in s['blocks']):
            if os.path.exists(afile(src)): pcms[k] = pcm(afile(src)); durs[k] = len(pcms[k]) / SR
            else: print(f"no take for {src}; timed at 135 words a minute and left silent", file=sys.stderr)
    pace = {k: seg[k] for k in ('lead', 'tail', 'silent') if k in seg}   # the intro's tighter gaps around each take
    st, au = build(key, sc, durs, header=seg['header'], drop_title=seg.get('drop_title'), drop_last=seg.get('drop_last'), only=seg.get('only'), **pace)
    states += st
    for a in au:
        if a['has_voice'] and a['key'] in pcms:
            p = pcms[a['key']]; rest = a['T'] - a['lead'] - len(p) / SR
            chunks += [silence(a['lead']), p, silence(max(rest, 0))]
        else:
            chunks.append(silence(a['T']))

def segment_short(seg, states, chunks):
    key = seg['key']; sc = S[key]
    if os.path.exists(seg['audio']): take = pcm(seg['audio'])
    else: take = silence(sum(len(b['text'].split()) for s in sc['scenes'] for b in s['blocks'] if b['kind'] == 'voice') / 2.25)
    D = len(take) / SR
    words = {f"{key}#{s['n']}": sum(len(b['text'].split()) for b in s['blocks'] if b['kind'] == 'voice') for s in sc['scenes']}
    W = sum(words.values())
    durs = {k: D * w / W for k, w in words.items() if w}
    st, au = build(key, sc, durs, header=seg['header'], lead=0.0, tail=0.0, silent=3.0, maxcards=2)
    lead = 0.4
    st[0]['dur'] += lead
    states += st
    chunks += [silence(lead), take, silence(sum(a['T'] for a in au if not a['has_voice']) + 0.2)]

def slate(seg, states, chunks):
    states.append({'header': seg['header'], 'scene': '', 'fig': seg.get('fig'), 'onscreen': seg['title'], 'sub': seg.get('sub', ''), 'cards': [], 'active': None,
                   'caption': '', 'slate': True, 'dur': seg['dur']})
    chunks.append(silence(seg['dur']))

def make(name, segments, vertical=False):
    states, chunks = [], []
    for seg in segments:
        {'script': lambda: segment_script(seg, states, chunks, vertical), 'short': lambda: segment_short(seg, states, chunks), 'slate': lambda: slate(seg, states, chunks)}[seg['type']]()
    out = os.path.join(V, 'out', name); os.makedirs(out, exist_ok=True)
    json.dump(states, open(out + '/states.json', 'w'))
    audio = np.concatenate(chunks)
    with wave.open(out + '/narration.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(audio.tobytes())
    for f in os.listdir(out):
        if f.startswith('s') and f.endswith('.png'): os.remove(os.path.join(out, f))
    from visual import icons as visual_icons
    visual_icons.sized(os.path.join(V, 'visual', 'icons'))   # the larger icon draws the frames use (ADR-0006)
    subprocess.run(['node', os.path.join(HERE, 'render.js'), out + '/states.json', out, os.path.join(DIST, 'paper', 'figures'), V + '/grid.json'] + (['v'] if vertical else []), check=True)
    mp4 = os.path.join(V, 'final', name + '.mp4'); os.makedirs(os.path.dirname(mp4), exist_ok=True)
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', out + '/concat.txt', '-i', out + '/narration.wav',
                    '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-tune', 'stillimage',
                    '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '44100', '-ac', '1', '-c:a', 'aac', '-b:a', '96k', '-shortest', '-movflags', '+faststart', mp4], check=True)
    dur = len(audio) / SR
    print(name, f'{dur/60:.1f} min', os.path.getsize(mp4) // 1024, 'KB')
    return mp4

def episode(n, key):
    return [{'type': 'script', 'key': key, 'header': f"Episode {n} · {title_of(key)}"},
            {'type': 'slate', 'header': f"Episode {n} · {title_of(key)}", 'title': DOMAIN, 'sub': 'Every game, mechanic, and technique in this video has a page of its own, with its sources.', 'dur': 4.0}]

FILM = 'mega/the-film.md'
FILM_TITLE = 'Every Simulation Game Is Built From the Same Parts'

def film(eps):
    segs = [{'type': 'script', 'key': FILM, 'header': FILM_TITLE, 'only': [1]}]
    W = film_wording()
    def chapter(n):
        k = eps[n - 1]
        over = {s: v for (e, s), v in W.items() if e == n}
        return [{'type': 'slate', 'header': FILM_TITLE, 'title': f"{n}. {title_of(k)}", 'dur': 3.0},
                {'type': 'script', 'key': k, 'header': f"{FILM_TITLE} · {n}. {title_of(k)}", 'drop_title': True, 'drop_last': n != 12, 'over': over}]
    for n in range(1, 6): segs += chapter(n)
    segs += [{'type': 'slate', 'header': FILM_TITLE, 'title': 'The machines arrive', 'dur': 3.0}, {'type': 'script', 'key': FILM, 'header': FILM_TITLE, 'only': [2]}]
    for n in range(6, 9): segs += chapter(n)
    segs += [{'type': 'slate', 'header': FILM_TITLE, 'title': 'From gaps to bets', 'dur': 3.0}, {'type': 'script', 'key': FILM, 'header': FILM_TITLE, 'only': [3]}]
    for n in range(9, 13): segs += chapter(n)
    segs += [{'type': 'slate', 'header': FILM_TITLE, 'title': DOMAIN, 'sub': 'Every game, mechanic, and technique, with its sources.', 'dur': 5.0}]
    return segs

def short(n, key):
    t = S[key]['title']; t = t.split('. ', 1)[1] if '. ' in t else t
    return [{'type': 'short', 'key': key, 'header': f"SimGrammar · Short {n}", 'audio': os.path.join(AUD, 'shorts__' + os.path.basename(key)[:-3] + '.mp3')}]

def intro(key):
    """The intro: one take per scene, as the episodes, with short gaps between the scenes, then the end slate."""
    return [{'type': 'script', 'key': key, 'header': 'SimGrammar', 'lead': 0.15, 'tail': 0.35},
            {'type': 'slate', 'header': 'SimGrammar', 'title': DOMAIN, 'sub': 'Every game, mechanic, technique, and bet has a page, with its sources.', 'dur': 3.5}]

if __name__ == '__main__':
    which = sys.argv[1]
    eps = sorted(k for k in S if k.startswith('episodes/'))
    shs = sorted(k for k in S if k.startswith('shorts/'))
    if which.startswith('ep'):
        n = int(which[2:]); make(f'episode-{n:02d}', episode(n, eps[n - 1]))
    elif which.startswith('short'):
        n = int(which[5:]); make(f'short-{n:02d}', short(n, shs[n - 1]), vertical=True)
    elif which == 'film':
        make('the-film', film(eps))
    elif which == 'intro':
        k = sorted(k for k in S if k.startswith('intro/'))[0]
        make('intro', intro(k)); make('intro-vertical', intro(k), vertical=True)
    elif which == 'all':
        for n in range(1, len(eps) + 1): make(f'episode-{n:02d}', episode(n, eps[n - 1]))
        for n in range(1, len(shs) + 1): make(f'short-{n:02d}', short(n, shs[n - 1]), vertical=True)
        make('the-film', film(eps))
        for k in sorted(k for k in S if k.startswith('intro/'))[:1]:
            make('intro', intro(k)); make('intro-vertical', intro(k), vertical=True)
