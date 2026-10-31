# Episode 9. Bets worth making

Target runtime about 12 minutes: about 1,230 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 10. Footage: Factorio, RimWorld, Democracy 4, all captured by us; the bottleneck view, the why-query, the branch preview, and the language-modding workshop are mock-ups built on captured footage and labelled as mock-ups on screen. Publisher video policies are tracked in `media/rights.yaml` and must be checked before release. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** The dataset's bets on what to build next, each with an experiment and a dated prediction: a button that asks why, a preview of possible futures, colonists with a memory, mods written as a sentence. None of the leading bets asks a model to become the simulation.

## 1. Cold open (0:00 to 0:43)

**Picture.** Factorio, mid-game. The science counter ticks slowly. The production graph shows electronic circuits falling. The player places four new circuit assemblers and connects them; their input slots stay empty. The camera follows a belt upstream, past the cable assemblers, to a smelter column where one belt carries iron and copper together, the iron filling both lanes.

**Frame.** moment panels="science-flask:Science output has halved|assembler:New circuit assemblers wait|conveyor-transport:Upstream, iron fills the copper belt"

**Voice.** Science output has halved, and the graph shows you where it dropped without showing you why. So you build more circuit assemblers. Nothing changes; the new ones just wait. Twenty minutes later you find it: the copper smelters share a belt with iron, the iron gets there first, and the cable assemblers are starving three steps upstream of where you were looking.

## 2. Title (0:43 to 0:53)

**Picture.** Title card over the ranked table of opportunities, out of focus.

**On screen.** Bets worth making. Episode 9.

## 3. A tool that names the cause (0:53 to 2:11)

**Picture.** Mock-up, labelled: the same factory with a bottleneck view switched on. Machines shade from grey to orange by how much one more unit of each would raise circuit output. The cable assemblers glow. A one-line explanation appears with a link that jumps the camera to the shared belt.

**Frame.** mockup kind=ui bet=bottleneck-explainer title="Bottleneck view" items="furnace:Smelters,conveyor-transport:Shared belt,assembler:Cable assemblers,assembler:Circuit assemblers" lines="Circuits are limited by copper cable|Cable is starved because the smelters share a belt with iron"

**Frame.** count at="That's one of the bets in the dataset" kind=bars ids=production-chain

**Voice.** When starvation happens far upstream, players blame the wrong building. And the hunt never ends: the slowest stage sets the pace, so the bottleneck moves every time you fix one.

**Voice.** A tool that answered the question directly wouldn't need new AI. Add a little capacity to each machine and belt in turn, and measure how much the output rises. The one that raises it most is the constraint. Then a short generated sentence names it: circuits are limited by copper cable, which is starved because the smelters share a belt with iron.

**On screen.** Production chains: used by {{derived:production-chain.prevalence}} catalog games. Techniques in the dataset aimed at them: none.

**Voice.** That's one of the bets in the dataset, the bottleneck explainer. Production chains are among the most common mechanics in the catalog, and no technique in the dataset points at them.{{assert:derived.production-chain.prevalence_rank <= 10}}{{assert:derived.production-chain.technique_exposure == 0}}

## 4. What a bet contains (2:11 to 3:50)

**Picture.** The bottleneck explainer's record scrolls past, field by field: mechanics, techniques, precedent games, thesis, sketch, experiment, prediction.

**Frame.** record bet=bottleneck-explainer fields=involves,applies,precedent

**Frame.** record at="Two more fields make it a bet" bet=bottleneck-explainer fields=validation_experiment,falsifiable_signal

**Voice.** Like every one of the {{count:opportunity}} bets, it names the mechanics it reworks, the techniques it depends on, and the games that already do part of it: for this one, Factorio, Satisfactory, Anno 1800, and Oxygen Not Included.

**Voice.** Two more fields make it a bet. An experiment a small team could run, with a number that counts as success: inject a bottleneck into a factory prototype, and see whether players fix it at least fifty percent faster with the view on. And a prediction with a date: a factory or city game ships a feature that finds the binding constraint by testing the simulation, by the middle of 2028.{{assert:field.bottleneck-explainer.falsifiable_signal.resolve_by == 2028-06-30}}

**Frame.** count kind=tally of=opportunity field=horizon

**Voice.** Of the {{count:opportunity}} bets, {{stat:n_opportunity_horizon_now}} are buildable now, {{stat:n_opportunity_horizon_1_2y}} in one to two years, and {{stat:n_opportunity_horizon_3_5y}} in three to five.{{assert:n_opportunity_horizon_3_5y < n_opportunity_horizon_now}}

## 5. The why button (3:50 to 5:40)

**Picture.** Mock-up, labelled: a colony sim. The player right-clicks a closed hospital and picks "why?". Five sentences appear, each with a small link. Clicking one scrubs a timeline back to the event it names. A small causal graph draws beside the text.

**Frame.** mockup kind=ui bet=causal-why-query title="Why did the hospital close?" items="question:Why?" lines="Three to six sentences, each linked to an event in the log|Clicking a link scrubs the timeline back to that event|An answer that cannot be grounded says so"

**Frame.** record at="The experiment gives two groups" bet=causal-why-query fields=validation_experiment

**Frame.** record at="A fluent answer that isn't grounded" bet=causal-why-query fields=key_risks

**Voice.** The top of the table is the why-query.{{assert:rank.opportunities-ranked.causal-why-query == 1}} Overlays and tooltips tell you why a number is low right now. Nothing in a typical game tells you why the hospital closed three months ago. That's a chain of events, and the bet is to record those events with their causes and let a language model narrate the chain, with every sentence linked to an event in the log.

**Voice.** The output is constrained so the model can only say things it can point to, and an answer it can't ground says so. Many engines already keep an event log for replays and debugging. The bet is that showing it to players, through a "why?" button, lets designers ship deeper systems without losing people.

**Voice.** The experiment gives two groups the same failing save, one with the button and one without, and has people check whether the cited events actually support each sentence. Success means a correct diagnosis forty percent faster, with at least ninety-five percent of the sentences supported.

**Voice.** A fluent answer that isn't grounded teaches players a wrong model of the game, which is worse than no answer. Most shipped event logs don't record causes, and adding them is real engineering. And a perfect explainer might make the best move too easy to find.

## 6. Previewing the future (5:40 to 6:24)

**Picture.** Democracy 4, a policy screen. Mock-up, labelled: a Preview button. The view splits into a fan of faint lines for unemployment and approval over the next year, then two short replays of the futures that differ most.

**Frame.** mockup kind=ui bet=branch-preview-forecasts title="Preview" chart=fan lines="Unemployment and approval over the next year" button="Pass the law"

**Voice.** Second on the list is a branch preview.{{assert:rank.opportunities-ranked.branch-preview-forecasts == 2}} Before you pass a law, the game copies the live save dozens of times, runs each copy a year ahead with different random seeds, and shows you the spread. Because a deterministic simulation can fork from any moment, the preview runs the game's own rules. The target: sixty-four futures in under five seconds on an ordinary PC.

## 7. A colonist with a memory (6:24 to 7:46)

**Picture.** RimWorld again. The cook from episode 1, walking out of the kitchen. Her needs tab. Mock-up, labelled: one new line in the list, referring to her son by name and to an argument the week before.

**Frame.** mockup kind=ui bet=salience-gated-llm-agents title="Needs" items="memories-thoughts:One new thought" lines="Rules run every tick: eat, sleep, haul|A model is called only when something crosses a threshold of importance|Its answer fits a schema: a thought, a mood value, a duration"

**Frame.** record at="The model's answer has to fit a schema" bet=salience-gated-llm-agents fields=validation_experiment

**Voice.** Another bet near the top goes back to the cook from episode 1. Most of what a colonist does is routine: eat, sleep, haul. Cheap rules handle that. The memorable moments are rare, a death, an insult, a breakdown. So keep the rules running every tick, and call a language model only when something crosses a threshold of importance.{{assert:rank.opportunities-ranked.salience-gated-llm-agents <= 5}}

**Voice.** The model's answer has to fit a schema: a thought with a mood value and a duration, maybe a change to a relationship, maybe one spoken line. It lands in the same list that explained her breakdown. The test caps the model at one call per colonist per in-game hour and measures believability in blind playtests, tokens per player-hour, and contradictions, like a colonist mourning someone who's still alive. Success needs a point of believability on a seven-point scale, under two thousand tokens per player-hour, and fewer than one contradiction an hour.

## 8. Mods from a sentence (7:46 to 8:43)

**Picture.** Mock-up, labelled: an in-game mod workshop. The player types "wolves avoid fire". A diff to the game's data and scripts appears, then a headless test map where wolves circle a campfire at a distance, then before-and-after numbers, then a Share button.

**Frame.** mockup kind=ui bet=language-modding title="Mod workshop" items="prompt-box:A rule change as a sentence,modding-api:Code against the modding interface,check-pass:Tested on a headless map" button="Share"

**Frame.** record at="The experiment takes a hundred" bet=language-modding fields=validation_experiment

**Voice.** Mods keep simulation games alive for decades, and writing one takes programming skill. Language modding turns a rule change into a sentence.{{assert:rank.opportunities-ranked.language-modding <= 5}} A model writes the change against the game's own modding interface, agents test it on a headless map for crashes and for the effect you asked for, and the description, the code, and the test results travel together when you share it. The experiment takes a hundred real requests from a modding community. It counts as a success if at least sixty percent compile, pass the test, and do what the person asked.

## 9. The pattern (8:43 to 9:47)

**Picture.** A diagram builds: a solid block labelled "simulation state" in the middle; around it, four arrows from outside labelled read, explain, decorate, propose; a gate labelled "validator" on the propose arrow; a strip labelled "log" along the bottom.

**Frame.** chain fan nodes="tile-cell:Simulation state kept symbolic,magnifier:Read,question:Explain,rendered-frame:Decorate,check-pass:Propose through a validator,event-log:Every call logged" verbs="read,explain,decorate,propose,log"

**Voice.** The bets at the top of the table share one design. None of the leading bets asks a learned model to become the simulation. The state stays symbolic and deterministic, and models work around it. They read it and explain it. They propose changes that a validator accepts or rejects. They decorate it, writing the line a character says without deciding whether she lives. And every call goes into the log.

**Voice.** What has shipped mostly stays at the edge of game state. And the economic core of these games, production, logistics, money, has almost nothing pointed at it.{{assert:n_technique_shipped_mainstream <= 2}}{{assert:rank.family-mean-exposure.resources-production >= 16}}{{assert:rank.family-mean-exposure.logistics-networks >= 16}} Bets that keep the core symbolic can ship on techniques that already work.

## 10. Long shots (9:47 to 10:40)

**Picture.** The bottom of the feasibility scale. Three record cards slide in. Mock-up stills, labelled: a city drawn as watercolor over a tile grid; a map of hundreds of small agents with a chronicle scrolling beside it.

**Frame.** record bet=symbolic-sim-neural-render fields=summary,falsifiable_signal

**Frame.** record at="A terrarium of hundreds" bet=llm-society-terrarium fields=summary,falsifiable_signal

**Frame.** record at="And a search over rule programs" bet=mechanic-discovery-search fields=summary,falsifiable_signal

**Voice.** At the far end are the long shots, each scored low for feasibility and high for novelty.{{assert:field.symbolic-sim-neural-render.feasibility == 2}}{{assert:field.llm-society-terrarium.feasibility == 2}} A city builder that keeps its state as a tile grid and lets a generative model draw it in any style. A terrarium of hundreds of language-model agents that you seed, nudge rarely, and watch write their own history. And a search over rule programs that proposes new mechanics, checked against the catalog in this series for what already exists. That last prediction runs the longest, to {{stat:last_prediction_resolves_spoken}}.{{assert:field.mechanic-discovery-search.falsifiable_signal.resolve_by == last_prediction_resolves}}

## 11. Who builds what (10:40 to 11:31)

**Picture.** The ranked table again, its rows sorting into three columns: small studio, engine and tools, research.

**Voice.** The bets sort by who can make them. A small studio has the ones that are feasible now: an explanation layer over a game it already has, events generated against a schema, colonists with a local model, balance testing before launch. An engine or tools company has the infrastructure, starting with an event log that records every model call. A research group has the open problems, like proving that a generated picture of a city matches the city's actual state.

## 12. Close (11:31 to 12:03)

**Picture.** The Factorio factory from the cold open, running, the smelter belts split. The ranked table again, every row with a date beside it.

**Voice.** Every one of the {{stat:n_predictions}} bets in the dataset carries a date, and the first ones come due on {{stat:first_prediction_resolves_spoken}}. Before that, the next episode is about how these ideas fail: the desync, the contradiction, and the bill.

**On screen.** Every bet and the test that would settle it: simgrammar.com
