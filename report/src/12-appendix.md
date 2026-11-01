## Appendix A. Game catalog

{{table:game-catalog}}

## Appendix B. Technique catalog

{{table:technique-catalog}}

## Appendix C. Data availability, use, and extension

The data behind this paper and every projection of it are public. The repository at https://github.com/yoheinakajima/simgrammar holds the records (`data/`), vocabularies, schemas, calibration set, run log (`log/runs/`), the report sources, and the code that builds the paper, tables, graph, wiki, and website. Data, vocabularies, schemas, report text, and generated projections are licensed CC BY 4.0, and code Apache-2.0 (`LICENSE`). The website publishes the built projections under https://simgrammar.com/dist/, with all of them in one archive, `simgrammar-dist.zip`.

- **Version.** Cite the paper from `CITATION.cff` together with the `dataset_sha256` in `dist/manifest.json`, which is printed on this paper's title page and pins the exact data a reading used. The build is deterministic (CONTRACT.md I11), so the same inputs give byte-identical projections. A release of the paper is the commit that bumps its version, tagged `v<version>` (`decisions/ADR-0008-citable-releases.md`). Zenodo archives each release; the concept DOI 10.5281/zenodo.23846209, which `CITATION.cff` carries, resolves to the newest version.
- **Records.** Each record carries its own sources, its claims (with a verbatim quote from the first source and its location, where one has been added), its evidence status (asserted, sourced, verified, or contested), any further ratings of its scores with their rationales, and the run that created it and the runs that reviewed it. Each run in `log/runs/` names its operator, its model when an agent ran it, its purpose, and its method.
- **Checks.** `make check` validates every record against the contract, renders this paper with every number filled in from the data, and fails if any of the paper's {{stat:n_report_assertions}} assertions no longer holds; CI runs the same checks on every pull request and every push to `main`. An assertion tests that a sentence's ranking, sign, threshold, grouping, or stored field agrees with the records. It does not test the records against the games, the coding of a mechanic, or the interpretation the sentence offers (§2.5).
- **Sources.** The reference list cites only the works the prose discusses. The atlas holds {{count:source}} source records in all; each has a page on the website, linked from every record that cites it, and all are in `dist/tables/sources.csv`, `dist/entities/sources.json`, and `dist/paper/references.bib`.
- **Query** with the CSVs in `dist/tables/`, the graph files in `dist/graph/` (JSON Lines, Cytoscape, GraphML), or `make sqlite` for SQL.
- **Browse** the wiki at `dist/wiki/index.md` or the explorer at `site/index.html`.
- **Contribute** by following `AGENTS.md`: open a run, search before creating, fill entities against the schema, run `make check`. The fastest useful contribution is sourcing an entity from `dist/analysis/verification-queue.csv`.
- **Dispute** a fact by setting `status: contested` with a claim that cites the opposing source; disputes are data, not edits.

## Appendix D. Contributors

{{table:contributors}}

## Appendix E. Definitions

The derived measures, as `scripts/analyze.py` computes them, with their parameters from `vocab/rubrics.yaml` and `report/analysis.yaml`. Below, N is the number of catalog games and n(m) the number of catalog games that use mechanic m.

- **Technique exposure** of a mechanic m is E(m) = Σ w_maturity(t) × w_effect(e), summed over every `affects` edge from a technique t to m, where e is the edge's effect type. A family's exposure is the sum of E(m) over its mechanics, and its mean exposure divides that sum by the number of its mechanics (§8.2). The weights, with the effect vocabulary's definitions:

{{table:exposure-weights}}

- **AI leverage** is not computed. It is a rubric score that the rater assigns to each mechanic by matching anchor text, from "Little change expected." to "The mechanic's definition changes." (`vocab/rubrics.yaml`).
- **AI leverage gap** (§8) of a mechanic m is ai_leverage(m) / 5 − E(m) / max E, the rater's judgment and the technique graph each scaled so that the largest possible value is 1. A positive gap means the rater expects more change than the published techniques yet reach.
- **Lift** of a mechanic pair (a, b) is observed / expected, where observed is the number of catalog games that use both and expected = n(a) × n(b) / N, the number that would use both if the two were tagged independently.
- **White-space gap** of a pair is expected − observed. A pair is white space when it passes the screen of §5.5 (both mechanics common, different families, no `tension` edge, observed at most {{stat:whitespace_max_observed}}), and the white-space table ranks those pairs by gap; its rank column numbers the lots in the vacant-lots figure.
- **Weighted Jaccard similarity** of games g and h treats each game as a vector over mechanics, x_g(m) = c × log(N / n(m)) when g uses m and 0 otherwise, where c is {{stat:clustering_core_weight}} for a core use and 1 for a supporting one. Similarity is Σ min(x_g(m), x_h(m)) / Σ max(x_g(m), x_h(m)) over all mechanics, and the clustering's distance is 1 minus similarity. The logarithm is the inverse-prevalence weight: a mechanic in every game would weigh nothing, and the rarest weigh most.
- **Opportunity priority** is impact^{{stat:priority_w_impact}} × feasibility^{{stat:priority_w_feasibility}} × novelty^{{stat:priority_w_novelty}}, a weighted geometric mean of three rubric scores whose weights sum to 1.
- **Game emergence** (§3.4) is a rubric score of a whole game, distinct from a mechanic's emergence potential: the rater matches each game against anchors from "Outcomes follow authored scripts or a single equation; replays look the same." to "Emergence is the product; players report histories no one could have authored (Dwarf Fortress tier)." §3.4 lists games by that score, then by influence, then by name.
- **Relation degree** of a mechanic (§1) is the number of `requires`, `specializes`, `synergy`, and `tension` edges that touch it, and relation density is the share of possible mechanic pairs joined by at least one of them.
