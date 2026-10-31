## Appendix A. Game catalog

{{table:game-catalog}}

## Appendix B. Technique catalog

{{table:technique-catalog}}

## Appendix C. Data availability, use, and extension

The data behind this paper and every projection of it are public. The repository at https://github.com/yoheinakajima/simgrammar holds the records (`data/`), vocabularies, schemas, calibration set, run log (`log/runs/`), the report sources, and the code that builds the paper, tables, graph, wiki, and website. Data, vocabularies, schemas, report text, and generated projections are licensed CC BY 4.0, and code Apache-2.0 (`LICENSE`). The website publishes the built projections under https://simgrammar.com/dist/, with all of them in one archive, `simgrammar-dist.zip`.

- **Version.** Cite the paper from `CITATION.cff` together with the `dataset_sha256` in `dist/manifest.json`, which is printed on this paper's title page and pins the exact data a reading used. The build is deterministic (CONTRACT.md I11), so the same inputs give byte-identical projections. A release of the paper is the commit that bumps its version, tagged `v<version>` (`decisions/ADR-0008-citable-releases.md`). Zenodo archives each release; the concept DOI 10.5281/zenodo.23846209, which `CITATION.cff` carries, resolves to the newest version.
- **Records.** Each record carries its own sources, its claims (with a verbatim quote from the first source and its location, where one has been added), its evidence status (asserted, sourced, verified, or contested), any further ratings of its scores with their rationales, and the run that created it and the runs that reviewed it. Each run in `log/runs/` names its operator, its model when an agent ran it, its purpose, and its method.
- **Checks.** `make check` validates every record against the contract, renders this paper, and fails if any assertion attached to an interpretive sentence no longer holds; CI runs the same checks on every pull request and every push to `main`.
- **Sources.** The reference list cites only the works the prose discusses. The atlas holds {{count:source}} source records in all; each has a page on the website, linked from every record that cites it, and all are in `dist/tables/sources.csv`, `dist/entities/sources.json`, and `dist/paper/references.bib`.
- **Query** with the CSVs in `dist/tables/`, the graph files in `dist/graph/` (JSON Lines, Cytoscape, GraphML), or `make sqlite` for SQL.
- **Browse** the wiki at `dist/wiki/index.md` or the explorer at `site/index.html`.
- **Contribute** by following `AGENTS.md`: open a run, search before creating, fill entities against the schema, run `make check`. The fastest useful contribution is sourcing an entity from `dist/analysis/verification-queue.csv`.
- **Dispute** a fact by setting `status: contested` with a claim that cites the opposing source; disputes are data, not edits.

## Appendix D. Contributors

{{table:contributors}}
