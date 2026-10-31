# SimGrammar Contract

**Version 1.2** · Applies to everything under `data/`, `vocab/`, `schema/`, `log/`, `report/`, and to the visual vocabulary in `media/visual/` with the Frame lines that use it.

This file defines what the repository guarantees. Code in `scripts/` enforces it; the rule table below is generated from `scripts/rules.py`, so the documented rules and the enforced rules are the same list. If this file and the code disagree, the code is the bug.

## 1. What this repository is

A versioned, machine-readable research graph of simulation game design:

- **games**: simulation games, each decomposed into the mechanics it uses
- **mechanics**: atomic rule-systems, each analyzed on its own
- **techniques**: math, AI, ML, and LLM results that change what mechanics can be
- **opportunities**: falsifiable design bets that combine mechanics and techniques
- **sources**: everything cited
- **runs**: append-only provenance records of who changed what, how

Every other artifact (tables, graph files, wiki, paper, site) is a projection built from those files.

## 2. Invariants

**I1. One source of truth.** Canonical state is `data/**/*.yaml`, `vocab/*.yaml`, `schema/*`, `log/runs/*.yaml`, `calibration/*.yaml`, and `report/src/*.md` with the analysis parameters in `report/*.yaml`. `dist/`, every `<!-- BEGIN GENERATED -->` block, and `CITATION.cff` are projections. `dist/` is not committed: CI builds it and the Pages workflow publishes it with the site. GENERATED blocks and `CITATION.cff` are committed and checked against a fresh build (E023). Never edit any of them by hand.

**I2. One entity, one file, one id.** File stem equals `id`. Ids are kebab-case and unique across all types (sources use the `src-` prefix). An id never changes after merge. To rename or merge, set `deprecated: {superseded_by, reason}` on the old entity and repoint edges (E014).

**I3. Closed schemas.** Every schema sets `additionalProperties: false`. A new field is a schema change (§4).

**I4. Closed vocabularies.** Every categorical field draws from `vocab/<name>.yaml`. A new term is a vocab change (§4). There are no free-form tags.

**I5. Anchored scores.** Every ordinal field names a scale in `vocab/rubrics.yaml` and is scored by matching anchor text. Between anchors, take the lower. Changing an anchor re-scores the dataset silently, so it is a contract change.

**I6. Edges live in one place.** Each edge type has one owner type (table below). Inverses are computed and never stored. Symmetric edges (`synergy`, `tension`) are stored only on the entity whose id sorts first (E007, E010).

**I7. Derived values are never stored.** Counts, prevalence, earliest appearance, clusters, exposure, priority, and backlinks are computed by `scripts/analyze.py`. A stored copy would drift; the schema has no field for them.

**I8. Status is a claim about evidence.** `asserted` means unsourced. `sourced` requires citations. `verified` requires a run of kind `verification`, distinct from and not earlier than the creating run, listed in `provenance.reviewed` (E031). That run has a different operator, and a different model when both runs are agent runs (E035), and the entity cites at least one source that is not an encyclopedia or wiki (E034). No one verifies their own work, and no model verifies its own output. Only runs of kind `taxonomy` create mechanics (E031). Techniques always cite (E012). A claim may carry a verbatim `quote` from its first source, which CI checks against the source (or its Wayback snapshot) whenever the record changes.

**I9. Provenance is append-only.** Every entity names the run that created it. Run files are never rewritten after merge except for typos. Git history plus run records reconstruct how every fact entered the graph.

**I10. Prose cannot outrun data.** Report text gets dataset numbers only through tokens (`{{count:game}}`, `{{stat:...}}`, `{{table:...}}`). Literal counts fail E021. Sentences that interpret data (a ranking, a sign, a cluster membership, a technique's maturity or determinism impact) carry `{{assert:...}}` tokens that fail the build when the data stops supporting them (E029); a cluster-membership assertion also needs the grouping to be stable under resampling. Record text that states a finding about the dataset carries `assertions` checked the same way (E032). Every `[[id]]` link and `[@src-...]` citation must resolve.

**I11. Builds are deterministic.** Same inputs, byte-identical outputs. No timestamps, no unordered iteration, no network calls in the build. CI proves it on every push by building twice under different `PYTHONHASHSEED` values and diffing the trees (`make determinism`). Anything that needs the network (source and store-id checks) runs in its own workflow, outside the build.

**I12. Admission tests are part of the contract.**

- *Game*: a released or publicly demonstrated work whose core loop is driven by a model of some system (§AGENTS.md "Game inclusion test"). Works that fail the "driven by a simulated system" condition but are included for specific mechanics set `boundary_case: true`.
- *Mechanic*: passes all four: (1) **nameable**: designers would recognize it across games; (2) **atomic**: owns one kind of state and one update rule; if it decomposes into two mechanics that each appear without the other, split it; (3) **tunable**: has at least two levers; (4) **removable**: a game could drop it and keep running. Combinations of mechanics are opportunities or game features, not mechanics.
- *Technique*: a dated, citable result (paper, release, shipped system) that changes what at least one mechanic can be. Vendor marketing alone is not sufficient.
- *Opportunity*: names at least one mechanic, has a validation experiment, and a falsifiable signal with a resolve-by date.

**I13. Disagreement is data.** A disputed fact becomes `status: contested` with a claim whose `disputes` field cites the opposing source (E026). Do not overwrite another contributor's sourced claim without recording the dispute.

**I14. Scores are ratings.** Each rubric score is one rater's reading of anchor text. A record may carry `ratings` from further raters, each naming its run and rationale; a field with ratings stores their lower median (E037). A field with ratings includes the creator's original score, every other rating comes from an independent verification run (E035), and one rater gives one rating. Raters who create or rate mechanics first pass a calibration against the current set in `calibration/` (E036); its reference scores are public, so the calibration shows a rater reads the anchors as the set does, not that the rater scored blind. Agreement between independent raters is computed, never stored.

**I15. Contributions are bounded.** A pull request carries one run, at most `contribution.max_records_per_pr` records and `max_sources_per_pr` sources (schema/registry.yaml), never deletes a merged record, never edits a merged run, and every commit is signed off (E039). Paths in `.github/CODEOWNERS` need maintainer review.

**I16. Pictures come from the project's own vocabulary.** Video frames are drawn from the icons in `media/visual/` and the dataset, through `**Frame.**` lines in the scripts (ADR-0006). A Frame names ids that resolve and states no number that its cited record lacks (E040); the numbers it shows are read from `dist/entities`, the stats, or the rubrics at render time. Icons are original drawings of generic subjects in a checked SVG subset, and no icon id, label, or alias names a game (E041). Nothing in a frame copies a game's art, logo, cover, characters, or UI; a picture that resembles a game's UI is labelled a mock-up.

## 3. Change classes

| Class | Examples | Requires |
|---|---|---|
| Data | add or edit games, mechanics, techniques, opportunities, sources | run record, `make check` green |
| Prose | report/src edits | `make check` green (tokens, links, literal-count lint, assertions); maintainer review |
| Analysis | report/analysis.yaml, report/tables.yaml | maintainer review; changing `clustering.k` only by its stated selection rule, in a maintenance run |
| Calibration | calibration/*.yaml | ADR (it is a rubric change: it fixes how anchors are read) |
| Vocabulary | add, rename, or redefine a term | ADR in `decisions/`, migrate affected entities in the same PR |
| Rubric | change an anchor or composite weight | ADR, contract minor bump, note in CHANGELOG of which scores to revisit |
| Schema | add or change a field or edge type | ADR, contract minor bump (breaking: major), `schema/registry.yaml` `contract_version` bump, migration script if data changes |
| Rule | add or change a validator rule | ADR, edit `scripts/rules.py` and its implementation together |

Contract version lives in `schema/registry.yaml` and in the header of this file; CI fails if they disagree. Every version is listed with its effective date in `contract_history`, and a run records the version it was written under, so a contract bump never rewrites run files (I9).

## 4. Edge types

<!-- BEGIN GENERATED: edge-types -->
| Edge | Owner → Target | Inverse (computed) | Symmetric | Meaning |
|---|---|---|---|---|
| `uses` | game → mechanic | `used_by` | no | A game uses a mechanic. Attributes role (mechanic_role) and note. |
| `influenced_by` | game → game | `influenced` | no | A game's design draws on an earlier game. |
| `requires` | mechanic → mechanic | `required_by` | no | A mechanic cannot function without another mechanic. |
| `specializes` | mechanic → mechanic | `generalizes` | no | A mechanic is a narrower form of a parent mechanic. |
| `synergy` | mechanic → mechanic | `synergy` | yes | Two mechanics amplify each other's dynamics when combined. |
| `tension` | mechanic → mechanic | `tension` | yes | Two mechanics pull design in opposite directions; combining them needs a resolution. |
| `affects` | technique → mechanic | `affected_by` | no | A technique changes a mechanic. Attributes effect (effect vocab) and note. |
| `builds_on` | technique → technique | `built_upon_by` | no | A technique depends on or extends an earlier technique. |
| `deployed_in` | technique → game | `deploys` | no | A technique is used in a specific game, shipped or prototype. |
| `involves` | opportunity → mechanic | `involved_in` | no | An opportunity reworks or combines a mechanic. |
| `applies` | opportunity → technique | `applied_in` | no | An opportunity depends on a technique. |
| `precedent` | opportunity → game | `precedent_for` | no | A game partially demonstrates an opportunity. |
| `cites` | any → source | `cited_by` | no | An entity or claim relies on a source. |
<!-- END GENERATED: edge-types -->

## 5. Enforced rules

Run `make check`. Every finding names a rule code; `--json` gives machine-readable output with a fix hint.

<!-- BEGIN GENERATED: rules -->
| Rule | Name | Check | Fix |
|---|---|---|---|
| E001 | yaml-parse | Every data file parses as YAML and contains exactly one mapping. | Fix YAML syntax; one entity per file. |
| E002 | file-location | File stem equals `id`; file lives in the directory registered for its `type`. | Rename the file or move it; never change an id after merge (see E003). |
| E003 | id-unique | Entity ids are kebab-case and globally unique across all entity types. | Pick a distinct id. Search first with `python scripts/find.py <term>`. |
| E004 | schema | Entity validates against its JSON Schema (no extra fields, required fields present, lengths and types). | Match schema/<type>.schema.json. Unknown fields are never allowed; propose schema changes in the run's `proposals`. |
| E005 | vocab | Every `x-vocab` field uses a term defined in vocab/<name>.yaml. | Use the closest existing term now and file a `vocab-term` proposal in your run. Maintainers add terms by ADR (decisions/). |
| E006 | ref-missing | Every reference (`x-edge`, `x-ref`) resolves to an existing entity or run. | Create the target first or fix the id. |
| E007 | ref-type | Edge targets have the type declared in vocab/edge_types.yaml, and the edge is stored on its declared owner type. | Point the edge at an entity of the declared target type, and store it only on the declared owner type (vocab/edge_types.yaml); inverses are computed. |
| E008 | self-edge | No entity has an edge to itself. | Remove the self-reference. |
| E009 | duplicate-edge | The same (source, type, target) appears at most once. | Merge duplicate entries. |
| E010 | symmetric-owner | Symmetric edges (synergy, tension) are stored once, on the entity whose id sorts first. | Move the edge to the lexicographically smaller id and delete the mirror. |
| E011 | orphan-source | Every source is cited by at least one entity, claim, or report citation. | Cite it or delete it. |
| E012 | evidence | `sourced`/`verified` entities cite sources; `verified` has a reviewed run distinct from `created`; techniques always cite sources. | Add sources or lower status to `asserted`. |
| E013 | provenance | `provenance.created` and every `reviewed` run exist in log/runs/. | Create the run file with `python scripts/new.py run <slug>`. |
| E014 | deprecated-target | No edge points at a deprecated entity; `superseded_by` targets are live. | Repoint edges to the successor. |
| E015 | acyclic | `requires`, `specializes`, `builds_on`, and `influenced_by` graphs are acyclic. | Break the cycle; one direction is wrong. |
| E016 | game-mechanics | Each game has >=1 core mechanic, every core mechanic has a `note`, and no mechanic is listed twice. | Mark the identity-defining mechanics core and describe how the game implements them. |
| E017 | mechanic-grounding | Every mechanic with maturity classic/established is used by >=2 games; every mechanic is used by >=1 game unless maturity is experimental. | Tag the games that use it, lower maturity, or deprecate it into a broader mechanic. |
| E018 | rubric | Ordinal fields name a rubric scale that exists, and values are anchor levels of that scale. | Score against the anchors in vocab/rubrics.yaml. |
| E019 | report-token | Every `{{...}}` token in report/src resolves (count, stat, table, figure, viz). | Use a defined token; tables live in report/tables.yaml, stats in scripts/analyze.py, interactive figures in scripts/viz.py. |
| E020 | report-link | Every `[[id]]` link and `[@src-id]` citation in report/src resolves. | Fix the id or create the entity. |
| E021 | report-literal-stat | Report prose states no literal counts or percentages of dataset nouns (games, mechanics, techniques, uses, edges, sources...), allowing one word between number and noun (a wider gap catches rubric values such as 'emergence 5 means the game'), unless the same sentence carries a citation (an external figure). | Replace the number with a token such as `{{count:game}}`. |
| E030 | style | Names and summaries of non-source entities contain no em-dash, no markdown, and none of the banned hype words (revolutionary, groundbreaking, game-changing, unprecedented, cutting-edge, paradigm-shifting). | Rewrite plainly: commas or parentheses for asides, no emphasis markup, specific words instead of hype. |
| E031 | run-kind | Mechanics are created only by runs of kind `taxonomy` or `bootstrap`; status `verified` requires a `reviewed` run of kind `verification`, distinct from the creating run and dated on or after it. | Record a new-mechanic proposal instead of creating one; to verify, open a verification run and re-check the entity against its sources. |
| E022 | vocab-integrity | Vocab files have unique term ids, a definition per term; edge_types declare owner, target, inverse, symmetric. | Repair the vocab file. |
| E023 | build | The build succeeds, every GENERATED block in README.md, CONTRACT.md, and AGENTS.md and the whole of CITATION.cff equal a fresh build, and every required block is present (`python scripts/build.py --check`). dist/ is not committed: CI builds it, checks that two builds under different hash seeds are byte-identical, and deploys it. | Run `make build` and commit any changed GENERATED blocks and CITATION.cff (they change with contract, vocab, rule, or report/meta.yaml edits and new contributors, not with data). Never hand-edit either. |
| E024 | dates | `year_full_release` >= `year`; game years, technique years, and source dates (full date) are not in the future. | Correct the dates. |
| E025 | influence-order | A game's `influenced_by` targets were released in or before its year. | Reverse or remove the edge. |
| E026 | contested | `contested` entities carry at least one claim with `disputes` filled. | Record the dispute and its source. |
| E027 | placeholder | No string in data/, log/, vocab/, or report/src contains a placeholder (TODO, TBD, FIXME, any case). | Fill every field `scripts/new.py` scaffolded. |
| E028 | contract-version | The version in CONTRACT.md's header equals `contract_version` in schema/registry.yaml, every schema `$id` carries that version, and the version is listed in `contract_history`. Every run records a listed version no newer than the current one, is not dated before that version took effect, and does not record a version older than the one in force the day before its date. | Bump the header, the registry (with a `contract_history` entry), and every schema `$id` together; new runs record the current version (scripts/new.py does this). |
| E029 | report-assertion | Every `{{assert:<ref> <op> <value or ref>}}` in report/src holds. A ref is a stat, `derived.<id>.<field>`, `field.<id>.<path>`, `rank.<table>.<id>[.<id>]` (9999 when no row holds them all, including a row that has left the table; an id that is neither in the table nor a record is malformed), `cooccur.<mechanic>.<mechanic>`, or `cocluster.<game>.<game>`. A right-hand side that looks like a ref must resolve. Cluster labels cannot be compared with literals and cluster tables cannot be ranked; two games' clusters can be compared, and `derived.a.cluster == derived.b.cluster` also needs co-clustering of at least `clustering.stability.together` (`!=` at most `apart`), so only stable groupings can be asserted. | The data changed under the prose, or the grouping is not stable: rewrite the sentence next to the assertion, then update the assertion. |
| E032 | entity-assertion | Every entry in a record's `assertions` holds (same references and limits as E029). A record whose text states a finding about this dataset (a lint over phrases such as 'in the catalog', 'the white-space analysis', 'most common', 'rarely combined', 'no technique links', 'more ... than any other') carries at least one assertion. The lint only flags; review judges whether the assertions pin what the text says. | Correct the text to match the data, then pin each finding with an assertion such as `derived.tech-tree.prevalence_rank <= 5` or `cooccur.power-grid.weather <= 1`. |
| E033 | field-bound-mechanic | A mechanic named by a vocab term's `requires_mechanic` or `allows_mechanic` is field-bound: a game whose field takes a requiring term tags it, and a game tags it only when its field takes a requiring or allowing term (time_model and variable-speed; modding and modding-api). | Tag the mechanic, or correct the game's field to the term that describes it. |
| E034 | evidence-quality | Status `verified` needs at least one cited source that is not a wiki: neither kind `encyclopedia` nor a url on a wiki host or path, whatever kind it claims, and a verbatim `quote` on every claim and key result, so a verification leaves a checkable trace. A source's `archived` snapshot must be of its own `url`. | Cite a primary source (paper, store page, developer documentation, postmortem, talk) and quote every claim, or keep status `sourced`; archive the source's own url. |
| E035 | independence | A run that verifies a record, rates one of its scores, or resolves its prediction has a different operator from the run that created it, and a different model (compared without case or punctuation) when both are agent runs. | Have a different person, using a different model if an agent does the work, run the verification or rating. |
| E036 | calibration | The current calibration set (registry `contribution.calibration_set`) lists live mechanics whose stored scores equal its frozen ones. A run's `calibration` names a set in calibration/ and scores all of it with anchor levels. A run recording contract 1.1 or later that creates mechanics or rates mechanics needs a calibration whose within-one agreement with the set it names reaches `contribution.calibration_min_within_one`. | Score the set with `python scripts/calibrate.py sheet` before reading stored scores, record it with `score --write-run`, and recalibrate in a new run if agreement is low. A score change on a set mechanic updates the set file in the same PR. |
| E037 | ratings | Each rating names a rubric-scored field of its record with an anchor value. A field with ratings includes the original score as a rating from the creating run; every other rating comes from a verification run; no two ratings of a field share an operator and model; and the field stores the lower median of its ratings. | Record the creator's original score first, rate only in verification runs, one rating per rater, and store the lower median. |
| E038 | prediction-resolution | A prediction resolution comes from a verification run independent of the opportunity's creator (E035), is dated between 2026-10-24 and today, cites evidence unless withdrawn, is `refuted` only once the resolve-by date has passed, and is `withdrawn` only before it. | Resolve in a verification run by another operator, cite what settled it, and match the outcome to the date. |
| E039 | pr-scope | A pull request changes at most `contribution.max_records_per_pr` records and `max_sources_per_pr` sources; adds exactly one run file when it changes data, recording the current contract version, dated within the last 30 days, with the PR author as operator; every changed record names that run, keeps `provenance.created`, and keeps every `reviewed` entry; new ratings come from that run (or record the creator's original score unchanged); new claims carry a `quote`; a record being deprecated keeps its other content; a `verification` run counts only when the PR author is the owner, a member, or an invited collaborator (GitHub `author_association`); no merged record is deleted, no merged run file is edited, a run-only PR is rejected, and every non-merge commit is signed off (scripts/pr_scope.py, CI only; maintainer labels lift the size limits). | Split the PR, one run per PR opened by its operator, deprecate in a PR of its own, ask for an invitation (or open a Verification request issue) before verifying, leave merged provenance and runs alone, quote new claims, and sign off after reading the diff (`git rebase --signoff origin/main`). |
| E040 | frame-line | Every `**Frame.**` line in media/episodes, media/shorts, and media/mega parses (scripts/visual/frames.py), follows a Picture line in its scene, names ids that resolve (icons in media/visual/vocab.yaml, live games and mechanics, mechanic families, rubric-scored fields), finds its `at=` phrase in the scene's narration, and states no number that the record text named by `from=` lacks. | Fix the template or key, draw the missing icon first, quote the narration exactly in `at=`, and take numbers from the cited record or leave them out. |
| E041 | visual-icon | Every entry in media/visual/vocab.yaml has a kind, an icon file in the SVG subset (flat rect, circle, ellipse, line, polyline, polygon; 48 or 96 dpx viewBox; coordinates on the half-dpx grid; palette tones only; strokes of 1 to 3 dpx), and every icon file has an entry. Dataset-kind ids exist, noun and term ids do not reuse dataset ids, and no id, label, or alias names a game. | Redraw the icon inside the subset (media/visual/README.md), add or remove its vocab.yaml entry, and draw generic subjects only. |
| E042 | frame-icon | Every element a `**Frame.**` line draws has an icon in media/visual, once the frame is resolved against the build as the renderer resolves it: the parts of a game it takes apart, the vocab terms of a tally, the techniques of a pile, and the subgenre emblem of a game it shows. The renderer draws an element with no icon as a blank tile, so the build stops instead (`python scripts/build.py`, scripts/visual/check.py). | Draw the icon in the SVG subset (media/visual/README.md) and list it in media/visual/vocab.yaml; a vocab term takes the prefix its field uses in scripts/video/framedata.py (TERM_ICON). |
| W101 | unused-vocab | Vocab terms not used by any entity (warning). | Fine early on; prune or document before 2.0. |
| W103 | thin-decomposition | Games tagged with fewer than 5 mechanics (warning; AGENTS.md expects 6-14). | Tag every clearly present mechanic, or record why the game is thin in design_notes. |
| W104 | maturity-dates | Mechanic maturity agrees with catalog dates: `classic` has a catalog use 20+ years before the newest game, `emerging` has none more than 10 years before it, `experimental` is used by fewer than 3 games (warning). | Change maturity to the anchor the evidence supports (take the lower one when between two), or tag the earlier games that use it. |
| W105 | source-archive | Sources with a `url` and no `archived` Wayback snapshot (warning). | Save the page at web.archive.org and record the snapshot URL in `archived`. |
| W106 | prediction-overdue | Predictions whose `resolve_by` date has passed without a `resolution` (warning). | Open a verification run and resolve it (tasks/resolve-prediction.md). |
| W107 | cluster-k-drift | The cluster selection rule clearly favours a different k: the configured `clustering.k` misses `min_mean_ari` by more than `drift_tolerance`, or a smaller k clears it by more than that (warning). Differences inside the tolerance are resampling noise. | In a maintenance run, set `clustering.k` to the rule's k, rebuild, and rewrite the report prose whose cluster assertions fail. Never pick k by what the clusters look like. |
| W108 | visual-coverage | Mechanics, mechanic families, subgenres, and technique categories that have no icon in media/visual yet (warning). | Draw the icon (media/visual/README.md) when a frame needs it; every mechanic gets one by phase 4 of ADR-0006. |
| W102 | verification-queue | Count of `asserted` entities awaiting sources (info). | Pick one from dist/analysis/verification-queue.csv and source it. |
<!-- END GENERATED: rules -->

## 6. Vocabularies

<!-- BEGIN GENERATED: vocab-index -->
| Vocabulary | Terms | Description |
|---|---:|---|
| [`actor`](vocab/actor.yaml) | 3 | Who performed a research run. |
| [`agency_model`](vocab/agency_model.yaml) | 11 | How player intent reaches the simulation. A game may use several. |
| [`agent_count_order`](vocab/agent_count_order.yaml) | 7 | Order of magnitude of individually simulated agents in typical play. Aggregate populations shown as a number but simulated as stocks count as `aggregate`. |
| [`confidence`](vocab/confidence.yaml) | 3 | Confidence in a specific claim. |
| [`determinism_impact`](vocab/determinism_impact.yaml) | 3 | Effect on reproducibility, replays, lockstep multiplayer, and save integrity when used at runtime. |
| [`edge_types`](vocab/edge_types.yaml) | 13 | Every typed relation in the graph. Each edge is stored exactly once, on the `owner` side named here. Inverses are computed by the build and never stored. Symmetric edges are stored on the entity whose id sorts first. |
| [`effect`](vocab/effect.yaml) | 7 | How a technique changes a mechanic (attribute of the technique→mechanic `affects` edge). |
| [`failure_model`](vocab/failure_model.yaml) | 5 | What happens when the system goes wrong. |
| [`feedback`](vocab/feedback.yaml) | 4 | Dominant feedback loop polarity the mechanic creates in play. |
| [`fidelity`](vocab/fidelity.yaml) | 5 | How closely the model tracks real-world causal structure. Independent of graphics. |
| [`horizon`](vocab/horizon.yaml) | 4 | Expected time until meaningful use in shipped simulation games, as judged at the entity's last review date. |
| [`math_basis`](vocab/math_basis.yaml) | 24 | Formal mathematical model a mechanic instantiates, explicitly or implicitly. Used to connect mechanics to research literature. |
| [`maturity`](vocab/maturity.yaml) | 4 | Adoption maturity of a mechanic across shipped games. |
| [`mechanic_family`](vocab/mechanic_family.yaml) | 21 | Primary functional family of a mechanic. Exactly one per mechanic. Assign by the state the mechanic owns, not by the genre it appears in. |
| [`mechanic_role`](vocab/mechanic_role.yaml) | 2 | Role a mechanic plays in a specific game (attribute of the game→mechanic `uses` edge). |
| [`modding`](vocab/modding.yaml) | 4 | Depth of player modification supported or widely practiced. `scripting` and `total-conversion` mean the game exposes a modding surface (official, or a de facto loader most modders use), so those games must tag the `modding-api` mechanic; `content` games may tag it when the content arrives through official data definitions (E033). |
| [`multiplayer`](vocab/multiplayer.yaml) | 5 | Supported social play modes. |
| [`narrative_mode`](vocab/narrative_mode.yaml) | 5 | Where story comes from. |
| [`opportunity_type`](vocab/opportunity_type.yaml) | 8 | Kind of opportunity. |
| [`perspective`](vocab/perspective.yaml) | 7 | Primary camera or presentation. |
| [`platform`](vocab/platform.yaml) | 8 | Platform families a game shipped on at any point. |
| [`player_interface`](vocab/player_interface.yaml) | 9 | How the player touches this mechanic. |
| [`player_role`](vocab/player_role.yaml) | 13 | The fiction-level role the player occupies relative to the simulation. |
| [`prediction_outcome`](vocab/prediction_outcome.yaml) | 4 | How an opportunity's falsifiable prediction resolved. Set in `falsifiable_signal.resolution` by an independent verification run (E038). |
| [`production_tier`](vocab/production_tier.yaml) | 5 | Production context at release. |
| [`risk`](vocab/risk.yaml) | 11 | Primary risks of using a technique in simulation games. |
| [`runtime`](vocab/runtime.yaml) | 5 | Where in the lifecycle the technique runs. |
| [`sim_domain`](vocab/sim_domain.yaml) | 15 | Real-world domain the simulation models. One to three per game. |
| [`sim_scale`](vocab/sim_scale.yaml) | 10 | Spatial or organizational scale of the primary simulated unit of play. |
| [`source_kind`](vocab/source_kind.yaml) | 11 | Type of cited source. |
| [`status`](vocab/status.yaml) | 4 | Epistemic status of an entity. Ordered from weakest to strongest support. Status is a claim about evidence, never about importance. |
| [`subgenre`](vocab/subgenre.yaml) | 31 | Design lineage a game belongs to. One primary per game, optional secondaries. Lineage, not marketing label. |
| [`substrate`](vocab/substrate.yaml) | 10 | Computational representation the mechanic is usually implemented on. A mechanic may have several. |
| [`technique_category`](vocab/technique_category.yaml) | 17 | Research area of a technique or breakthrough. |
| [`technique_maturity`](vocab/technique_maturity.yaml) | 4 | Deployment maturity of a technique in games specifically (not in general AI). |
| [`time_model`](vocab/time_model.yaml) | 6 | Dominant relation between simulation time and player time. `real-time-pausable` games must tag the `variable-speed` mechanic and only `real-time-pausable` and `run-on-demand` games may (E033). |
| [`win_structure`](vocab/win_structure.yaml) | 7 | How play is bounded and evaluated. |
<!-- END GENERATED: vocab-index -->

## 7. Rubric scales

<!-- BEGIN GENERATED: rubric-index -->
| Scale | Applies to | Question |
|---|---|---|
| `emergence` | game | How much of play arises from system interaction rather than authored content? |
| `influence` | game | How strongly did this game shape later simulation design? |
| `legibility` | mechanic | How easily can a typical player form an accurate mental model of the mechanic from play? |
| `emergence_potential` | mechanic | How much unscripted variety does this mechanic generate when coupled with others? |
| `authoring_cost` | mechanic | Developer cost of the content this mechanic consumes (animations, writing, assets, tuning data), per unit of player-facing variety. |
| `compute_cost` | mechanic | Runtime compute at the scale the mechanic is typically used. |
| `tuning_difficulty` | mechanic | How hard is it to balance so the mechanic is neither trivial nor degenerate? |
| `ai_leverage` | mechanic | Expert judgment of how much 2024-2026 AI techniques could change this mechanic's design ceiling (cross-checked by `affects` edges in analysis). |
| `trl` | technique | Technology Readiness Level for use in simulation games (NASA scale adapted). |
| `novelty` | opportunity | How far from shipped practice is this? |
| `feasibility` | opportunity | Can a small team (5-15) ship it within 24 months using techniques at their current maturity? |
| `impact` | opportunity | If it works, how much does it change player experience or the market? |
<!-- END GENERATED: rubric-index -->
