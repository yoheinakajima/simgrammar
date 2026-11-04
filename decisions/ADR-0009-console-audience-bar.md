# ADR-0009: An audience bar for console clauses, and longer prediction criteria

- Status: accepted
- Date: 2026-11-03
- Contract version: 1.3. The opportunity schema's `falsifiable_signal.criteria` may hold up to 600 characters, up from 500. No rule, vocabulary, or rubric changes.
- Run: `2026-11-03-console-audience-bar`

## Context

Ten prediction criteria let "a console release" stand in for a Steam review count (1,000 reviews in eight, 5,000 in two). The clause set no audience size, so a minor console title could meet a criterion the review bar was meant to close. The paper listed amending these clauses as open work (§11.1, item 7). Four of the ten criteria are within 30 characters of the schema's 500-character limit, so the added condition does not fit without rewording other parts of the criteria. Rewording the outcome conditions or the technique-class sentence would change more than an amendment may.

## Decision

1. **Each console clause gains an audience size.** A console release now counts when a public source reports copies sold or players of at least 20 times the review bar: 20,000 for a 1,000-review bar, and 100,000 for a 5,000-review bar. Twenty is the low end of the 20 to 50 sales per review that a 2023 review of the Boxleiter method reports (`src-gwinnell-2023-steam-benchmarks`), so the console bar is no harder to meet than the review bar it stands in for.
2. **The change only adds a condition.** The text goes directly after "console release", so a title that meets the new criteria met the old ones. No prediction has resolved, so no outcome moves. `report/predictions.yaml` records each change as `audience_bar` (date and added text), and the build fails if the added text is not in the criteria.
3. **Criteria may run to 600 characters.** This is a non-breaking schema change, so it is a minor contract bump.

## Consequences

- `scripts/analyze.py` counts the bars, their date, the predictions resolved by then, and the console clauses still without a bar. The paper asserts that last count is zero.
- Runs from this date record contract version 1.3. Earlier runs keep 1.2 (E028).
