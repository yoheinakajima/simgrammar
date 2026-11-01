# Chapter 12. Keeping score

On {{stat:first_prediction_resolves_long}}, {{stat:n_predictions_first_date}} of the dataset's predictions come due.{{assert:n_predictions_first_date >= 5}} One of them belongs to the top-ranked bet from chapter 10, the why-query. It reads, in full: a widely played simulation or strategy game will let players ask in natural language why something happened in their own game and answer from game state.

Suppose you are the person who checks it. The prediction's criteria tell you exactly what to look for, and they are narrower than the sentence. The feature must have first shipped after 24 October 2026, so a game that already had one before the dataset was published does not count. The title must have at least 10,000 Steam user reviews, counted on the resolve date. And the release notes or the store page must describe free-text causal questions answered from the player's own save state, which rules out a chatbot that answers from a wiki or general help text.{{assert:field.causal-why-query.falsifiable_signal.resolve_by == first_prediction_resolves}}

You search patch notes and store pages for the year. You find, say, a strategy game that added an advisor you can type questions to. You open its patch notes: the advisor answers questions about game mechanics from the developer's documentation. That fails the last criterion, because the answers do not come from the player's save. You keep looking. If nothing qualifies, the outcome is `refuted`, and the thesis behind the top-ranked bet in the dataset takes a mark against it.

## A bet that can lose

An opportunity without a date cannot be wrong. "AI will make simulation games more legible" will look plausible in any year, whatever happens. Every opportunity in the dataset therefore carries a falsifiable signal: a one-sentence prediction, a resolve-by date, and criteria written so that a stranger with a browser could decide the outcome from public evidence.

The criteria were not always that strict. When an independent reviewer read the first version of the dataset, the predictions used words like "major", "popular", and "peer studio", relied on store rankings, and had no start date, so a feature that already existed could resolve them; one prediction was already true on the day it was written. The fix, recorded in the project's third decision record, set three rules that every prediction now follows. A feature counts only if it first shipped after 24 October 2026. Size is a stated number of Steam user reviews, or a console release. And the evidence must be developer material: patch notes, a store page, documentation, a talk.

All {{stat:n_predictions}} predictions are open today.{{assert:n_predictions_open == n_predictions}} The table lists them by date.

{{table:predictions}}

They come due over four years: {{stat:n_predictions_by_2027}} resolve by the end of 2027, {{stat:n_predictions_by_2028}} by the end of 2028, and the last on {{stat:last_prediction_resolves_long}}.{{assert:n_predictions_by_2027 < n_predictions_by_2028}}{{assert:last_prediction_resolves == 2030-12-31}} Most of the early dates belong to bets the dataset rates as buildable now. The late ones belong to the long shots of chapter 10, such as a game rendered by a generative model from a symbolic state, or a mechanic credited to automated discovery.

{{viz:prediction-timeline}}

## Reading criteria literally

Most of the work of resolving a prediction is reading its criteria without adding anything to them. Four of the predictions due on {{stat:first_prediction_resolves_long}} show the kinds of judgment involved.

The local-first prediction counts titles. It resolves `confirmed` if at least five games with more than 1,000 Steam user reviews use an on-device language model at runtime without needing an internet connection, each one's local-model feature first shipped after 24 October 2026, with store pages or documentation confirming that the inference runs locally.{{assert:field.local-first-ai-sims.falsifiable_signal.resolve_by == first_prediction_resolves}} The checker has to establish two facts per title, the date and the offline operation, and a game that falls back to a server when one is available is a judgment call that has to be explained in the resolution's note.

The simulator-instructor prediction excludes things explicitly. It needs a flight or racing simulator with at least 5,000 Steam user reviews or a console release to ship an official AI voice instructor that speaks generated feedback based on the player's live inputs. Third-party apps do not count, however good they are.{{assert:field.sim-instructor-coach.falsifiable_signal.resolve_by == first_prediction_resolves}}

The decoration-catalog prediction excludes a specific game. It asks for a life or management sim other than [[inzoi|inZOI]] to let players generate new placeable 3D objects from text or images inside the game, because inZOI already did so before the window opened.{{assert:field.generative-decoration-catalogs.falsifiable_signal.resolve_by == first_prediction_resolves}}

The autobalance prediction counts studios. It needs talks, technical blogs, or papers from staff of two different studios, each naming a commercial title with at least 1,000 Steam user reviews and describing automated agent play at scale used to balance its economy.{{assert:field.parallel-autobalance.falsifiable_signal.resolve_by == first_prediction_resolves}} This one can fail because a studio uses the practice without describing it in public. The resolution would record that as `refuted` all the same, and the note would say what was searched.

## What counts as evidence

Nearly every prediction names the evidence that can settle it, and some go beyond the developer material listed above. Several, the drama-aware storyteller among them, also accept a technical talk. The content-elastic events bet accepts Steam's AI disclosure, the content survey of chapter 7, as well as developer documentation. The salience-gated agents bet accepts behaviour that modders have verified, alongside documentation and postmortems. The benchmark bet requires an official announcement or repository from the developer or publisher. The planning-sandbox bet needs a public planning document or press release that names the tool, says that it simulates residents' responses, and records its use in an official consultation.{{assert:field.participatory-planning-sandboxes.falsifiable_signal.resolve_by == 2029-12-31}}

The size bar varies too. Most predictions ask for 1,000 Steam user reviews. Besides the why-query, the language-modding bet asks for 10,000, and its developer must also offer an official modding interface; negotiating faction AI joins the decoration catalog and the instructor at 5,000. A console release can stand in for the review count in {{stat:n_predictions_console_alternative}} predictions.{{assert:n_predictions_console_alternative >= 5}} The recipe-graph bet accepts a mod with at least 10,000 downloads on its official portal, and the legislation bet says that early access counts. Every review count is taken on the resolve date, which is hardest on bets about new titles such as the living workforce and the society terrarium: a game released late in the window has less time to reach the bar.

## What does not count

Exclusions appear in {{stat:n_predictions_exclusion_clause}} predictions, each naming something that does not count.{{assert:n_predictions_exclusion_clause >= 5}} The branch preview does not count a single deterministic projection, the kind of forecast games already show. The dream-replay bet does not count pre-rendered cutscenes. The trainable-creatures bet does not count single-layer learners such as the perceptrons of [[black-and-white|Black & White]], so a new game that reuses that 2001 design cannot settle it.{{assert:field.black-and-white.year == 2001}} The storyteller bet does not count generated event text alone, because the bet is about a model ranking authored events against the story state. The delegation bet does not count fixed presets or global difficulty settings. The market bet does not count vendors with fixed prices, and the benchmark bet does not count community wrappers or academic forks. Others draw the line inside the sentence; for example, learned build assist needs a model trained on layout data, as opposed to procedural rules written by hand, and learned material surrogates need a trained model that computes physical behaviour during play, which a purely visual effect does not.

## Who may resolve one

A prediction is resolved by a pull request, like any other change to the dataset. The procedure is a short brief in the repository. The resolver reads the criteria, finds the evidence, creates source records for it, and adds a resolution to the prediction: an outcome, the date it was checked, the run that checked it, the sources, and a note saying which title met which criterion or which criterion failed.

In the record, a resolution is a few lines of data:

```yaml
resolution:
  outcome: confirmed        # confirmed | refuted | ambiguous | withdrawn
  date: '2028-01-04'        # the day it was checked
  run: 2028-01-04-resolve-why-query
  evidence: [src-...]       # required unless withdrawn
  note: Which title met which criterion, and how it was checked.
```

The outcomes come from a closed list: `confirmed`, `refuted`, `ambiguous`, or `withdrawn`. The validator enforces when each may be used. A prediction can be `refuted` only after its resolve-by date has passed, so nobody can declare a bet lost early. It can be `withdrawn` only before the date, so nobody can withdraw a bet after seeing that it lost. Every outcome except a withdrawal must cite evidence. A prediction that passes its date with no resolution is listed by a warning every time the dataset is built.

The resolver also has to be someone else. All {{stat:n_predictions}} predictions were written in a single synthesis run by an agent running one model under the dataset's maintainer, and the independence rule says a resolution must come from a run with a different operator and, when both runs are agents, a different model. The person who made the bet cannot settle it, and neither can another copy of the model that wrote it. The rule is the same one that governs verifying records and rating scores, and chapter 13 explains how the build checks it.

The brief limits how much one change may decide. A run that resolves predictions is a verification run, and one pull request may resolve at most three. The resolution is dated the day it was checked, and the validator rejects a date before 24 October 2026 or after the day it runs. The resolving run is added to the opportunity's list of reviewing runs, and the pull-request check confirms no earlier entry is dropped. A prediction may be resolved early once every criterion is met.

A refuted prediction shows the bet did not arrive by its date. Whether that counts against the thesis or only its timing depends on why, and the resolver records which. The brief asks resolvers not to edit the thesis in the same pull request. If a bet loses, the record keeps the losing argument next to the evidence that it lost, and any rewrite has to come later, in its own change, where a reader can see what changed and why.

## What a checker has to establish

The criteria also differ in what kind of fact they need. Some describe what a player would see. The inspection-shift bet needs runtime-generated cases whose correct outcome is computed from the game's rules rather than authored case by case. The chronicle bet needs an automatically written history of a run that the player can export or share. The companion bet needs skills learned from the player that persist and can be reused on new tasks. Each still needs the store page, patch notes, or documentation to say so, so play only tells a checker what to look for.{{assert:field.generated-inspection-shifts.falsifiable_signal.resolve_by == first_prediction_resolves}}

Others turn on how the game is built, which only the developer can show. The neural-rendering bet needs documentation that gameplay state is symbolic and that the main view is produced frame by frame by a learned renderer. The mean-field bet needs the developer to name a mean-field, continuum, or equilibrium-field method used at runtime for the main traffic or population model. Negotiating faction AI needs a statement that the language-based diplomacy chooses its offers with a planner or an evaluation of game state.{{assert:field.symbolic-sim-neural-render.falsifiable_signal.resolve_by == 2029-12-31}}{{assert:field.mean-field-crowds.falsifiable_signal.resolve_by == 2029-12-31}}

The salience-gated bet counts titles the way the local-first bet does: three colony or life sims, each over 1,000 reviews, with model calls triggered by discrete events while routine behaviour runs on systems without a model.

## The two quiet outcomes

A prediction resolves `ambiguous` when evidence exists but a criterion cannot be checked as written, and the note must say which criterion and why. A prediction is `withdrawn` when its premise no longer holds before its date, and the note says why. Both outcomes keep the original prediction in the record beside the reason it did not resolve cleanly.

## A prediction that was true when written

The prediction the first review found already true was a bet on weather-coupled power grids. It predicted developer documentation of renewable output and storage that depend on the weather, and [[cities-skylines-2|Cities: Skylines II]] already coupled solar and wind output to the weather, with battery storage. The record was deprecated rather than deleted. It names the reason and the bet that supersedes it, learned regional weather, which keeps the remaining idea of learned weather driving a game's systems.{{assert:n_opportunity_deprecated == 1}}{{assert:field.weather-coupled-grids.deprecated.superseded_by == learned-weather-layer}} Deprecated records stay in the repository and drop out of every count in this book, so the {{stat:n_predictions}} predictions in the table are the live ones.

## Horizon and date

A bet's horizon and its resolve date measure different things. The horizon is the record's judgment of when the design becomes usable: a horizon of now means usable in a production title started today. The date is the deadline for the evidence the prediction names, usually a shipped title above a review bar. The two can sit years apart. The living-workforce bet is rated buildable now, and its prediction, which asks for a factory game with generational workforce mechanics to reach 1,000 Steam reviews, runs to the end of 2029.{{assert:field.living-workforce-factories.horizon == now}}{{assert:field.living-workforce-factories.falsifiable_signal.resolve_by == 2029-12-31}} Of the bets rated buildable now, {{stat:n_opportunity_now_due_2029}} resolve in 2029 or later.{{assert:n_opportunity_now_due_2029 >= 1}} A refutation records that the window closed without a qualifying title, and the brief counts it against the thesis even when the design was buildable throughout.

## What the scoreboard will show

Nothing has been checked yet; the first {{stat:n_predictions_first_date}} predictions come due on {{stat:first_prediction_resolves_long}}.

The simplest result will be a count: how many of the bets the dataset ranked highest came true, against how many of the ones it ranked lowest. If the priority scores in chapter 10 mean anything, confirmations should cluster near the top of the table. A cluster of refutations among the legibility bets would say that the argument running through this book, that explanation is the most neglected use of current techniques, was wrong about what studios would build, even if it was right about what players need.

The predictions also test the dataset's maturity scores. Chapter 7 classified each technique as research, prototype, shipped in a niche, or shipped as a norm. A prediction that depends on a research-stage technique and still resolves `confirmed` by its date is evidence that the maturity scale ran behind the field.

Each edition names the version of the dataset it was built from, and a new edition follows when predictions resolve or the catalog grows substantially. Every number in this chapter is a placeholder the build fills in, so an edition built after the first resolutions will print different counts, and the sentences asserting that all predictions are open will fail the build until someone rewrites them.

## Exercise: resolve one early

Pick a prediction from the table whose date is more than a year away.

1. Read its criteria and list every fact a resolver would need to establish, each as a yes-or-no question.
2. Search for evidence today. For each question, note whether you found an answer and where.
3. Decide what the outcome would be if the date were today. If any question is open, say what evidence would close it.
4. Write the note you would attach to the resolution, in two sentences, so that someone who never saw your search could check it.

Step 1 usually turns up a question the criteria leave open, and a question like that is grounds for a proposal to sharpen the prediction before it comes due. Chapter 13 covers the rules that govern such a proposal, from the run that records it to the review it needs.
