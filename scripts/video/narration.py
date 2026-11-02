"""Narration jobs: the text each take must speak, keyed as in media/narration.yaml.

    python scripts/video/narration.py missing     # jobs with no take in video-out/audio, as JSON
    python scripts/video/narration.py all         # every job

Episodes, the intro, and the film's own scenes get one take per scene with a Voice line; scenes the film re-voices
(media/mega/the-film.md, "Film wording") get keys like mega/the-film.md#ep10.4; a short gets one take for
the whole short. speech() respells what the voice model misreads: roman numerals and all-caps names."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse import parse_all, film_wording

RESPELL = {"DOOM": "Doom", "EVE": "Eve", "NVIDIA": "Nvidia", "KRAFTON": "Krafton"}
ROMAN = {"II": "Two", "III": "Three", "IV": "Four"}

def speech(text):
    text = re.sub(r"\b(" + "|".join(RESPELL) + r")\b", lambda m: RESPELL[m.group(1)], text)
    return re.sub(r"(?<=[a-z]) (II|III|IV)\b", lambda m: " " + ROMAN[m.group(1)], text)

def audio_name(key):
    return re.sub(r"[/#]", "__", key.replace(".md", "")) + ".mp3"

def jobs():
    S = parse_all()
    out = []
    for k in sorted(S):
        voices = lambda s: [b["text"] for b in s["blocks"] if b["kind"] == "voice"]
        if k.startswith("shorts/"):
            out.append({"key": k, "text": speech("\n\n".join(v for s in S[k]["scenes"] for v in voices(s)))})
            continue
        for s in S[k]["scenes"]:
            if voices(s): out.append({"key": f"{k}#{s['n']}", "text": speech("\n\n".join(voices(s)))})
    for (e, n), v in sorted(film_wording().items()):
        out.append({"key": f"mega/the-film.md#ep{e:02d}.{n}", "text": speech("\n\n".join(v))})
    for j in out: j["file"] = audio_name(j["key"]); j["chars"] = len(j["text"])
    return out

if __name__ == "__main__":
    audio = os.environ.get("SIMGRAMMAR_AUDIO", os.path.join(os.environ.get("SIMGRAMMAR_VIDEO_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "video-out")), "audio"))
    J = jobs()
    if sys.argv[1:] == ["missing"]: J = [j for j in J if not os.path.exists(os.path.join(audio, j["file"]))]
    json.dump(J, sys.stdout, ensure_ascii=False, indent=1)
    print(f"\n{len(J)} jobs, {sum(j['chars'] for j in J)} characters", file=sys.stderr)
