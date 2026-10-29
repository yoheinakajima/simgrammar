# SimGrammar

An open, machine-readable atlas of simulation game mechanics: which games use which rule-systems, how each mechanic works and fails, which math/AI/ML/LLM results change what those mechanics can be, and where the design opportunities are.

The repository is the research. The report, wiki, tables, graph, and site are projections of the same YAML files, rebuilt and checked on every commit, so they cannot disagree with each other.

Live counts, downloads, and the research log: **[sim.yohei.me/data](https://sim.yohei.me/data/)**.

## Read it

| You want | Open |
|---|---|
| The website: paper with interactive figures, a page per record | **[sim.yohei.me](https://sim.yohei.me/)** |
| The report (paper form) | [paper.md](https://sim.yohei.me/dist/paper/paper.md) · BibTeX: [references.bib](https://sim.yohei.me/dist/paper/references.bib) |
| Every projection in one download | [simgrammar-dist.zip](https://sim.yohei.me/dist/simgrammar-dist.zip): tables, full records, graph, analysis, wiki, paper, manifest |
| Tables | [games.csv](https://sim.yohei.me/dist/tables/games.csv), [mechanics.csv](https://sim.yohei.me/dist/tables/mechanics.csv), [edges.csv](https://sim.yohei.me/dist/tables/edges.csv), and the rest on the [data page](https://sim.yohei.me/data/) |
| A graph | [nodes.jsonl](https://sim.yohei.me/dist/graph/nodes.jsonl), [edges.jsonl](https://sim.yohei.me/dist/graph/edges.jsonl), Cytoscape JSON, GraphML for Gephi |
| The data behind any page | `data/` (one YAML file per record) and `log/runs/` (who added what, how) |
| Integrity certificate | [manifest.json](https://sim.yohei.me/dist/manifest.json): per-record and dataset SHA-256 |

`dist/` is not committed. `make build` writes it locally (it also feeds the old explorer at `site/index.html`, served from the repository root, and `make sqlite`). CI builds it on every push, checks the build is deterministic, and publishes it with the site.

## Contribute

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the briefs in [`tasks/`](tasks/). Open issues labeled `task` are ready to claim.

```bash
pip install -r requirements.txt
make hooks       # optional pre-commit check
make check       # validate every rule, the report and record assertions, and the GENERATED blocks
```

1. Read [`CONTRACT.md`](CONTRACT.md) (invariants and enforced rules) and [`AGENTS.md`](AGENTS.md) (procedure; written for AI agents, works for humans).
2. Claim an issue, then open a run of the kind its brief names: `python scripts/new.py run <slug> --kind catalog --actor human --operator <you> --purpose "..."`.
3. Search first: `python scripts/find.py "<concept>"`.
4. Scaffold what your run kind may create, for example `python scripts/new.py game <id> --run <run-id>` in a catalog run. Mechanics are created only in taxonomy runs; elsewhere, record a `new-mechanic` proposal (`tasks/propose-mechanic.md`).
5. `make build && make check`, commit with `git commit -s`, and open a PR that links the issue. A PR carries one run and at most 10 records.

High-value first contributions: verbatim quotes for existing claims (`tasks/source-claims.md`), Wayback snapshots for sources (`tasks/archive-sources.md`), store ids for games (`tasks/store-ids.md`), and independent, calibrated ratings of mechanic scores (`tasks/rate-scores.md`). The [verification queue](https://sim.yohei.me/dist/analysis/verification-queue.csv) lists records still waiting for sources.

### Contributors

Built from the run log: you appear here when your first pull request merges. What each person's runs created and verified is in [appendix D of the paper](https://sim.yohei.me/#appendix-d-contributors). To be credited by name rather than handle, add yourself to `contributors` in [`report/meta.yaml`](report/meta.yaml).

<!-- BEGIN GENERATED: contributors -->
| contributor | github | first run |
|---|---|---|
| Yohei Nakajima | [yoheinakajima](https://github.com/yoheinakajima) | 2026-10-23 |
| Pedro Lucca | [heypedrolucca](https://github.com/heypedrolucca) | 2026-10-28 |
| ShreyKo | [shreyko-antim](https://github.com/shreyko-antim) | 2026-10-29 |
<!-- END GENERATED: contributors -->

## Layout

```
CONTRACT.md      invariants, change classes, generated rule table
AGENTS.md        step-by-step procedure for agents and humans
CONTRIBUTING.md  how to get work, review, licensing of contributions
tasks/           briefs for bounded contributor jobs
schema/          JSON Schemas (closed) + registry.yaml (types, dirs, contract version and history, PR limits)
vocab/           closed vocabularies, edge types, anchored rubrics
data/            canonical entities, one YAML file each
log/runs/        append-only provenance records
calibration/     frozen calibration set for rubric raters
decisions/       ADRs for vocab, rubric, schema, and rule changes
report/src/      report prose with {{tokens}}, [[links]], [@citations]
report/          tables.yaml (declarative table views), analysis.yaml (analysis parameters), meta.yaml
scripts/         validate.py, build.py, analyze.py, new.py, find.py, calibrate.py, check_sources.py, pr_scope.py
dist/            generated projections (gitignored; built by CI and published with the site)
site/            static explorer over dist/site/data.json
web/             website assets: register.css (vendored, see web/DESIGN.md) and simgrammar.js
```

## Design lineage

Two ideas carried over from earlier projects:

- **The log is the source; views are projections** (ActiveGraph). Canonical facts live in small typed records with provenance; every table, graph, and paper is a replayable projection, and the build is deterministic so drift is a diff.
- **Provenance-first knowledge with explicit epistemic status** (Epistemedia). Every entity carries `asserted / sourced / verified / contested`, verification requires an independent run, and the manifest's hashes let anyone certify which dataset version a claim came from.

## License

Code: Apache-2.0. Data, vocabularies, and report text: CC BY 4.0. See [`LICENSE`](LICENSE).
