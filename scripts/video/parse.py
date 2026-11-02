"""Parse rendered scripts (dist/media) into scenes with ordered blocks: picture, voice, onscreen, frame (ADR-0006)."""
import re, json, glob, os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', 'dist', 'media')
OUT = os.environ.get('SIMGRAMMAR_VIDEO_OUT', os.path.join(HERE, '..', '..', 'video-out'))
SCENE = re.compile(r"^## (\d+)\. (.+?)(?: \((.+?)\))?\s*$")
SHORT = re.compile(r"^## (\d+:\d\d) to (\d+:\d\d)\. (.+?)\s*$")
WORDING = re.compile(r"^### Episode (\d+), scene (\d+)")

def clean(s):
    s = re.sub(r"<!--.*?-->", "", s)
    s = re.sub(r"\s*\[(?:\[\d+\]\(#ref-[^)]+\)(?:,\s*)?)+\]", "", s)       # citations
    s = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", s)                       # links
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = s.replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", s).strip()

def parse(path):
    return parse_text(open(path, encoding='utf-8').read(), os.path.basename(path))

def parse_text(txt, name):
    txt = txt.split("\n## Sources")[0]
    title = re.search(r"^# (.+)$", txt, re.M).group(1)
    scenes, cur = [], None
    for line in txt.splitlines():
        m2 = SHORT.match(line)
        if m2:
            cur = {"n": len(scenes) + 1, "title": m2.group(3), "time": f"{m2.group(1)} to {m2.group(2)}", "blocks": []}
            scenes.append(cur); continue
        m = SCENE.match(line)
        if m:
            cur = {"n": int(m.group(1)), "title": m.group(2), "time": m.group(3) or "", "blocks": []}
            scenes.append(cur); continue
        if cur is None: continue
        for kind, lab in (("picture", "**Picture.**"), ("voice", "**Voice.**"), ("onscreen", "**On screen.**"), ("frame", "**Frame.**")):
            if line.startswith(lab):
                cur["blocks"].append({"kind": kind, "text": clean(line[len(lab):])})
    return {"file": name, "title": title, "scenes": scenes}

def film_wording(path=None):
    """{(episode, scene): [voice paragraphs]} from the film script's "Film wording" section."""
    txt = open(path or os.path.join(ROOT, "mega", "the-film.md"), encoding="utf-8").read()
    if "\n## Film wording" not in txt: return {}
    body = txt.split("\n## Film wording", 1)[1].split("\n## ", 1)[0]
    out, cur = {}, None
    for line in body.splitlines():
        m = WORDING.match(line)
        if m: cur = (int(m.group(1)), int(m.group(2))); out[cur] = []; continue
        if cur and line.startswith("**Voice.**"): out[cur].append(clean(line[len("**Voice.**"):]))
    return out

def parse_all():
    out = {}
    for p in sorted(glob.glob(ROOT + "/episodes/*.md")) + [ROOT + "/mega/the-film.md"] + sorted(glob.glob(ROOT + "/shorts/*.md")) + sorted(glob.glob(ROOT + "/intro/*.md")):
        d = parse(p); out[os.path.relpath(p, ROOT)] = d
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, "scripts.json"), "w"), ensure_ascii=False, indent=1)
    return out

if __name__ == "__main__":
    out = parse_all()
    for k, d in out.items():
        nv = sum(1 for s in d["scenes"] for b in s["blocks"] if b["kind"] == "voice")
        w = sum(len(b["text"].split()) for s in d["scenes"] for b in s["blocks"] if b["kind"] == "voice")
        print(f"{k:45s} scenes={len(d['scenes']):3d} voice={nv:3d} words={w}")
