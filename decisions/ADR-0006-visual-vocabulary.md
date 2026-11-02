# ADR-0006: A visual vocabulary for the video series

- Status: accepted
- Date: 2026-10-26
- Contract version: 1.2 (new rules E040, E041, E042, W108 and invariant I16)
- Runs: `2026-10-26-visual-vocabulary`

## Context

The renderer in `scripts/video` drew each scene from entity cards, the catalog grid, and the paper's figures. In episodes and shorts, cards held the screen for 60 % of the runtime (72.6 of 121 minutes), figures for 22 %, and title or fallback slates for 14 %. A card restates what the narration says, so most of each video read as secondary information.

The scripts' Picture lines describe gameplay footage the project does not have and will not use for now. 101 of the 228 Picture lines name a game.

Two more problems came out of the survey:

- `render.html` loaded IBM Plex from Google Fonts at render time. When the proxy refused that host, Chromium rendered in a fallback face and the build still passed.
- Its labels used `text-transform: uppercase`, which the Register contract (`web/DESIGN.md`, rule 3) forbids.

Yohei approved a plan for a dithered visual vocabulary on 2026-10-26, with these choices:

1. Icons are drawn as code and dithered by a deterministic filter. The series uses no AI images.
2. Ink and one accent on Register paper, ordered 8x8 Bayer dither, 3 px per dither pixel at 16:9 and 4 px at 9:16.
3. Moment strips and toy simulations stand in for footage in cold opens.
4. Scenes choose their pictures with inline `**Frame.**` lines.
5. `media/visual/` is licensed CC BY 4.0.
6. Coverage target is all 199 mechanics, in phase 4.
7. While a frame is up, the main entity shows as one line. Scenes with no Frame keep the cards.

## Decision

### Icons

`media/visual/vocab.yaml` lists every icon: its id, its kind, and, for nouns, a label and the words in narration that point at it.

- Kinds: mechanic, family, subgenre, technique, technique-category, noun, term.
- Mechanic, family, subgenre, and technique-category icons use the dataset's own ids, so no record changes.
- Nouns are drawn subjects that are not records, such as a refrigerator or a raid.

Each icon is `media/visual/icons/<id>.svg` in a small SVG subset, rasterized by `scripts/visual/raster.py`:

- flat rect, circle, ellipse, line, polyline, and polygon elements;
- a 48-dpx viewBox, or 96 for hero subjects;
- coordinates on the half-dpx grid;
- strokes of 1 to 3 dpx;
- colours from a nine-tone palette that names the tones, so each file previews in a browser as flat greys.

`scripts/build.py` dithers every icon into `dist/visual/` at 3 px and 4 px per dpx, in ink and in the accent, through `scripts/visual/dither.py`. The icons are part of the build, so `make determinism` covers them. Pillow is pinned in `requirements.txt`.

The first set has 79 icons:

| Kind | Icons |
|---|---:|
| Mechanics | 25 |
| Family | 1 |
| Subgenres | 4 |
| Nouns | 49 |

### Frame lines

A `**Frame.**` line under a Picture line names a frame template and its arguments. The grammar is `scripts/visual/frames.py`.

There are twelve templates: anatomy, chain, compare, count, timeline, formula, scale, record, moment, toysim, mockup, and site. Each has variants:

- **anatomy**: a game's parts (core, all, the parts it was first to use, or a list), a hub of objects, or a blank row.
- **chain**: a causal chain in one or two rows, with signs and loops, or a fan from one node.
- **compare**: two drawn columns, or two games with their families, shared parts, or own core parts.
- **count**: bars, tiles, histograms, a Venn of two mechanics, a set, units, figures from a source, a tally of a vocab field, piles, a spread over years, one stat, a ranked table, packages of mechanics, the catalog's totals, or every icon in this vocabulary. Bars may name games that use each mechanic.
- **timeline**: first appearances, the gap to a second game, the bets due on a date or by year, techniques by year, or every catalog game by year.
- **formula**: terms, groups, and constants with units, or a composite from `vocab/rubrics.yaml`.
- **scale**: one rubric scale, or rulers that place several mechanics.
- **record**: a mechanic, bet, technique, run, or game record; several bets; a line of a script's source; or a card of lines.
- **mockup**: a window, terminal, document, or stand-in, always labelled mock-up, re-enactment, or stand-in.
- **site**: a screenshot of this project's own site as the same build renders it (`dist/web`), added for the intro (run 2026-11-01-intro-video). It is not drawn, and it shows no other site.

A Picture may carry several Frame lines. Each one after the first has `at="..."`, the narration words where it takes over.

Picture ids in `scripts/video/figmap.py` count only Picture, Voice, and On screen blocks, so adding a Frame line never shifts a figure mapping.

### Numbers

`scripts/video/framedata.py` reads every number a frame shows from one of these sources:

- `dist/entities`;
- `dist/analysis/stats.json` and the cluster table;
- the run records in `log/runs/`;
- `vocab/`.

Every frame carries a source line.

A number the Frame line itself states must appear in the text that its `from=` names: a game's record and its note on the mechanic, a mechanic, a technique, a bet, or a source. That covers formula constants, toy simulation parameters, unit counts, survey figures, and numbers in a mock-up. Crime is 128 − land value + density − police in SimCity's record, and Generative Agents' gossip reached 13 of 25 agents in its own. Labels the script gives, such as "Zone growth" or a panel caption, are prose and are linted with the script.

### Renderer

- **Templates.** `scripts/video/templates.js` draws the templates. While a frame is up, the highlight follows the narration through the frame's own elements only.
- **Sizes and the grid.** A frame draws its icons at 42 to 144 dpx. The renderer redraws the vector at that size into its cache, so the dither grain stays one dpx, and moves each layout unit so its sprite sits on the page's 8-dpx grid. 9:16 layouts fit their sizes to the stage height.
- **Motion.** A new frame builds in by Bayer dissolve, unit by unit. Arrows draw from tail to head, counters tick in integers, and a moved highlight cross-dissolves. The steps are 1/30 s stills taken from the start of each state's own duration, so the cut points and the narration do not move.
- **Chip.** The main entity shows as one line under the frame. Scenes with no Frame line keep the cards.
- **Fonts.** IBM Plex is vendored in `media/fonts/` under the SIL Open Font License 1.1. `render.js` stops if a face fails to load.
- **Labels.** Labels are lowercase mono, as Register requires.
- **Toy simulations.** `scripts/visual/toysim.py` runs the rule a record states (Oxygen Not Included's tile heat exchange, Factorio's chunk pollution) on a small grid with no randomness. The frame labels the picture as a toy simulation of the rule.

### Rights

Icons draw generic subjects only: no game's art, logo, cover, character, or UI. A game is shown as its name in type, its subgenre emblem, and its parts.

Moment frames say "drawn from the narration, not game footage". A frame that draws something resembling game UI carries the mock-up label from its template.

### Checks

- **E040 frame-line.** Every Frame line parses and follows a Picture line in its scene. Its ids resolve, its `at=` phrase is in the scene's narration, and it states no number missing from the record text it cites.
- **E041 visual-icon.** Every vocab.yaml entry has a valid icon file in the subset, and every icon file has an entry. Dataset-kind ids exist, noun and term ids do not reuse dataset ids, and no id, label, or alias names a game.
- **E042 frame-icon.** Every element a Frame line draws has an icon, once the frame is resolved against the build as the renderer resolves it: the parts of a game it takes apart, the vocab terms of a tally, the subgenre emblem of a game it shows. E040 reads only the ids a line names, and the renderer drew an element with no icon as a blank type tile, so the build stops instead. `scripts/build.py` runs it, since it needs the built entities and stats.
- **W108 visual-coverage.** Counts the mechanics, families, subgenres, and technique categories with no icon yet. It stays a warning for icons no frame draws; E042 covers the ones a frame does.

### Licences

- `media/visual/` is CC BY 4.0, like the data.
- `media/fonts/` keeps the font's own licence.
- The code in `scripts/visual` is Apache-2.0, like the rest of `scripts/`.

## Consequences

- **First cut.** Episode 1 and shorts 1, 4, 5, and 7 are re-rendered with frames. Narration and scene lengths are unchanged: the same takes, the same state durations, the same audio track.
- **Other videos.** They render as before, with cards, figures, and the grid, until their scripts gain Frame lines. Their labels are now lowercase and their fonts local, so every video changes slightly in look.
- **Phase 3.** Every episode, short, and the film's own scenes carry Frame lines. Pictures that show the catalog grid or a paper figure keep it.
- **Dense layouts.** A frame with many elements draws them smaller, down to 42 dpx, and keeps 3 px and 4 px per dpx. Past about twelve parts, anatomy lists the parts as a grid beside the game.
- **Upkeep.** A Frame line goes stale when its scene changes. E040 catches broken ids, phrases, and numbers, and E042 a data change that puts an element with no icon into a frame. A layout that no longer fits the narration is caught only by review.
- **Blank tiles.** The phase-3 renders drew 57 elements with no icon as blank tiles, about 1,240 times across the 25 videos: mechanics a frame took from a game's parts, the risk and horizon terms of two tallies, and the contested status. Phase 4 drew them and added E042.
- **Name lint.** The rights lint compares names and cannot judge a drawing. A generic drawing can still recall a game, so each icon's review stays a human check.
