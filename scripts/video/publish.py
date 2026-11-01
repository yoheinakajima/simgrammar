"""Publish rendered videos to the website: write media/published.yaml from video-out and stage the files for a release.

    make build && python scripts/video/assemble.py all        (the renders in video-out/final, their states in video-out/out)
    python scripts/video/publish.py --release videos-2026-10-27
    gh release create videos-2026-10-27 video-out/publish/*    (the files are not committed; the release holds them)
    python scripts/video/publish.py --release videos-2026-11-02 --repo https://github.com/<owner>/<media-repo>
        then: gh release create videos-2026-11-02 video-out/publish/* --repo <owner>/<media-repo>

Zenodo archives every release of this repository as a version of the paper, so video releases belong in a separate
repository that Zenodo does not archive; --repo records it in media/published.yaml (repo:), and the Pages workflow
downloads from there.

The shorts and the episodes are published; the film stays off the site. Each entry names the video file and its sha256,
its length, a poster frame and its sha256, and the records the video shows: the frame elements and cards in its rendered
states.json that are records, most shown first, at most twelve. A short's poster is a frame at 2.5 s. An episode's poster
is its title card, and its thumb the frame with the most records on screen; it also lists its scenes from the render, each
with its start, the records it shows and when each first appears, and a digest of what its narration says
(lib.narration_digest), so the site can tell when the dataset has moved on from a render. The site reads this file
(scripts/web.py), and the Pages workflow fetches the files from the release and checks every sha256
(scripts/video/fetch_published.py). Re-run it after re-rendering and publish under a new release name.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import narration_digest  # noqa: E402

V = Path(os.environ.get('SIMGRAMMAR_VIDEO_OUT', ROOT / 'video-out'))
FFMPEG = os.environ.get('SIMGRAMMAR_FFMPEG', 'ffmpeg')
KEYS = ('id', 'icon', 'of', 'current')
SHOWS_MAX = 12
POSTER_AT = 2.5


def records():
    out = {}
    for f in sorted((ROOT / 'dist' / 'entities').glob('*.json')):
        for r in json.loads(f.read_text(encoding='utf-8')):
            if r['type'] != 'source':
                out[r['id']] = r['type']
    return out


def found(state, recs):
    """The records one rendered state puts on screen."""
    acc = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in KEYS and isinstance(v, str) and v in recs:
                    acc.add(v)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(state)
    return acc


def shows(states, recs):
    c = Counter()
    for s in states:
        c.update(found(s, recs))
    return [i for i, _ in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))][:SHOWS_MAX]


def scenes(states, recs):
    """An episode's scenes as rendered: start, a digest of the narration, and each record shown with when it first appears.
    Also the time of the frame with the most records on screen (the end of that state, once it has all drawn in)."""
    out, t, rich = [], 0.0, (0, 0.0)
    for s in states:
        name = s.get('scene') or ''
        recs_here = found(s, recs)
        if s['dur'] >= 1.0 and len(recs_here) > rich[0]:
            rich = (len(recs_here), t + s['dur'] - 0.3)
        if name and (not out or out[-1]['name'] != name):
            out.append({'name': name, 'start': round(t, 1), 'said': [], 'shows': {}})
        if name:
            sc = out[-1]
            cap = (s.get('caption') or '').strip()
            if cap and (not sc['said'] or sc['said'][-1] != cap):
                sc['said'].append(cap)
            for r in sorted(recs_here):
                sc['shows'].setdefault(r, round(t, 1))
        t += s['dur']
    return [{**sc, 'said': narration_digest(' '.join(sc['said']))} for sc in out], rich[1]


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def seconds(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)], capture_output=True, text=True, check=True)
    return round(float(out.stdout), 1)


def frame(mp4, at, out, width):
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-ss', f'{at:.2f}', '-i', str(mp4), '-frames:v', '1', '-vf', f'scale={width}:-2', '-q:v', '3', str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--release', required=True, help='GitHub release tag that will hold the files')
    ap.add_argument('--repo', help='https URL of the repository whose release holds the files, when it is not this one')
    a = ap.parse_args()
    recs = records()
    stage = V / 'publish'
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    rows = []
    for i, script in enumerate(sorted((ROOT / 'media' / 'shorts').glob('*.md')), 1):
        key = f'short-{i:02d}'
        mp4 = V / 'final' / f'{key}.mp4'
        states = json.loads((V / 'out' / key / 'states.json').read_text(encoding='utf-8'))
        poster = stage / f'{key}.jpg'
        shutil.copy2(mp4, stage / mp4.name)
        frame(mp4, POSTER_AT, poster, 540)
        rows.append({'key': key, 'script': script.name, 'file': mp4.name, 'sha256': sha256(mp4), 'seconds': seconds(mp4),
                     'poster': poster.name, 'poster_sha256': sha256(poster), 'shows': shows(states, recs)})
    eps = []
    for i, script in enumerate(sorted((ROOT / 'media' / 'episodes').glob('*.md')), 1):
        key = f'episode-{i:02d}'
        mp4 = V / 'final' / f'{key}.mp4'
        states = json.loads((V / 'out' / key / 'states.json').read_text(encoding='utf-8'))
        scs, rich = scenes(states, recs)
        title = next((s['start'] for s in scs if s['name'] == 'Title'), 20.0)
        poster, thumb = stage / f'{key}.jpg', stage / f'{key}-thumb.jpg'
        shutil.copy2(mp4, stage / mp4.name)
        frame(mp4, title + 2.0, poster, 960)
        frame(mp4, rich, thumb, 640)
        eps.append({'key': key, 'script': script.name, 'file': mp4.name, 'sha256': sha256(mp4), 'seconds': seconds(mp4),
                    'rendered': datetime.date.fromtimestamp(mp4.stat().st_mtime).isoformat(),
                    'poster': poster.name, 'poster_sha256': sha256(poster), 'thumb': thumb.name, 'thumb_sha256': sha256(thumb),
                    'shows': shows(states, recs), 'scenes': scs})
    head = ('# Videos published on the website (scripts/web.py). The files are not in git: they are assets of the GitHub release\n'
            '# named here, which the Pages workflow fetches and checks against each sha256 (scripts/video/fetch_published.py).\n'
            '# Written by scripts/video/publish.py from the renders in video-out; shows lists the records each video puts on screen.\n'
            '# An episode\'s scenes give each scene\'s start in seconds, the records it shows with when each first appears, and said,\n'
            '# a digest of its narration as rendered (lib.narration_digest).\n')
    body = f'release: {a.release}\n' + (f'repo: {a.repo.rstrip("/")}\n' if a.repo else '') + 'shorts:\n' + ''.join(
        f'  - {{key: {r["key"]}, script: {r["script"]}, file: {r["file"]}, seconds: {r["seconds"]},\n'
        f'     sha256: {r["sha256"]},\n     poster: {r["poster"]}, poster_sha256: {r["poster_sha256"]},\n'
        f'     shows: [{", ".join(r["shows"])}]}}\n' for r in rows)
    body += 'episodes:\n' + ''.join(
        f'  - {{key: {r["key"]}, script: {r["script"]}, file: {r["file"]}, seconds: {r["seconds"]}, rendered: \'{r["rendered"]}\',\n'
        f'     sha256: {r["sha256"]},\n     poster: {r["poster"]}, poster_sha256: {r["poster_sha256"]},\n'
        f'     thumb: {r["thumb"]}, thumb_sha256: {r["thumb_sha256"]},\n     shows: [{", ".join(r["shows"])}],\n     scenes: [\n'
        + ''.join(f'       {json.dumps(sc, ensure_ascii=False)},\n' for sc in r['scenes']) + '     ]}\n' for r in eps)
    (ROOT / 'media' / 'published.yaml').write_text(head + body, encoding='utf-8')
    print(f'media/published.yaml: {len(rows)} shorts and {len(eps)} episodes for release {a.release}; files staged in {stage}')


if __name__ == '__main__':
    main()
