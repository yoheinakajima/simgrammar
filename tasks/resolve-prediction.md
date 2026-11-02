# Brief: resolve a falsifiable prediction

**Run kind:** `verification`. **Limit:** 3 opportunities per PR.

**Who can take it:** an invited contributor (the repository's owner, a member, or a collaborator) whose operator is not the opportunity's creator. CI counts a `verification` run only from an invited author (E039), because independence (E035) rests on who the operator is. Not invited? Open a [Verification request](https://github.com/yoheinakajima/simgrammar/issues/new?template=verification.yml) to ask for an invitation, or for the check.

Every opportunity carries a prediction with a `resolve_by` date and criteria. `W106` lists predictions whose date has passed without a resolution. Resolving one early is fine once every criterion is met.

1. Read the `criteria` literally. Features count only if first shipped after 2026-10-24 (ADR-0003); review thresholds are Steam user review counts on the resolve date.
2. Read the prediction's entry in `report/predictions.yaml`, written before any prediction resolved: its reference class (whom to count), its generic-diffusion version (what the same event looks like without the opportunity's mechanism), and what counts for the thesis. The entry does not change the outcome, which the criteria alone decide; it says what a confirmation shows. Do not edit the entry in the same PR; if it is wrong, say so in your run's `proposals`.
3. Find the evidence: a developer page, patch notes, store page, or study. Create source records for it.
4. Add to `falsifiable_signal`:
   ```yaml
   resolution:
     outcome: confirmed        # confirmed | refuted | ambiguous | withdrawn (vocab/prediction_outcome.yaml)
     date: '2027-03-01'        # the day you checked
     run: <your-run-id>
     evidence: [src-...]       # required unless withdrawn
     note: Which title met which criterion, or which criterion failed, and how you checked.
   ```
5. Append your run to the opportunity's `provenance.reviewed` (E039). `refuted` is only for after the resolve-by date and `withdrawn` only for before it (E038).
6. Your run must be independent of the run that created the opportunity (E035). In the note, count the entry's reference class on the day you check: how many of its titles (or studios, vendors, or cities) first shipped the feature in the window, and, for titles on Steam, how many of those disclose generative AI in the Steam content survey, which is the generic-diffusion rate on that day. A refuted prediction shows the bet did not arrive by its date: say whether that counts against the thesis or only its timing (cost, schedules, reception). For a confirmed one, say whether the evidence shows what the entry's thesis field names; if not, write that the confirmation is generic diffusion. Say also whether the prediction was a technique test or a feature test. Do not edit the thesis in the same PR.
