# Tasks: briefs for contributors, human or agent

Invited contributors who work through an agent: start with [humans-with-agents.md](humans-with-agents.md).

Each brief is a self-contained job. It says which run kind to open, what to read, what to change, and what CI will check. A brief plus `AGENTS.md` is everything an agent needs; nothing here overrides `CONTRACT.md`.

## How work is claimed

1. Pick an open issue labeled `task` (or open one with the **Task** form). It names a brief and the records it covers: at most 10 records, or up to 30 sources for `archive-sources` (sources count separately).
2. Comment `claiming` on the issue. One issue, one claimant, one run, one pull request. Issues never overlap: the generator (`make tasks`, run by the `tasks` workflow) skips records already in a task issue for that brief and files that open pull requests touch. If you stop, comment so; a maintainer unassigns or closes the issue, and closing it keeps its records out of new issues until it is reopened.
3. Open the run with the kind the brief names: `python scripts/new.py run <slug> --kind <kind> --actor agent --operator <your-github-handle> --model <model-id> --harness "<tool>" --purpose "<one sentence>"`.
4. Do the work, then `make build && make check`. Commit as `<type>(<scope>): <what> [run:<run-id>]` and open a PR that links the issue.
5. CI checks the rules (`make check`), determinism, the PR's scope (E039: at most 10 records and 30 sources, exactly one new run file, every changed record names that run), and, for changed records, every claim quote and store id against the live web (`sources` workflow).

The operator is the accountable human. An agent never verifies, rates, or resolves work created by a run with the same operator, or with the same model when both are agents (E035). CI counts verification runs only from invited contributors: the owner, members, and collaborators (E039).

## Briefs

| Brief | Run kind | Typical size |
|---|---|---|
| [catalog-game.md](catalog-game.md): add or complete games | `catalog` | 3 to 10 games |
| [source-claims.md](source-claims.md): add verbatim quotes to claims | `maintenance` or `catalog` | 10 records |
| [archive-sources.md](archive-sources.md): add Wayback snapshots to sources | `maintenance` | 30 sources |
| [store-ids.md](store-ids.md): add Steam, IGDB, Wikidata ids to games | `catalog` | 10 games |
| [verify-record.md](verify-record.md): check a sourced record and mark it verified | `verification` | 5 to 10 records |
| [rate-scores.md](rate-scores.md): calibrate, then add independent ratings | `verification` | 10 mechanics |
| [resolve-prediction.md](resolve-prediction.md): resolve a falsifiable prediction | `verification` | 1 to 3 opportunities |
| [second-coding.md](second-coding.md): code families, admission tests, and effect types a second time | `verification` | one sample, no records changed |
| [propose-mechanic.md](propose-mechanic.md): propose a missing mechanic | any (a proposal) | 1 proposal |

Taxonomy work (creating mechanics), synthesis (opportunities, report prose), and anything under `vocab/`, `schema/`, `scripts/`, `calibration/`, or `report/` is maintainer-reviewed (`.github/CODEOWNERS`). Propose it; do not do it in a task PR. The one exception is the codes file a second-coding task adds under `report/coding/` (`tasks/second-coding.md`).
