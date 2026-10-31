# The film: Every Simulation Game Is Built From the Same Parts

One long cut of the twelve episodes, released with the book's first edition so the two point at each other. It is assembled from finished episodes plus three new pieces, so it costs editing time and no new production. Every episode stays up on its own.

## Assembly

- Each episode's title card is cut; the film has one title, after the opening.
- Each episode's closing scene is cut except episode 12's, which ends the film. Lines that point to the next episode go with them.
- Cold opens stay. Each one starts a chapter of the film on a moment in a game.
- The three new pieces below open the film and join its acts. Their numbers are filled from the dataset like the episodes', so the film's edition names one dataset version.
- With the recorded narration the twelve episodes run about 86 minutes and the film about 84: the episodes less their title cards and closes, plus the three new pieces.
- Lines that name another episode, or this one, are re-voiced for the film so they name chapters instead (Film wording, below). The picture and on-screen text of those scenes stay the episode's.

| Act | Episodes | Bridge before it |
|---|---|---|
| I. The grammar | 1 to 5 | Opening |
| II. The machines arrive | 6 to 8 | Bridge one |
| III. Bets and checks | 9 to 12 | Bridge two |

## Film wording

The film re-voices these episode scenes so their cross-references name the film's chapters. Each entry is the scene's narration as the film speaks it, and replaces that scene's Voice lines in the film only. When an episode scene below changes, change its entry here too.

### Episode 1, scene 9: Where genres spend

**Voice.** Count where each genre spends its parts and the genres separate. Life sims put about a third into agents and behavior.{{assert:top_family_life_sim == agents-behavior}}{{assert:top_family_pct_life_sim >= 30}} Factory games lead with production.{{assert:top_family_factory_automation == resources-production}} Programming games lead with control.{{assert:top_family_programming_sim == control-automation}} Vehicle sims lead with careers and missions, ahead of the physics.{{assert:top_family_vehicle_sim == progression-goals}} And the AI-native games, the ones built on learned models, lead with social relations.{{assert:top_family_ai_native == social-relations}}

**Voice.** Of the {{stat:n_possible_pairs}} possible pairs of mechanics, {{stat:pair_coverage_pct}} percent have ever shared a catalog game.{{assert:pair_coverage_pct < 50}} Later chapters go looking in the gaps.

### Episode 4, scene 4: Two scores

**Voice.** The dataset behind this series scores every mechanic on six scales. Two matter here. Legibility asks how easily a player builds an accurate picture of the mechanic from play. A 2 means you need a wiki. A 5 means it's clear at a glance. Emergence potential asks how much unscripted variety the mechanic produces when it's connected to others. A 4 means it often sets off chains of consequences across systems.

**Voice.** Dwarf Fortress's stress system scores 3 and 4.{{assert:field.stress-accumulation.legibility == 3}}{{assert:field.stress-accumulation.emergence_potential == 4}} Its simulated history, which can run a world forward thousands of years before you arrive, scores 2 and 5.{{assert:field.history-generation.legibility == 2}}{{assert:field.history-generation.emergence_potential == 5}} The pause button scores 5 and 1.{{assert:field.variable-speed.legibility == 5}}{{assert:field.variable-speed.emergence_potential == 1}}

**Voice.** One model rater assigned the original scores by reading each mechanic's record against the anchors. Independent second ratings now cover {{stat:n_scores_independently_rated}} scores.{{assert:n_scores_independently_rated > 0}} The patterns in this chapter still rely largely on the original rater's reading of the design knowledge in the records. They aren't measurements of players.

### Episode 4, scene 10: Choosing a point

**Voice.** Dwarf Fortress was built to break each system into parts and base each one on something real [@src-adams-2015-df-simulation-principles]. It has more mechanics than any other game in the catalog, {{stat:max_mechanics_per_game}}.{{assert:most_mechanics_game == Dwarf Fortress}} The stress numbers at the start of this chapter come from the community wiki, because the game doesn't show them. RimWorld took several of the same systems and chose them for how readable their results are. Its stress is a mood bar with visible break lines, and every thought has a number and a timer.

**Voice.** Oxygen Not Included puts much of its depth in one rule for heat, applied to every cell, and gives you overlays to read the result. Victoria 3 puts its explanation inside the numbers.

### Episode 5, scene 6: What a player can follow

**Voice.** The third ceiling was the last chapter. On the dataset's scores, the mechanics that produce the most variety are the hardest to read, so every system a game connects to the others needs a way to be understood: an overlay, a tooltip, an inspection panel. Each one costs design time and screen space.{{assert:rho_legibility_emergence_potential < -0.2}}

### Episode 5, scene 7: Same inputs, same world

**Voice.** Replays, bug reports from save files, leaderboards, and lockstep multiplayer all depend on the same inputs producing exactly the same world. In lockstep play, every player's machine runs the whole simulation and only inputs cross the network. Factorio is built around it. Its items move in exact, discrete steps, a belt carrying 15, 30, 45, or 60 items a second depending on its tier, so every machine in a multiplayer game computes the identical factory [@src-factoriowiki-2026-transport-belt-physics].

**Voice.** That requirement has kept learned models out of the parts of games that decide what happens. The dataset sorts every AI technique that can run during play by what it does to reproducibility. Some break it outright. More can be made reproducible by fixing a seed, caching an answer, or logging what the model said. Chapter 10 is about what happens when they meet a game that depends on it.{{assert:n_technique_runtime_breaks < n_technique_runtime_mitigable}}

### Episode 6, scene 10: What writes into the simulation

**Voice.** Only a few shipped techniques change the game's state, the part your save file and a replay depend on. A model's answer can be cached as a rule, which Infinite Craft does, and the next chapter starts there.{{assert:field.llm-rule-adjudication.maturity == shipped-niche}} Language-model characters choose actions in inZOI and a few AI-native games. And trained or search-based opponents drive cars and armies. The {{stat:n_technique_shipped}} shipped techniques reach mechanics that make up {{stat:pct_uses_touched_by_shipped}} percent of what catalog games use.{{assert:pct_uses_touched_by_shipped < 50}}

**Voice.** Nothing learned has replaced a game's physics or its world in a catalog game. The models that would replace the engine itself are prototypes. GameNGen ran DOOM at 20 frames a second on one TPU, and its authors say it can't make new games [@src-valevski-2024-gamengen]. When Google opened Genie 3 to subscribers, each world allowed sixty seconds of play, a limit DeepMind put down to compute, and a reviewer watched characters walk through walls [@src-techcrunch-2026-project-genie]. Microsoft's Quake II demo ran at about ten frames a second, with health counters that couldn't be trusted [@src-microsoft-2025-whamm].{{assert:field.genie-world-models.maturity == prototype}}{{assert:field.diffusion-game-engines.maturity == prototype}}

**Voice.** These models keep the game's state as pixels. Health, position, the layout of the map exist only in the frames they remember, so whatever scrolls out of memory can come back different. A simulation game needs the cow in the field on day one to be the same cow on day three hundred.

### Episode 9, scene 7: A colonist with a memory

**Voice.** Another bet near the top goes back to the cook from chapter 1. Most of what a colonist does is routine: eat, sleep, haul. Cheap rules handle that. The memorable moments are rare, a death, an insult, a breakdown. So keep the rules running every tick, and call a language model only when something crosses a threshold of importance.{{assert:rank.opportunities-ranked.salience-gated-llm-agents <= 5}}

**Voice.** The model's answer has to fit a schema: a thought with a mood value and a duration, maybe a change to a relationship, maybe one spoken line. It lands in the same list that explained her breakdown. The test caps the whole colony at four model calls per real hour, each held to 400 tokens, and measures believability in blind playtests, tokens per player-hour, and contradictions, like a colonist mourning someone who's still alive. Success needs a point of believability on a seven-point scale, under two thousand tokens per player-hour, and fewer than one contradiction an hour.

### Episode 10, scene 4: Same inputs, same world

**Voice.** Factorio's record notes that items move in fixed, discrete steps, and that's what lets its multiplayer run identical worlds on every machine. The same property gives you replays, bug reports a developer can reproduce, leaderboards you can trust, and saves that load into the world you saved.

**Voice.** Of the techniques in the dataset that can run while you play, {{stat:n_technique_runtime_breaks}} break that property outright.{{assert:n_technique_runtime_breaks < n_technique_runtime_mitigable}} Frame-generating world models, language-model game masters, societies of language agents, realtime voice: each samples its output, and its output decides what happens next.{{assert:field.genie-world-models.determinism_impact == breaks}}{{assert:field.llm-game-master.determinism_impact == breaks}}{{assert:field.realtime-voice-models.determinism_impact == breaks}}

**Voice.** Infinite Craft, from chapter 7, stores each answer the first time a model gives it, so every player after that gets the same one.{{assert:field.llm-rule-adjudication.determinism_impact == mitigable}}

**Voice.** Townscaper fits its houses together with a deterministic algorithm, wave function collapse, so the same clicks always build the same town.{{assert:field.wave-function-collapse.determinism_impact == preserves}} Neural upscaling and frame generation never touch the simulation at all; they work on the picture after the game has decided everything. That's part of why they're the one learned technique that has become normal in games, and the dataset marks them as leaving reproducibility intact.{{assert:field.neural-rendering-shaders.maturity == shipped-mainstream}}{{assert:field.neural-rendering-shaders.determinism_impact == preserves}} Of the {{stat:n_predictions}} bets in the last chapter, {{stat:n_opportunity_applies_breaking}} lean on at least one technique that breaks reproducibility, so each of those needs a plan for it.{{assert:n_opportunity_applies_breaking < n_predictions}}

### Episode 10, scene 5: Contradiction

**Voice.** A gap in a simulation is survivable. A contradiction teaches the player something false. Chapter 7 showed a language model getting the state of a text game wrong close to half the time. A diffusion model trained on Counter-Strike footage lets the player jump again in mid-air, which the real game never allows [@src-alonso-2024-diamond]. In one playtest, players reported language-model characters forgetting what they had said earlier in one report out of ten [@src-peng-2024-player-driven-emergence].

**Voice.** Asked to predict what the simulation will do, it's wrong often enough to mislead. Asked to describe what the simulation did, from a log of events the simulation computed, it has the answer in front of it.

### Episode 10, scene 10: A log as the fix

**Voice.** Record every change to the game as an event, including the changes a model decided, and treat the log as the source of truth.{{assert:rank.opportunities-ranked.event-sourced-sim-runtime <= 5}} In the desynced match, the opponent's move would have been decided once and sent to both machines. A replay reads the logged answer instead of asking the model again. A bug report carries the log. And the "why?" button from the last chapter cites it.

**Voice.** A second tool limits what the model can write in the first place: constrained decoding only lets it produce output that fits a schema, so every action it proposes is one the engine can carry out. A hosted version followed a complex schema every time in testing, against under forty percent for an older model without it [@src-openai-2024-structured-outputs]. Strict formats cost some reasoning accuracy [@src-tam-2024-let-me-speak-freely], and the dataset hasn't found a shipped game that documents using it.{{assert:field.constrained-decoding.maturity == research}}

### Episode 11, scene 6: The calendar

**Voice.** All {{stat:n_predictions}} are open right now.{{assert:n_predictions_open == n_predictions}} {{stat:n_predictions_by_2027}} come due by the end of 2027, {{stat:n_predictions_by_2028}} by the end of 2028, and the last on {{stat:last_prediction_resolves_spoken}}.{{assert:n_predictions_by_2027 < n_predictions_by_2028}} The {{stat:n_predictions_first_date}} due first cover the why button, events generated against a schema, endless inspection shifts for a Papers, Please-style game, furniture generated from text, run histories written up automatically, local language models, automated balancing, a voice instructor in a flight or racing sim, and simulation games released as test beds for AI agents. Most of the early dates belong to bets rated buildable now. The late ones are the long shots from chapter 9: a game drawn by a generative model, a mechanic invented by a search program.

### Episode 12, scene 4: Everything is a build

**Voice.** The whole dataset is a folder of plain-text records. Everything else is built from it on every change: the paper, the website, the book, and the script for this film. Nothing computed is stored. A mechanic's prevalence, a game's cluster, a bet's priority: each is worked out again on every build, because a stored copy would drift.

**Voice.** Sentences are the hard part, because they interpret numbers. So every number in this series is a token the build fills in, and every sentence that interprets one carries a check. When chapter 1 said four of the five most common parts don't simulate anything, the build checked all five ranks. If the data stops agreeing, the build fails until somebody rewrites the line.

### Episode 12, scene 5: The rules came from failures

**Voice.** Most of the rules exist because something went wrong once. The first catalog was built by agents working in parallel, each taking a slice of games. An outside reviewer found that they'd recorded each game's distinctive parts and skipped the obvious ones: pause, building placement, tech trees. The finding that opened this series, that most of the commonest parts don't simulate anything, wasn't visible in that first data. The gaps were filled, and the analysis was redone.

**Voice.** The same review caught the paper calling some techniques impossible to reproduce when their own records said they could be. Now a sentence about a technique is checked against that technique's record.{{assert:field.monte-carlo-tree-search.determinism_impact == mitigable}}

**Voice.** A later review removed one game at a time and re-ran everything. Several claims about which games belong together broke, because the samples used to test the clusters were reshuffled whenever the catalog changed. Each game's place in each of the {{stat:cluster_subsamples}} samples is now fixed by a hash of its name, and a claim that two games belong together has to hold in at least {{stat:cocluster_together_pct}} percent of them.

**Voice.** Even the number of clusters follows a written rule: the smallest number whose clusters stay stable across the samples. The number is fixed so new games don't reshuffle everything, and when the data moves far enough that the rule would choose another, the build warns and the number is chosen again by the rule. Today it is {{stat:cluster_k}}.{{assert:cluster_k == cluster_rule_k}}{{assert:cluster_k_drift == 0}} Chapter 3 only claims the groupings that survive resampling.

## YouTube chapters

Recompute these from the render when an episode or its narration changes: `scripts/video/assemble.py film` writes the slate times to `video-out/out/the-film/states.json`. The times below are from the render with the recorded narration; the film runs 1:23:54.

| Start | Chapter |
|---|---|
| 0:00 | Opening |
| 0:54 | 1. Every simulation game is made of the same parts |
| 5:52 | 2. Where the parts came from |
| 13:28 | 3. Families across genres |
| 20:40 | 4. Why deep systems are hard to read |
| 27:07 | 5. The five ceilings |
| 33:55 | Bridge: the machines arrive |
| 34:40 | 6. What AI shipped |
| 42:32 | 7. Where AI lands |
| 49:48 | 8. Vacant lots |
| 57:05 | Bridge: from gaps to bets |
| 57:37 | 9. Bets worth making |
| 1:04:28 | 10. What breaks |
| 1:10:41 | 11. Keeping score |
| 1:17:09 | 12. How this was made |

## 1. Opening (0:00 to 2:00)

**Picture.** A teletype prints a line of text in 1968: the steward's yearly report on a city's grain. The camera pulls back as the line becomes the first row of the catalog grid, and rows pour in beneath it, one per game, a year counter running in the corner up to {{stat:year_max}}.

**Voice.** In 1968, a program asked its player how many bushels of grain to feed the people. The dataset behind this film starts there and runs to this year: {{stat:n_game}} simulation games, broken into {{stat:n_mechanic}} named parts, every one with its sources.

**Picture.** The grid's five fullest columns light up, then RimWorld's row with its core columns, each nearly empty.

**Voice.** Four of the five parts that turn up most often in those games model nothing in the world: a pause button, building placement, mod support, and a tech tree. The fifth is a treasury.{{assert:derived.variable-speed.prevalence_rank == 1}}{{assert:derived.free-placement.prevalence_rank == 2}}{{assert:derived.modding-api.prevalence_rank == 3}}{{assert:derived.budget-treasury.prevalence_rank == 4}}{{assert:derived.tech-tree.prevalence_rank == 5}} And most games count at least one rare part among their core.{{assert:pct_games_with_rare_core >= 75}}

**Picture.** The technique-flow ribbons draw in from the right and land on a handful of columns; most of the grid stays unlit.

**Voice.** Research on AI in games lands on a few of those columns. {{stat:n_mechanics_zero_exposure}} mechanics, carrying {{stat:pct_uses_on_zero_exposure}} percent of every use in the catalog, have no technique in the dataset aimed at them, the treasury among them.{{assert:pct_uses_on_zero_exposure >= 40}}{{assert:derived.budget-treasury.technique_exposure == 0}}

**Picture.** A calendar strip scrolls forward; dates light up one by one, the first group bunched on a single day.

**Frame.** timeline kind=due date=2027-12-31

**Voice.** The dataset also makes {{stat:n_predictions}} bets about what comes next, each with a date on which it can be wrong. The first {{stat:n_predictions_first_date}} come due on {{stat:first_prediction_resolves_spoken}}.{{assert:n_predictions_open == n_predictions}}

**On screen.** Every Simulation Game Is Built From the Same Parts.

## 2. Bridge: the machines arrive (between episodes 5 and 6, about 1:30)

**Picture.** The five ceilings from episode 5 as five horizontal lines across the screen. Dots appear on a timeline beneath them, one per technique, each rising to the ceiling it presses on and colored by how far it has shipped.

**Frame.** timeline kind=techniques

**Voice.** Each of those ceilings has techniques pressing on it. The dataset records {{count:technique}} of them, each a dated result that changes at least one mechanic, and {{stat:n_technique_since_2023}} are dated 2023 or later.{{assert:n_technique_since_2023 > 20}} Language models, asset generators, and learned motion press on authoring cost. Neural rendering and learned surrogates for physics and weather press on compute. Language-model characters press on believability.

**Picture.** The determinism line darkens as a cluster of dots pushes down on it from above.

**Frame.** count kind=tally of=technique field=determinism_impact where=in-play

**Frame.** count at="have shipped in at least one game" kind=tally of=technique field=maturity

**Voice.** Determinism is the ceiling some of them push the other way. Of the techniques that can run during play, {{stat:n_technique_runtime_breaks}} break reproducibility outright.{{assert:n_technique_runtime_breaks >= 5}}

**On screen.** {{count:technique}} techniques. Shipped in a game: {{stat:n_technique_shipped}}. A norm in shipped games: {{stat:n_technique_shipped_mainstream}}.

**Voice.** {{stat:n_technique_shipped}} have shipped in at least one game, and one has become a norm.{{assert:n_technique_shipped_mainstream == 1}} In 2019 a text adventure ran its whole world on a language model.

## 3. Bridge: from gaps to bets (between episodes 8 and 9, about 1:15)

**Picture.** The vacant-lots plan on the left half of the screen, the technique-flow ribbons on the right. Lines from both run to the middle and become the rows of one table.

**Frame.** chain nodes="map-overlay:The empty lots,language-model:The techniques,dataset-record:The bets" verbs="meet,in one list"

**Frame.** count at="By the dataset's reading" kind=tally of=opportunity field=horizon

**Voice.** The empty lots and the techniques meet in one list: {{count:opportunity}} bets, each a design that combines mechanics the catalog already has with a technique the dataset records. Each names the games that partly do it already, an experiment a small team could run, and a prediction with a date. By the dataset's reading, {{stat:n_opportunity_horizon_now}} could be built now.{{assert:n_opportunity_horizon_now >= 10}}

**Picture.** The table sorts itself by priority; the top rows glow, then every row's status cell reads "open".

**Voice.** None of them has been tested, and none of the predictions has come due.{{assert:n_predictions_open == n_predictions}} The first one starts with a factory that has stopped, and a player who can't tell why.
