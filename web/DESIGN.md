# DESIGN.md · register

This file is the design contract for agents working in this repository. Read it before generating or editing any page. When it conflicts with a general instinct, this file wins.

## Stylesheet

- The only stylesheet is `register.css`. Do not add another. Do not add Tailwind, shadcn, or a component library.
- Do not write inline `<style>` blocks or new classes for variants. Use the grammar below. If a variant does not exist, add it to `register.css` as a `data-*` value on the existing component, not as a new class.
- No JavaScript is required for any page to be complete. Interactive controls must degrade to a complete static table or list.
- Type is IBM Plex, self-hosted: `register.css` declares the faces, and the build copies the vendored files from `media/fonts` (SIL OFL 1.1, license included) to `assets/fonts/`. Pages load nothing from another host.

## Grammar

- A class names the component (`register`, `row`, `panel`, `band`, `numbers`, `receipt`, `note`, `chart`, `rule`, `pattern`).
- `data-surface` picks the paper: `tint` `wash` `deep` `s1`–`s4` `s1w`–`s4w` `ok` `open` `stop` `info` `duo`.
- `data-series` picks a data series `1`–`4`. Only for numbers that are series.
- `data-state` marks state: `done` `active` `waiting` `blocked` `parked` `optional` `live` `reserved` `superseded`. Claim workflows map: proposed/sourced/derived → `waiting`; implemented/checked → `active`; verified/independently-reproduced → `done`; refuted → `blocked`; superseded/retired → `parked`.
- `data-style` is a component's own variant; `data-size` is `sm` `lg` `wide`; `data-kind` says what a register lists.
- `data-theme` and `data-display` go on `<html>`.

## Skins

- Looks are tokens. To change how pages look, write or edit a skin in `skins/` following `skins/_schema.md`; never edit component rules for a look. A skin may set any token in the schema and nothing else.
- Set `data-skin` on `<html>`; load the skin after `register.css`.
- Meet the contrast floors in the schema. A dark paper needs a light `--deep` block. Small text needs 4.5:1: `--muted`, `--faint` and `--open` are at least that on `--paper` and `--paper-2` in every theme in `register.css`, and `--deep-faint` on each theme's `--deep`.
- Every skin file starts with the seven-line image brief; the prompt templates depend on it.

## Images

- Use `figure.image` with `data-ratio` so nothing shifts on load. Treat images (`data-treatment`) so they sit in the palette.
- Every image carries a provenance line in its caption: `generated` or `photo` · prompt id · model · date · seed · treatment. No untraced images. (Video posters and stills are traced by their video's page instead; see Subject first.)
- Generate images only with the templates in `prompts/`, with the skin brief pasted in. No text in generated images; the page sets type.

## Rules (the default skin; a skin may relax the ones marked ◇)

1. Every object shows its identifier in the register column (`.row > .id`), at the same x. Dates, claim ids, case numbers, commits, run ids. (A record's own id, status, and history may sit in its page's closing disclosure; see Subject first.)
2. ◇ Hierarchy from hairlines and alignment. No cards, no border-radius, no drop shadows, no gradients, no backdrop blur, no colored edge stripes. Fills are `data-surface`. At most one `deep` or series surface per screen, never two adjacent. `deep` is `--deep`, never `#000`. (A skin may set `--radius` up to 12px and a hard-offset `--shadow`; never a blur.)
3. ◇ Identifiers, numbers, labels, and metadata are lowercase monospace. Prose and headings are sans. No `text-transform: uppercase` anywhere. Case only for names, symbols, and sentences. (A skin may set `--label-case` and `--label` for spaced caps; identifiers stay mono.)
4. One accent (`--accent`) for links and current. Three states: `--ok` `--open` `--stop`. Four series `--s1`–`--s4` for charts and labs only. Color never appears without a glyph or a word.
5. Every component must have a plain-text twin (a table, list, or key/value block). If you cannot write it as text, do not add it. Accents come only from `accents.html`, rationed: one signature accent per page, one texture per page, one stamp per site.

## Subject first (this site)

Readers come for simulation games, not for how the atlas is built. Every page except the paper (`paper/`) and the about page (`about/`) leads with the subject:

- A record page opens with what the record is. Its id, status, checks, ratings, history, and file links go in one `details.disclosure`, collapsed, at the end of the page, opened by a sentence on why they matter.
- A number strip or chart names the paper section that makes its case, not a file, run, or commit. The paper's own figures keep their source lines.
- Video posters and stills carry no provenance caption; the video's page and transcript say what is on screen and link each record.
- The paper and the about page show process in full, and every other page keeps them one click away.

## Numbers

- Exact results go in `.numbers` (20px mono). The stat-banner tell, and the scorer, start at 22px; nothing in the system sits in a row above that size. Counts (works, claims, runs) go in `.meta`, never in a number strip.
- Live values go in `.numbers[data-style="readout"]` (18px mono).
- A filled figure block (`.panel[data-surface="s1"]` with one `.number[data-style="block"]`) is always alone. A row of them is forbidden.
- Every number strip or chart carries a source line naming the run, claim, or commit, or, outside the paper, the paper section that makes its case (see Subject first).

## Copy

- Plain verbs, sentence case, no filler. No em dashes. Straight quotes. No emoji.
- Headlines state a specific claim or question, never an aspiration.
- Do not invent numbers, identifiers, or citations. Mark sample data as sample.

## Before you finish

- Run `npx design-slop-cop <url>` on any new page. It must score 0/14.
- Check the page at 390px wide. The register column collapses to inline ids; nothing scrolls horizontally except `.table-wrap` and, on phones, the family bar (`.family`), whose row of sister sites scrolls sideways when it does not fit. A citation to copy is a `pre[data-style="citation"]`, which wraps instead of scrolling.
- Confirm every new component has its twin shown in `components.html`.
