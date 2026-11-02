# Visual vocabulary

The pictures in the video series are built from the icons here and the frame templates in `scripts/video/templates.js` (ADR-0006). The contents of this folder are licensed CC BY 4.0, like the data.

## Add an icon

1. Pick the id.
   - A mechanic, mechanic family, subgenre, or technique category uses the dataset's id.
   - A vocab term a frame tallies takes its field's prefix: `status-`, `maturity-`, `determinism-`, `effect-`, `risk-`, or `horizon-` and the term id, labelled as in `vocab/` (`TERM_ICON` in `scripts/video/framedata.py`).
   - Anything else is a noun with its own kebab-case id, and that id cannot be a dataset id.
2. Draw `icons/<id>.svg` in the subset below. Open it in a browser to check it: the colours preview as flat greys.
3. Add an entry to `vocab.yaml`. A noun needs a label. Add aliases for the other words the narration uses for the subject, so the frame's highlight can follow it.
4. Run `make build` and look at `dist/visual/sheet.html`, which shows every icon in ink and in the accent. Then run `make check`: E041 reports anything outside the subset, and E042 any element a frame would draw without an icon, including the parts and terms it takes from the data.

## The subset

- `viewBox="0 0 48 48"` for vocab icons, or `0 0 96 96` for a hero subject. One unit is one dither pixel (dpx). The video draws it at 3 px for 16:9 and 4 px for 9:16.
- Elements: `rect` (with optional `rx`), `circle`, `ellipse`, `line`, `polyline`, `polygon`. The file is a flat list, with no groups, transforms, paths, or text.
- Coordinates are multiples of 0.5 inside the box.
- Every filled shape states `fill`, a palette colour or `none`.
- Strokes are 1, 2, or 3 dpx and centred on the shape.
- Shapes are drawn in file order. A later shape covers an earlier one, and `#fafaf7` knocks out to paper.

| Colour | Tone |
|---|---|
| `#c8c8c2` | 25 % ink |
| `#8c8c86` | 50 % ink |
| `#55554f` | 75 % ink |
| `#171717` | ink |
| `#fafaf7` | paper (knockout) |
| `#a9c2e6` `#6f93cf` `#3a6ab8` `#0550ae` | 25, 50, 75, 100 % accent, for a part that is always accent (an injury) |

## Drawing rules

- Use the live area 4 to 44, with standing things on a baseline at y = 44.
- Outlines are 2 dpx and interior detail 1 dpx.
- Light comes from the top left: top and left faces are one tone lighter than bottom and right faces.
- Draw people, objects, and buildings in front elevation. Ground, parcels, and tokens such as a die or a book use one 2:1 axonometric. Maps are in plan.
- There is one person glyph: round head, box torso, separate arm and leg bars. It has no face, hair, or clothing detail.
- Never put text inside an icon. Labels are set in type beside it.
- Draw generic subjects only. Nothing may copy a game's art, logo, cover, characters, or UI, so no plumbob-like marker over a head, no armless round-headed pawn, and no game's tileset. A game is shown as its name, its subgenre emblem, and its parts.

## Frame lines

A `**Frame.**` line under a Picture line chooses the frame. For example:

    **Frame.** chain nodes="factory,pollution-spread,land-value,house:Zone growth" signs=+,-,+ verbs=writes,lowers,raises from=simcity-1989

The grammar and the twelve templates are in `scripts/visual/frames.py`, and `make check` validates every line (E040). A frame's numbers come from the dataset, never from the Frame line. The exception is a number the line states, such as a formula constant, a toy simulation parameter, or a survey figure, and it must appear in the text of the record or source the line cites with `from=`. A label inside a list cannot contain a comma. Anything drawn to look like a screen goes in a `mockup` frame, which always carries its label. A `site` frame is not drawn: it is a screenshot of this project's own site as the same build renders it (`dist/web`, served under its address with no network), and its footer says so. It shows no other site.
