# AGENTS.md: operating procedure for AI agents (and humans who want zero surprises)

You are contributing to a research graph that many agents and people edit concurrently. Drift happens when contributors invent fields, terms, ids, or numbers. This file removes those choices. Follow it literally. When it is silent, choose the option that changes the fewest files and record your doubt as a `proposal` in your run file.

`CLAUDE.md`, `GEMINI.md`, `.cursorrules`, and `.github/copilot-instructions.md` point here (Codex and most other agents read this file directly). `CONTRACT.md` is the law; this file is the procedure.

## 0. Before you touch anything

```bash
pip install -r requirements.txt
make hooks          # optional: validate before every commit
make check          # must be green before you start; if it is red, stop and report
```

Read, in order: `CONTRACT.md` §2 (invariants), the brief for your task in `tasks/` if you have one, the schema for every type you will edit (`schema/<type>.schema.json`), and the vocab files those schemas reference. Do not rely on memory of a previous version of this repo.

Work arrives as GitHub issues labeled `task`, each naming a brief and at most 10 records. Comment `claiming` on one issue; that issue becomes one run and one pull request (`tasks/README.md`).

## 1. Open a run

Every change belongs to exactly one run.

```bash
python scripts/new.py run <slug> --kind <kind> --actor agent --operator <github-handle-of-accountable-human> \
  --model <model-id> --harness "<tool you run in>" --purpose "<one sentence>"
```

`--kind` says what the run may do: `taxonomy` (the only kind that may create mechanics), `catalog` (games), `technique`, `synthesis` (opportunities, report), `verification` (the only kind that may set `status: verified`, add `ratings` to someone else's record, or resolve a prediction), `maintenance`. The validator enforces this (E031, E037, E038).

`--operator` is the accountable human's GitHub handle, and must be the account that opens the PR (E039); `--model` is the exact model id. Record both truthfully: the checks below compare them, and they cannot detect a false entry. Independence is checked on both: a run that verifies, rates, or resolves someone's work needs a different operator, and a different model when both runs are agents (E035). A run that creates mechanics or adds mechanic ratings first records a calibration: its rater scores the reference set in `calibration/` from the sheet alone (`python scripts/calibrate.py sheet`, then `score --write-run <run-id>`; E036, `tasks/rate-scores.md`). The reference scores are public, so a passing calibration shows that the rater reads the anchors as the set does; only the procedure keeps the scoring blind (CONTRACT.md I14).

The command prints the run id (the date plus your slug). The new file's `method` is `TODO`, so `make check` stays red (E027) until you write it; that is expected, and the check before you start is the one that must be green. Fill `method` (what you searched, read, or computed, and what failed) and keep `proposals` for anything you wanted to do but this file does not allow. Every entity you create gets `provenance.created: <run-id>`. Every existing entity you actually re-check gets your run id appended to `provenance.reviewed`. Re-checking means you opened the first source of every claim you touched and confirmed it still supports the claim, or recorded in `method` why it does not. One you looked at but did not re-check (a snapshot you could not reach, a page you could not open) is not marked, and your `method` names it instead. A PR appends only its own run (E039).

If the run ends up changing no records or sources (every lookup was blocked, say), do not open a pull request: comment on the issue with what you tried and what failed, and leave the run file uncommitted.

## 2. Search before you create

```bash
python scripts/find.py "<name or concept>"           # all types
python scripts/find.py "<concept>" --type mechanic
```

If something close exists, edit it instead of creating a near-duplicate. Duplicates are the most common drift.

## 3. Admission tests

### Game inclusion test
Include a work if all hold: (a) released commercially, freely, or as a public research demo; (b) its core loop is driven by a model of some system (economy, ecology, physics, society, bodies, machines) whose state evolves without the player scripting each change; (c) it contributes at least one mechanic usage not already well represented, or it is a lineage-defining title. A work that fails (b) but is included anyway for specific mechanics (a puzzle or toy whose rules matter to simulation design) sets `boundary_case: true`; say in `design_notes` which mechanics justify it.

If no subgenre or other vocab term fits, pick the closest term and file a `vocab-term` proposal. If no mechanic fits a rule-system the game clearly has, **do not force-fit** the nearest mechanic (a wrong tag distorts prevalence and clustering); leave it out, describe it in `design_notes`, and file a `new-mechanic` proposal.

### Mechanic admission test (all four must pass)
1. **Nameable**: a designer would recognize it in games other than the one you are looking at.
2. **Atomic**: owns one kind of state and one update rule. If it splits into two parts that each appear without the other in real games, create two mechanics.
3. **Tunable**: has at least two levers you can list in `design_levers`.
4. **Removable**: a game could drop it and still run.

If a candidate fails, it is a game-specific feature (describe it in that game's `uses` note) or an opportunity. Agents doing game or technique work **may not create mechanics**; add a `new-mechanic` proposal to the run instead. Mechanic creation is reserved for runs of kind `taxonomy` (E031).

### Technique inclusion test
A dated, citable result (paper, preprint, model release, shipped system, or engine feature) that changes at least one mechanic, with `affects` edges that say how (`effect` vocab). Vendor marketing alone fails. `year` is the year of the key result. `maturity` and `trl` describe deployment **in games**, not in AI generally.

### Opportunity test
Names at least one mechanic in `involves`, has a `validation_experiment` a small team could run, and a `falsifiable_signal` with a `resolve_by` date and criteria a stranger could check.

## 4. Fields: how to fill them without drifting

| Situation | Rule |
|---|---|
| Categorical field | Use an existing term from the vocab file named in the schema (`x-vocab`). Missing term → proposal `vocab-term`, pick the closest existing term now. |
| Ordinal score | Read the anchors in `vocab/rubrics.yaml`. Pick the anchor whose text matches. Between two, take the lower. Never adjust a score to make a ranking come out a certain way. To disagree with an existing score, do not overwrite it: in a verification run, record the original score as a rating from the creating run (unchanged), add your own rating (field, value, run, rationale), and store the lower median (E037). |
| Claim | `text` says what the source supports; `quote` is the shortest verbatim passage from the first source that supports it, `locator` says where. Every new claim carries a quote (E039). CI fetches the source and fails when a page holding the full text lacks the quote; when it can only reach an abstract or landing page, it warns and the reviewer checks. |
| Text about the dataset | A sentence in any record that states a finding about this catalog ("the most used", "rarely combined", "no technique links to") carries `assertions` that fail the build when the data changes (E032), e.g. `derived.tech-tree.prevalence_rank <= 5`, `cooccur.power-grid.weather <= 1`, `rank.whitespace.lifecycle-aging.production-chain <= 10`. |
| `time_model`, `modding` | Two mechanics follow these fields exactly (E033): `real-time-pausable` games tag `variable-speed`; `scripting` and `total-conversion` games tag `modding-api`. Pick the true field term, then tag. |
| `store_ids` | Steam app id, IGDB slug, Wikidata id, only for the exact edition the record describes (`tasks/store-ids.md`). |
| Source `archived` | A Wayback snapshot URL of `url`, taken when you read it (`tasks/archive-sources.md`). |
| Prediction `resolution` | Only in a verification run independent of the opportunity's creator: outcome, date, run, evidence, note (`tasks/resolve-prediction.md`). |
| `summary` | One sentence, no markdown, no hype adjectives (revolutionary, groundbreaking, game-changing), no em-dashes. |
| Long text | Specific and mechanical. Name the variables and the update rule. Cite numbers only if a source supports them. |
| Game `mechanics` | 6–14 entries typical; fewer than 5 raises W103. `core` only for mechanics whose removal changes the game's identity; every core entry needs a `note` saying how this game implements it. |
| `influenced_by` | Only documented or widely acknowledged lineage. Earlier games only (E025). |
| Mechanic relations | `requires` for hard dependencies; `specializes` for narrower forms; `synergy`/`tension` stored only on the id that sorts first in plain character order, hyphens included, as Python sorts strings (E010). Never list games or techniques on a mechanic. |
| Technique `affects` | One entry per mechanic actually changed; `effect` from `vocab/effect.yaml`; note says what changes. |
| `deployed_in` | Only games in `data/games/` where the technique is used (shipped or public demo). |
| Dates | `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` at the precision you know. |
| Derived numbers | Never store counts, prevalence, earliest year, priority, clusters, or backlinks. The build computes them. |

## 5. Evidence and status

- No source → `status: asserted`. That is fine; the verification queue exists for this.
- You cite a source that supports the factual fields → `status: sourced`.
- You re-check someone else's sourced entity against its sources in a run of kind `verification` → append your run to `provenance.reviewed` and set `verified`. Never verify an entity your own run created; a review by any other kind of run does not count (E031). The verifying run needs a different operator, and a different model when both are agents (E035). An entity whose sources are all encyclopedias or wikis stays `sourced` (E034).
- A source contradicts a sourced entity → `status: contested`, add a claim with `disputes`, cite both sides. Do not silently overwrite.

### Sources
- Id: `src-<publisher-or-first-author-surname>-<year>-<short-slug>`, e.g. `src-park-2023-generative-agents`, `src-steam-2024-manor-lords`; Wikipedia articles use `src-wikipedia-<slug>` (no year). The schema enforces both forms (E004).
- Check `data/sources/` before creating; one file per work. If it exists, cite it.
- Prefer primary sources (paper, official blog, store page, developer postmortem) over aggregators. `accessed` is the date you read it, and `archived` a Wayback snapshot of it.
- Cite only what you opened and read. Never create a source record from memory or from a search snippet.
- Every source must be cited by something (E011).

## 6. Writing the report

`report/src/*.md` is prose plus tokens. Rendered by `make build` into `dist/paper/paper.md` and the website (`dist/web/`, published at simgrammar.com).

| Token | Renders |
|---|---|
| `{{count:game}}` (any type) | live entity count |
| `{{count:edge:uses}}` (any edge type) | edge count |
| `{{stat:<name>}}` | a statistic from `dist/analysis/stats.json` |
| `{{table:<name>}}` | a table from `report/tables.yaml` or `dist/analysis/*.csv` |
| `{{figure:<name>}}` | an SVG from `dist/analysis/figures/` |
| `{{viz:<name>}}` | an interactive figure from `scripts/viz.py`: a static SVG in `paper.md`, interactive on the website, always with a plain-text twin table |
| `{{vocab:<vocab>:<term>}}` | a vocab label |
| `{{assert:<ref> <op> <value\|ref>}}` | renders nothing; fails the build (E029) if false. Put one next to every sentence that interprets a ranking, sign, ordering, or grouping. `<ref>` is a stat (`rho_legibility_emergence_potential < 0`), an entity's derived field (`derived.rimworld.cluster == derived.dwarf-fortress.cluster`), a stored field (`field.genie-world-models.maturity == prototype`), a row rank in a generated table (`rank.whitespace.lifecycle-aging.production-chain <= 10`; 9999 when no row holds all the ids, including a row that has left the table, and an error when an id is neither in the table nor a record), a co-occurrence count (`cooccur.power-grid.weather <= 1`), or a co-clustering share (`cocluster.rimworld.the-sims < 0.8`). A cluster-membership assertion passes only if the pair co-clusters in at least `clustering.stability.together` of resampled clusterings (at most `apart` for `!=`), so assert only groupings that are stable, and describe weaker links by comparison (`cocluster.a.b < cocluster.a.c`). Cluster labels (`C03`) and ranks in the cluster tables change with k and are rejected |
| `[[id]]`, `[[id\|text]]` | link to an entity |
| `[@src-id]`, `[@src-a; @src-b]` | numbered citation |

Never type a dataset count ("140 games") into prose (E021). When a sentence interprets data ("X is the most exposed family", "the correlation is negative"), pin it with an assertion so the build fails if a later data change makes the sentence false. If you need a new statistic, add it to `scripts/analyze.py` (deterministic) in the same PR. If you need a new table view, add it to `report/tables.yaml`. The number of game clusters (`clustering.k` in `report/analysis.yaml`) is set by its stated stability rule, never by what the clusters look like; W107 says when the rule would now pick another k.

### The website

`scripts/web.py` projects everything into `dist/web/`: a home page that links into every part, the paper (at `paper/`), the book (one chapter a page, from the build's `dist/book`), one page per record, an index per type, a watch page with a page per episode, a find page that lists every page, and an about page (how the atlas is made, the downloads, the research log, the vocabularies). Pages lead with the subject: a record's status, checks, ratings, and history sit in one collapsed block at the end of its page (`web/DESIGN.md`, Subject first). Pages link each other both ways wherever the data relates them: a record page lists the paper's sections, the chapters, the episode moments, and the shorts that link, name, show, or cite it, and its backlinks list every incoming edge; chapters and episodes link each other and their shorts. Records and indexes carry the dithered icons of ADR-0006 (mechanics as icon tiles, games as parts boards, opportunities by horizon, each index keeping its table as the plain-text twin), and `scripts/og.py` draws a link-preview image for every page. The shorts and episodes on the site are the ones `media/published.yaml` lists; `scripts/video/publish.py` writes it after a render, the files go on a GitHub release, and the Pages workflow fetches them and checks each sha256. Each episode script opens with a `**Summary.**` line, which the watch page and the episode's page show. An episode's entry carries its scenes from the render, so its page can jump to each scene and record pages can link the moments a record is on screen. Each scene also carries a digest of its narration as rendered: when the dataset moves on and the built script no longer says the same thing, the episode page marks that scene, and re-rendering and re-publishing clears it. The film stays off the site. It uses Register (`web/register.css`, vendored; its contract is `web/DESIGN.md`). Follow that contract when you change a page template: no new stylesheet or classes, lowercase mono labels, one accent, every component with a plain-text twin, and every page complete without JavaScript (`web/simgrammar.js` only adds interaction). Figures are laid out in Python, deterministically; the script never lays anything out. The domain lives in `report/meta.yaml` (`site.domain`) and is written to `dist/web/CNAME`. `.github/workflows/pages.yml` builds on every push to `main` and publishes `dist/web/` as the site with the other projections under `/dist/`.

### The videos

`scripts/video` renders the episodes, shorts, and film from the scripts in `media/`. A `**Frame.**` line under a Picture line chooses the frame that shows it, from the icons in `media/visual/` (ADR-0006, `media/visual/README.md`). A Frame's numbers come from the dataset at render time; any number the line itself states must appear in the text of the record or source it cites with `from=` (E040). Draw a missing icon in the SVG subset before a Frame names it (E041); the build stops when a frame would draw any element without one, including the parts and terms it takes from the data (E042). Icons draw generic subjects only, and nothing in a frame copies a game's art, logo, cover, characters, or UI.

## 7. Never

- Edit anything between `<!-- BEGIN GENERATED -->` markers or in `CITATION.cff` (the build writes both), or commit `dist/` (it is gitignored; CI builds it).
- Cite a source you did not open, paraphrase inside a `quote`, or verify, rate, or resolve work from your own operator or model.
- Change an existing record's `provenance.created`, drop a `reviewed` entry, or attribute a rating to any run but your own (E039).
- Put more than 10 records or 30 sources in one PR, or more than one run (E039).
- Add a field, vocab term, edge type, or rubric anchor without an ADR (`decisions/`).
- Change or reuse an id. Delete a merged entity (deprecate it).
- Store an inverse edge or a derived number.
- Leave a placeholder (`TODO`, `TBD`, `FIXME`, any case) in data, runs, vocab, or report prose (E027).
- Work around a failing rule. If you believe a rule is wrong, stop, keep `make check` green, and file a `rule` proposal.

## 8. Finish

```bash
make build            # build dist/ locally (for reading) and refresh GENERATED blocks; it does not validate
make check            # validate + report/record assertions + build --check; must be green
git add -A && git commit -m "<type>(<scope>): <what> [run:<run-id>]"   # agents: no -s (see below)
make pr-check         # what CI will say: PR scope (E039) and, with network, the quotes and store ids you touched
```

`python scripts/validate.py --warnings` lists the warnings `make check` only counts. If your data change fails a report or record assertion you did not write (E029, E032), a finding moved: do not edit `report/` or records outside your task. Open the PR with the error quoted, and a maintainer rewrites the sentence.

Rewrite the run's `method` before you commit: what you searched, opened, and computed, and what failed. `dist/` is gitignored, so a data PR contains records and one run file. Commit types: `data`, `taxonomy`, `vocab`, `schema`, `report`, `build`, `docs`. One run per PR, at most 10 records and at most 30 sources, every commit signed off (E039). An agent does not sign off: the sign-off is the operator's attestation (Developer Certificate of Origin), so the operator reads the diff and then signs every commit with `git rebase --signoff origin/main` before pushing. A human working without an agent uses `git commit -s`. CI also runs `make determinism` and, for the records you touched, checks claim quotes and store ids against the live web (`.github/workflows/sources.yml`). The PR template asks for the run id, the issue, the rule codes you hit, and your proposals. Paths in `.github/CODEOWNERS` (the contract and its code, the report and its analysis parameters, mechanics, opportunities, calibration) need maintainer review because the validator cannot judge whether such a change is justified; it can only enforce the contract as written.

## 9. Parallel agents

When several agents work at once, partition by **files**, not topics: each agent owns a disjoint set of entity files and only reads others. Shared files (sources) are append-only: check existence immediately before writing; if a source id already exists, cite it rather than rewriting it. The orchestrator runs `make check` after merging and owns conflict resolution.
