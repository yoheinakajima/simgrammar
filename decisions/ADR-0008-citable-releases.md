# ADR-0008: Citable releases

- Status: accepted
- Date: 2026-10-31
- Contract version: 1.2. E023's text and invariant I1 now name `CITATION.cff`; no schema, vocabulary, or data rule changes.
- Run: `2026-10-31-citable-release`

## Context

An outside review on 2026-10-31 found the paper hard to cite. Its title page said version 0.2 of 2026-10-25 although the dataset had changed since. The repository had no `CITATION.cff`, no tagged release, and no DOI. The paper existed only as markdown and HTML, and arXiv's computer science section now accepts review articles and position papers only after peer review, so a submission would have to be framed as a dataset and method paper, uploaded as TeX source.

The dataset already carries a precise identity: the build stamps `dataset_sha256` (from `dist/manifest.json`) into the paper's front matter, the paper page, its BibTeX entry, and every book chapter. What was missing was a version a citation manager, an archive, or a preprint server can read.

## Decision

1. **The paper's version and date live in `report/meta.yaml`** and are bumped for a release. A release is the commit that bumps them, tagged `v<version>`. The dataset hash, not the version, pins the data: the version names a paper, and many datasets can pass under one version between releases.
2. **The build writes `CITATION.cff`** (Citation File Format 1.2.0) at the repository root, from `report/meta.yaml` and the byline the paper uses. It is committed and checked like a GENERATED block (E023), so it cannot drift from the paper. It holds nothing that moves with the data (no hash, no counts), so data pull requests never touch it, and its `message` asks citers to add the dataset hash. Its `license` is CC-BY-4.0, the license of the data and report text; `LICENSE` keeps code under Apache-2.0.
3. **Two optional fields feed it.** `doi` in `report/meta.yaml`, once Zenodo mints a concept DOI, goes into `CITATION.cff` and the paper's BibTeX entry. `orcid` joins the contributor profile links (an https link to orcid.org), and `CITATION.cff` lists it for the byline.
4. **A PDF is an optional local build.** `make pdf` runs `scripts/paper_pdf.py`, which turns `dist/paper/paper.md` into LaTeX and each figure SVG into TikZ, then compiles with tectonic, a self-contained XeTeX engine, in its deterministic mode with `SOURCE_DATE_EPOCH` set to the paper's date. One tectonic version gives a byte-identical PDF. Output goes to `pdf-out/` (gitignored), outside `dist/`, which `make build` prunes. `make check` and CI do not depend on it, because tectonic fetches its TeX bundle over the network on first use and the build forbids network calls (I11). The LaTeX source is the arXiv upload; arXiv now compiles XeLaTeX.
5. **The release and the DOI are the operator's steps.** No workflow tags, releases, or uploads anything.

## Consequences

- Changing `report/meta.yaml`'s title, version, date, site links, or `doi`, or a byline contributor's profile, changes `CITATION.cff`; `make build` rewrites it and `make check` fails until it is committed.
- The figure translator accepts the SVG subset `scripts/viz.py` and `scripts/analyze.py` write (rect, line, circle, polyline, polygon, path with M, L, H, V, C, S, Q, Z, text with colour tspans, g with translate, rotate, and scale). A figure that draws anything else stops `make pdf` with the element named, rather than printing a wrong picture.
- arXiv still needs the paper reframed. Its CS moderators reject review and position papers that have not passed peer review, and the abstract, opportunities, and predictions read partly as both. A submission would lead with the dataset, the schema, and the checking method (contract, assertions, deterministic projections) and present the findings as results of that method.
