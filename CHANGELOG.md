# Changelog

Contract, schema, vocabulary, and rubric changes. Data changes are tracked by run records in `log/runs/` and by git history.

## 1.2 additions (2026-10-31, citable release)

ADR-0008 (run `2026-10-31-citable-release`). No schema, vocabulary, or data rule changed.

- **Paper:** version 0.3, dated 2026-10-31, in `report/meta.yaml`, which now says how a release is cut.
- **Citation:** the build writes `CITATION.cff` (CFF 1.2.0) from `report/meta.yaml` and the byline; E023 and invariant I1 now cover it. Optional `doi` in `report/meta.yaml` (into `CITATION.cff` and the paper's BibTeX) and `orcid` in contributor profiles.
- **PDF:** `make pdf` (`scripts/paper_pdf.py`) writes the paper as LaTeX with TikZ figures in `pdf-out/` and compiles it with tectonic, byte-identical for one tectonic version. Optional; not part of `make check` or CI.

## 1.2 additions (2026-10-27, three-lab review)

Outside models reviewed the paper and the contribution rules cold: gemini-3.1-pro-preview, meta/muse-spark-1.3, and openai/gpt-5.3-codex for the scope-check code. Each finding was checked against the data before acting (ADR-0007, run `2026-10-25-gemini-review`, written under 1.1 and rebased onto 1.2).

- **Report:** §5.4 states both the configured k and the rule's current pick (on 2026-10-25, adding three games moved it from 24 to 19, inside the drift tolerance); §8.2 no longer says the family concentration is independent of family size (per mechanic, world generation is second); §5.6 says the p-values describe one rater; §5.5 says the independence null ignores game size.
- **Rules:** E039 counts a `verification` run only from the owner, members, or invited collaborators; a PR appends only its own run to `provenance.reviewed`; a run-only PR needs an invited author; rewording a sourced claim needs a new quote or a dispute; a deprecation keeps the record's content; a sign-off is a real trailer line. E034 requires a quote on every claim of a `verified` record. E021 and E029 texts match the code.
- **Report:** the abstract no longer states single-rater correlations causally; "in or before 2000"; §5.5 counts tension edges. Agents commit without sign-off and the operator signs off after reading the diff (`git rebase --signoff origin/main`).
- **Tooling:** `check_sources.py` stops after three straight network failures and flags source domains the dataset has never cited.
- **Tasks:** seven suggested games added to `tasks/candidates.yaml`; four mechanic proposals and three technique leads recorded in the run.

## 1.2 (2026-10-26)

ADR-0006, a visual vocabulary for the video series (run `2026-10-26-visual-vocabulary`).

- **Rules:** E040 frame-line, E041 visual-icon, E042 frame-icon, W108 visual-coverage; invariant I16. The contract now also applies to `media/visual/` and the Frame lines that use it.
- **Visual vocabulary:** `media/visual/vocab.yaml` and 79 icons in `media/visual/icons/`, drawn in a checked SVG subset (25 mechanics, 1 family, 4 subgenres, 49 nouns), built by `scripts/visual` into `dist/visual/` at 3 px and 4 px per dither pixel through an 8x8 Bayer dither. `media/visual/README.md` says how to add one.
- **Scripts:** `**Frame.**` lines choose a picture's frame from ten templates (anatomy, chain, compare, count, timeline, formula, scale, record, moment, toysim). Episode 1 and shorts 1, 4, 5, and 7 carry them; the other scripts render as before.
- **Renderer:** `scripts/video/framedata.py` resolves frames from the dataset with a source line on each; `templates.js` draws them; the main entity is a one-line chip while a frame is up; labels are lowercase mono; IBM Plex is vendored in `media/fonts/` (SIL OFL 1.1) and the render stops if a face fails to load.
- **Build:** `scripts/build.py` writes binary outputs; Pillow is pinned.

## 1.1 (2026-10-25)

ADR-0004, contributor readiness.

- **Schema:** claim `quote` and `locator`; source `archived` (Wayback snapshot); `assertions` and `ratings` on games, mechanics, techniques, opportunities; game `store_ids` (steam, igdb, wikidata); opportunity `falsifiable_signal.resolution`; run `calibration` (raw blind scores).
- **Vocabulary:** new `prediction_outcome`; `time_model` and `modding` terms declare `requires_mechanic` / `allows_mechanic`; `modding` and `real-time-pausable` definitions sharpened.
- **Registry:** `contract_history` (E028 now accepts any listed version no newer than the current one) and `contribution` limits.
- **Rules:** E032 entity-assertion, E033 field-bound-mechanic, E034 evidence-quality, E035 independence, E036 calibration, E037 ratings, E038 prediction-resolution, E039 pr-scope; W105 source-archive, W106 prediction-overdue, W107 cluster-k-drift. E023 now checks GENERATED blocks only (dist/ is not committed); E029 cluster assertions require stable co-clustering and accept `cooccur.` and `cocluster.` references; E005 hint corrected.
- **Analysis:** cluster count from a stated stability rule (k = 24) over 1,000 hash-assigned subsamples, cluster stability, co-clustering, ARI and NMI against subgenre with a permutation null, `prevalence_rank`, per-mechanic family exposure ranking, prediction status, rater agreement, calibration results.
- **Build and CI:** dist/ gitignored; `build.py --out`; `make determinism` in CI; Pages workflow builds and publishes dist/ with the site; `sources` workflow (claim quotes, store ids, archive suggestions); PR scope check with DCO sign-off.
- **Docs:** CONTRIBUTING.md, CODE_OF_CONDUCT.md, `tasks/` briefs, issue forms, versioned calibration sets (`calibration/mechanics-v1.yaml`), CODEOWNERS for report, analysis, mechanics, opportunities, calibration.
- **After independent review (same release):** subsamples assigned by hash so adding a game redraws nothing; pair thresholds 0.9/0.1; tolerant W107; assertion references hardened (unknown right-hand refs, cluster labels, misspelled rank ids); E028 run dates checked against contract history; E034 judges wikis by url and binds snapshots to their url; E035 normalizes model ids; E037 requires the creator's score, verification raters, one rating per rater; E038 date rules for refuted and withdrawn; E039 binds operator to PR author and protects provenance, rating attribution, and quotes on new claims; `check_sources.py` searches full text before failing.

## 1.1 additions (2026-10-25, book and series draft)

The whole book and series drafted (run `2026-10-25-book-draft`). No contract rule changed.

- **Prose:** thirteen chapters in four parts and a preface in `book/src/`, with a contents page, a glossary of every mechanic by family, and the catalog of games as back matter (the `book-glossary-*` and `book-catalog` tables in `report/tables.yaml`); twelve episode scripts in `media/episodes/`, twelve shorts in `media/shorts/`, and the film's assembly and new pieces in `media/mega/`. Chapter 1 is "Same parts" and chapter 3 "Old parts"; short 1 leads with one finding, and the shorts line is one finding per short.
- **Japanese subtitles:** `media/subtitles/ja/` holds cue sources for all twelve episodes, checked like the scripts; the build times them from the scene timings into `dist/media/subtitles/ja/*.srt` (`scripts/subtitles.py`), to be retimed against the recorded voice.
- **Figures:** seven figures added to `scripts/viz.py` (layer profile by subgenre, constraint profile, technique landscape, determinism by runtime, opportunity priorities, prediction timeline, pipeline), placed in the paper and the book and built into the site.
- **House style:** `book/STYLE.md` and `book/tells.yaml`, enforced by `scripts/style_check.py` in `make check` and CI. It fails the build on stock phrases, contrast frames, signposting, setup sentences, and narration that ends on a question.
- **Analysis:** stats and derived fields the book cites, among them core against supporting prevalence, a chance test for the share of mechanics seen by 2000 (`p_mechanics_seen_by_2000`), per-decade origins, family counts, technique risk and runtime counts, prediction dates written out for prose and narration, run and evidence counts, and a `subgenre-spend` table. Figure captions written for the paper have their section numbers mapped to chapters in book and media output.
- **Paper:** the abstract's second finding and section 5.2 now report the chance test: random sets of the same number of games cover nearly as many mechanics as the games released by 2000 (p = 0.11), so the paper claims reuse, not an early-set vocabulary.
- **Rights:** `media/rights.yaml` lists every title the scripts show, with each publisher's video policy as read on 2026-10-25: 5 allowed, 23 allowed with conditions, 1 not allowed (Gran Turismo 7, now shown as a labelled graphic), 37 with no usable policy.
- **Fact-check:** fresh agents read every chapter and script against the records, twice for the first draft and once for the expansion. Sentences that drifted from or went beyond a record were rewritten to match it, repeated facts were reduced to one home chapter, and pictures that could pass for game UI are labelled as graphics or re-enactments.
- **Narration and video:** `media/narration.yaml` registers the ElevenLabs take that voices each scene (149 takes, about 101 minutes, including the thirteen episode scenes the film re-voices so their cross-references name chapters; their wording is in the film script's Film wording section). `scripts/video/narration.py missing` lists any line still without a take. `scripts/video/assemble.py` renders the twelve episodes, twelve vertical shorts, and the film into `video-out/final/` from the built scripts and those takes. Pictures use only the project's own graphics: entity cards from `dist/entities`, the catalog grid, and the paper's figures. Footage and cover art are left for an editor and `media/rights.yaml`.

## 1.1 additions (2026-10-25, book and video pilot)

Phase 1 of the book and video plan (run `2026-10-25-book-pilot`).

- **Prose:** `book/src/` (preface and chapter 1), `media/episodes/` (episode 1 script), and `media/shorts/` (the first 60-second short) are rendered to `dist/book` and `dist/media` and checked like the paper: tokens, links, citations, literal counts, assertions, placeholders.
- **Tokens and stats:** `{{derived:<id>.<field>}}` prints a per-record value (a game's mechanic count, a mechanic's prevalence); the analysis adds games per time model and the most common time model.
- **Rights:** `media/rights.yaml` registers each game whose footage a video uses, with its video policy and the date it was checked.

## 1.1 additions (2026-10-25, AI contributor pilot)

Fixes from the friction logs of the pilot agents that worked task issues end to end (ADR-0005, run `2026-10-25-ai-pilot`).

- **Analysis:** the white-space table admits mechanics used by at least 14 games (`min_prevalence_games`) instead of 8% of the catalog, so adding games cannot drop a mechanic from it; today's table is unchanged. A `rank.` reference to a row that has left its table fails as E029 with the cause, not as an unknown reference.

- **Schema:** `archived` also accepts the Wayback `id_` form (original bytes, for raw files and PDFs).
- **Tooling:** `check_sources.py --ids` scopes a check to the ids a task lists, and `--suggest-archive` prints each snapshot's date beside `accessed`. `pr_scope.py` checks the run file of a run-only PR and rejects a PR that adds a run and changes nothing. `make pr-check` stops if `git config github.user` is unset instead of comparing against `$USER`. `new.py run` prints the run id and says why `make check` is red until `method` is written. `check_sources.py` prints NOTHING CHECKED when every fetch failed, so an offline pass is not mistaken for a real one, a quote missing from a full-text page is fetched once more before it fails, a failed quote says how far it matched and what the page has instead, footnote markers such as [12] are ignored, and page text no longer gains a space where a link or bold run meets punctuation ("Studios</a>, with"), which had failed four correct Wikipedia quotes in the catalog pilot. Task issues for checkable briefs carry the exact `check_sources.py --ids` command. The tasks workflow never lists a record that is already in a task issue for the same brief, open or closed, or that an open pull request touches, so two contributors are not handed the same record (`make_tasks.py --exclude`).
- **Docs:** the archive brief says which snapshot to use (dates, raw files, paywalls), what to do without network access to archive.org, and that only sources actually archived are marked reviewed; the store-ids brief gives edition rules (later paid edition of the same game, series records, renamed developers), a fallback when Wikidata and IGDB cannot be opened, and marks only changed games reviewed; the source-claims brief runs as `maintenance` (quoting is not verification and needs no independence) and covers claims that overreach, bundle facts, state an absence, or cite a repository root, copies of DOI-only papers, locator forms, and agent fetch tools that return only fragments; AGENTS.md says a run that changes nothing is reported on the issue, not opened as a PR; the issue size rule names the 30-source limit; CONTRIBUTING.md says the sign-off is the operator's attestation.

## 1.0 (2026-10-23)

- Initial contract (CONTRACT.md), schemas for game, mechanic, technique, opportunity, source, run.
- Closed vocabularies in `vocab/`, edge types with single owners, anchored rubrics and composites.
- Validator rules E001-E031, W101-W104; deterministic build with projections to tables, graph, wiki, paper, and site.
- ADR-0001: repository architecture.
- ADR-0002 (pre-release hardening after an independent drift test): run `kind` with E031 (only taxonomy runs create mechanics; only verification runs verify), report assertions E029, style lint E030, broader literal-count lint E021 with citation exemption, placeholder lint across vocab and report prose, required GENERATED blocks, future-date checks for games and full source dates, run contract version check, W103 thin decompositions, source id pattern in schema, CODEOWNERS for contract surfaces.
- ADR-0003 (pre-release, after an independent content review): inverse-prevalence weighting and k=16 for game clustering, time-and-pacing excluded from white space, `field.` and `rank.` references in report assertions, schema rule that determinism-breaking techniques list determinism as a risk (`risks` up to six), W104 maturity-dates warning, prediction criteria with a post-2026-10-24 window and objective thresholds.

## 1.0 additions (2026-10-25)

- Website projection `dist/web/` (scripts/web.py), published by `.github/workflows/pages.yml`; styled with Register (vendored `web/register.css`, contract `web/DESIGN.md`).
- `{{viz:<name>}}` report token for interactive figures from scripts/viz.py (E019 covers unknown names); figures render as static SVG in paper.md.
- Dependencies pinned in requirements.txt; CI runs Python 3.13.
