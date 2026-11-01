# Episode 11. Keeping score

Target runtime about 11 minutes: about 1,180 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 12. Footage: screen recordings of the dataset's prediction records, its predictions table, and its resolution brief; store pages and patch notes appear as generic mock-ups with no real title shown. No game footage. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** Every bet in the series comes with a dated prediction that can lose. Here is how the predictions were written, when they come due, and who is allowed to check them. Once results arrive, the scoreboard also tests whether the rankings behind the bets meant anything.

## 1. Cold open (0:00 to 0:38)

**Picture.** A wall calendar flips to {{stat:first_prediction_resolves_long}}. Index cards pin themselves to the date, one by one. The camera stops on the first card and reads it.

**Frame.** timeline kind=due date=2027-12-31 current=causal-why-query

**Voice.** On {{stat:first_prediction_resolves_spoken}}, {{stat:n_predictions_first_date}} predictions about AI in simulation games come due on the same day.{{assert:n_predictions_first_date >= 5}} The first says that a widely played simulation or strategy game will let you ask, in plain language, why something happened in your own game, and answer from your save. Somebody is going to have to check.

## 2. Title (0:38 to 0:48)

**Picture.** Title card over the predictions table, out of focus.

**On screen.** Keeping score. Episode 11.

## 3. Reading it literally (0:48 to 2:07)

**Picture.** The prediction's record on screen. Its criteria highlight one clause at a time.

**Frame.** record bet=causal-why-query fields=falsifiable_signal

**Voice.** The sentence on the card is the headline. The criteria underneath are what count, and they're narrower. The feature has to have first shipped after the 24th of October 2026, so a game that already had it doesn't count. The game needs at least ten thousand Steam reviews, counted on the resolve date, so a game that crosses the line a month late doesn't count. And the patch notes or store page have to describe free-text questions about causes, answered from the player's own save.{{assert:field.causal-why-query.falsifiable_signal.resolve_by == first_prediction_resolves}}

**Picture.** Mock-up: a generic strategy game's patch notes, "New: ask the Advisor anything". The checker clicks through to the details: answers come from the game's manual.

**Frame.** mockup kind=ui title="Patch notes" lines="New: ask the Advisor anything|Answers come from the game's manual"

**Voice.** Say you find a strategy game that added an advisor you can type to. You read the details: it answers questions about the rules, from the manual. That fails the last clause, because nothing comes from your save. If nothing else qualifies by the date, the prediction is refuted, and the top-ranked bet in the dataset takes the loss.

## 4. Bets that can lose (2:07 to 3:26)

**Picture.** An early draft of a prediction, from the project's history, with three words circled: "major", "popular", "peer studio".

**Frame.** mockup kind=doc title="An early draft of a prediction" lines="Ships in a game from “a major studio”|Reaches “a popular game”|Copied by “a peer studio”"

**Frame.** record at="The fix set three rules for every prediction" title="Three rules for every prediction" lines="A feature counts only if it first shipped after the dataset was published|Size is a stated number of Steam reviews, or a console release|The evidence comes from the developer: patch notes, a store page, documentation, a talk" numbered

**Voice.** A bet with no date can't lose, so every bet in the dataset carries one. They weren't always this strict. When an outside reviewer read the first version, the predictions said things like "a major studio" or "a popular game", leaned on store rankings, and had no start date, so a feature that already existed could have settled them. One was already true on the day it was written. The fix, and the reasons for it, are written down in the project's decision records, where anyone can read why the rules are what they are.

**Voice.** The fix set three rules for every prediction. A feature only counts if it first shipped after the dataset was published. Size is a stated number of Steam reviews, or a console release. And the evidence has to come from the developer: patch notes, a store page, documentation, a talk.

## 5. Two tests per bet (3:26 to 4:34)

**Picture.** One opportunity record, split down the middle: on the left its validation experiment, on the right its prediction.

**Frame.** record bet=causal-why-query fields=validation_experiment,falsifiable_signal

**Voice.** Each bet in the dataset carries two tests. The experiment tests the idea: what a small team would build, who would play it, and the number that counts as success. For the why button, that's a correct diagnosis forty percent faster with nearly every sentence backed by the log. Anyone with a build can run it.

**Voice.** The prediction tests the world: whether anyone ships the thing by a date. An idea can pass the experiment and still lose the prediction, because studios didn't build it in time. It can also win the prediction with a design the experiment would have rejected. The record keeps both, so a reader can tell which kind of wrong a bet turned out to be.

## 6. The calendar (4:34 to 5:40)

**Picture.** The predictions table scrolls, grouped by year. A bar under each year grows to its count.

**Frame.** timeline kind=due-years

**On screen.** Due by the end of 2027: {{stat:n_predictions_by_2027}}. By the end of 2028: {{stat:n_predictions_by_2028}}. Last: {{stat:last_prediction_resolves_long}}.

**Voice.** All {{stat:n_predictions}} are open right now.{{assert:n_predictions_open == n_predictions}} {{stat:n_predictions_by_2027}} come due by the end of 2027, {{stat:n_predictions_by_2028}} by the end of 2028, and the last on {{stat:last_prediction_resolves_spoken}}.{{assert:n_predictions_by_2027 < n_predictions_by_2028}} The {{stat:n_predictions_first_date}} due first cover the why button, events generated against a schema, endless inspection shifts for a Papers, Please-style game, furniture generated from text, run histories written up automatically, local language models, automated balancing, a voice instructor in a flight or racing sim, and simulation games released as test beds for AI agents. Most of the early dates belong to bets rated buildable now. The late ones are the long shots from episode 9: a game drawn by a generative model, a mechanic invented by a search program.

## 7. Four more cards (5:40 to 7:07)

**Picture.** Four prediction cards in a grid. Each one's limiting clause highlights as the narration reaches it.

**Frame.** record bets=local-first-ai-sims,sim-instructor-coach,generative-decoration-catalogs,parallel-autobalance

**Voice.** The other cards due that day show what checking involves. One counts games: at least five, each with over a thousand reviews, using a language model that runs on your own machine with no internet connection.{{assert:field.local-first-ai-sims.falsifiable_signal.resolve_by == first_prediction_resolves}} Each one needs two facts checked, the date and the offline part.

**Voice.** One excludes things. An AI voice instructor in a flight or racing sim counts only if the developer ships it; third-party apps don't count, however good they are, and the sim needs at least five thousand reviews or a console release.{{assert:field.sim-instructor-coach.falsifiable_signal.resolve_by == first_prediction_resolves}}

**Voice.** One excludes a specific game. Generated furniture and scenery from text has to show up in a life or management sim other than inZOI, because inZOI did it before the window opened.{{assert:field.generative-decoration-catalogs.falsifiable_signal.resolve_by == first_prediction_resolves}}

**Voice.** And one counts studios: two different studios have to describe in public using large-scale automated play to balance a game's economy.{{assert:field.parallel-autobalance.falsifiable_signal.resolve_by == first_prediction_resolves}} That one can fail because a studio does it and never says so, and the record will still say refuted.

## 8. Who is allowed to check (7:07 to 8:59)

**Picture.** The resolution brief on screen. Then a resolution block being added to a prediction's record: outcome, date, run, evidence, note.

**Frame.** record title="A resolution" lines="Outcome: confirmed, refuted, ambiguous, or withdrawn|Date|Run|Evidence, each page added as a source|Note: which game met which clause"

**Voice.** Resolving a prediction is a change to the dataset, like any other. The checker finds the evidence and adds each page that settles it as a source in the dataset, so anyone can open the patch note or store page that decided the bet. Then comes the resolution: confirmed, refuted, ambiguous, or withdrawn, with the date, the evidence, and a note saying which game met which clause.

**Voice.** The build enforces the timing. You can't call a bet refuted before its date, and you can't withdraw it after. And the checker has to be someone else. Every prediction was written by one agent, running one model, working for the dataset's maintainer. So a resolution has to come from a different person and, if an agent does the work, a different model. Whoever made the bet doesn't get to settle it, and neither does another copy of the model that wrote it.

**Voice.** A refuted prediction says the bet didn't arrive by its date. That can mean the argument was wrong, or only that cost, schedules, or reception got in the way, and the resolver records which. The rules ask that nobody rewrite the argument in the same change that records the loss, so the losing case stays readable next to the evidence.

**Voice.** Every time the dataset is built, a warning lists each prediction whose date has passed without a resolution, and it keeps appearing until someone checks. <!-- tells-ok: setup-sentence -->

## 9. What the scoreboard tests (8:59 to 9:57)

**Picture.** The ranked table of bets, with an empty column labelled "outcome" beside it. Then the technique table, its maturity column highlighted: research, prototype, shipped in a niche, shipped as a norm.

**Frame.** count kind=ranked of=opportunity n=6

**Frame.** count at="It also tests the dataset's maturity scores" kind=tally of=technique field=maturity

**Voice.** Once results come in, the scoreboard also tests the rankings. If the scores behind the table mean anything, confirmations should gather near the top. A run of refutations among the explanation bets would mean this series was wrong about what studios would build, even if it was right about what players need.

**Voice.** It also tests the dataset's maturity scores. Every technique is rated research, prototype, shipped in a niche, or shipped as a norm. If a bet that depends on a research-stage technique comes true on time, that's evidence the scale was running behind the field.

## 10. Try one (9:57 to 10:49)

**Picture.** A blank card with four numbered lines, filling in as the narration goes.

**Frame.** record title="Try one" lines="Turn every clause into a yes-or-no question|Search for each answer, and write down where you found it|Decide the outcome as if the date were today|Write the two-sentence note" numbered

**Voice.** You can do this yourself today. Pick a prediction that's more than a year out. Turn every clause into a yes-or-no question. Search for each answer, and write down where you found it. Decide what the outcome would be if the date were today. Then write the two-sentence note you'd attach, so that someone who never saw your search could check it. Most people find a clause the criteria leave open, and that's worth a proposal to sharpen the prediction before it comes due.

## 11. Close (10:49 to 11:25)

**Picture.** The calendar from the cold open, the cards still pinned to {{stat:first_prediction_resolves_long}}.

**Frame.** timeline kind=due date=2027-12-31

**Voice.** Every number in this episode is computed from the dataset, so a version built after the first results will say something different. The last episode shows how that works, and why the sentence saying every prediction is still open will break the build the day one isn't.

**On screen.** Every prediction and its criteria: simgrammar.com
