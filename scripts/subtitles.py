"""Subtitle cues to SRT, timed from an episode script's scene timings, and to WebVTT, timed from a published render.

A subtitle source (media/subtitles/<lang>/<episode>.md) has one `## <scene number>` heading per scene and one cue per
line beneath it; a line in ［brackets］ translates on-screen text. Cues share each scene's narration window in proportion
to their length, and on-screen cues add two seconds each. Scenes with no narration show their cues across the scene.

srt() takes the windows from the script: narration starts half a second into each planned scene and runs at the script's
135 words a minute. That is a first timing for editors, to be retimed against the recorded voice; the planned scenes are
not the rendered ones, so the site never serves it.

vtt() takes the windows from a render, as media/published.yaml records it: each scene's start, and its narration, which
scripts/video/timeline.py places LEAD seconds after the scene starts and ends TAIL seconds before the next scene, the same
window the video's own captions are spread across. The episode pages offer it as a subtitle track.
"""
from __future__ import annotations

import re

WPM = 135
LEAD, TAIL = 0.5, 0.8   # scripts/video/timeline.py: a voiced scene runs lead + narration + tail
SCENE = re.compile(r"^## (\d+)\. .*?\((\d+):(\d\d) to (\d+):(\d\d)\)\s*$", re.M)
VOICE = re.compile(r"^\*\*Voice\.\*\* (.+)$", re.M)


def _scenes(script: str) -> dict[int, tuple[float, float, int]]:
    out = {}
    heads = list(SCENE.finditer(script))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(script)
        body = script[m.end():end].split("\n## Sources")[0]
        words = sum(len(v.split()) for v in VOICE.findall(body))
        out[int(m.group(1))] = (int(m.group(2)) * 60 + int(m.group(3)), int(m.group(4)) * 60 + int(m.group(5)), words)
    return out


def _cues(src: str) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    cur = None
    for line in src.splitlines():
        m = re.match(r"^## (\d+)\s*$", line)
        if m:
            cur = int(m.group(1))
            out[cur] = []
        elif cur is not None and line.strip() and not line.startswith("#") and not line.startswith("*Dataset"):
            out[cur].append(line.strip())
    return out


def _ts(t: float, sep: str = ",") -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def _timed(windows: dict[int, tuple[float, float, float | None]], cues: dict[int, list[str]]) -> list[tuple[float, float, str]]:
    """Each cue with its start and end. `windows` gives a scene's start, end, and narration length in seconds (None for a
    scene without narration)."""
    out = []
    for k in sorted(cues):
        if k not in windows or not cues[k]:
            continue
        t0, t1, voiced = windows[k]
        screen = sum(1 for c in cues[k] if c.startswith("［"))
        start = t0 + 0.5
        end = t1 - 0.5 if voiced is None else min(t1 - 0.3, start + voiced + 2 * screen)
        weights = [max(len(c), 8) for c in cues[k]]
        total = sum(weights)
        t = start
        for c, w in zip(cues[k], weights):
            d = max(1.2, (end - start) * w / total)
            out.append((t, min(t + d, t1), c))
            t = min(t + d, t1)
    return out


def srt(script: str, src: str) -> str:
    windows = {k: (t0, t1, words / WPM * 60 if words else None) for k, (t0, t1, words) in _scenes(script).items()}
    lines = []
    for n, (a, b, c) in enumerate(_timed(windows, _cues(src)), start=1):
        lines += [str(n), f"{_ts(a)} --> {_ts(b)}", c, ""]
    return "\n".join(lines)


def scene_numbers(script: str) -> dict[str, int]:
    """A rendered episode script's scene names, with their numbers."""
    return {m.group(2): int(m.group(1)) for m in re.finditer(r"^## (\d+)\. (.+?)(?: \(.+?\))?\s*$", script, re.M)}


def vtt(scenes: list[dict], seconds: float, numbers: dict[str, int], src: str) -> tuple[str, list[str]]:
    """WebVTT for a published episode, and the problems that make it unfit to serve (empty when it fits).

    `scenes` are the episode's scenes from media/published.yaml in order (name, start, and `said`, the digest of the
    narration as rendered, which is the empty digest for a scene the render left silent), `seconds` its length, and
    `numbers` the script's scene numbers by name."""
    from lib import narration_digest
    silent = narration_digest("")
    windows, problems = {}, []
    for i, sc in enumerate(scenes):
        t0 = sc["start"]
        t1 = scenes[i + 1]["start"] if i + 1 < len(scenes) else seconds
        if sc["name"] not in numbers:
            problems.append(f"scene '{sc['name']}' is not in the script")
            continue
        windows[numbers[sc["name"]]] = (t0, t1, None if sc["said"] == silent else t1 - t0 - LEAD - TAIL)
    cues = _cues(src)
    problems += [f"cues for scene {k}, which the render does not have" for k in sorted(cues) if cues[k] and k not in windows]
    timed = _timed(windows, cues)
    if timed and timed[-1][1] > seconds + 0.05:
        problems.append(f"a cue ends at {timed[-1][1]:.1f}s, after the video's {seconds}s")
    lines = ["WEBVTT", ""]
    for a, b, c in timed:
        lines += [f"{_ts(a, '.')} --> {_ts(b, '.')}", c, ""]
    return "\n".join(lines), problems
