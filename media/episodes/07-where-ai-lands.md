# Episode 7. Where AI lands

Target runtime about 12 minutes: about 1,270 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 8. Footage: Infinite Craft, RimWorld, Crusader Kings III, Victoria 3, Dwarf Fortress, inZOI, The Sims, Factorio, all captured by us; a still from the DIAMOND paper's Counter-Strike model, credited. Publisher video policies are tracked in `media/rights.yaml` and must be checked before release. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** Infinite Craft stores a language model's answer and treats it as a rule. Counting every technique against every mechanic shows research aimed at generative content, while the economic core most games are built from has almost nothing aimed at it.

## 1. Cold open (0:00 to 0:36)

**Picture.** Infinite Craft. Four tiles: water, fire, wind, earth. The cursor drags one onto another; a new tile pops out. Faster now, combination after combination. Then one combination pauses for a beat, a new tile appears, and a badge flashes: First Discovery.

**Frame.** moment panels="tile-cell+tile-cell:Every pair you try|cache:Has an answer every player shares|language-model:A pair nobody tried goes to a model|badge:Saved, and yours for everyone after"

**Voice.** Every pair you try in Infinite Craft has an answer stored in a database every player shares. Until you try a pair nobody's tried. Then a language model names the result, the game saves it, and from that moment everyone who makes that pair gets your answer [@src-wikipedia-infinite-craft].

## 2. Title (0:36 to 0:46)

**Picture.** Title card over a wall of tiles.

**On screen.** Where AI lands. Episode 7.

## 3. A rule decided once (0:46 to 2:04)

**Picture.** A diagram: a pair of tiles goes into a lookup box. Hit: the stored answer comes back. Miss: an arrow to a model, then back into the box, which now holds one more row.

**Frame.** chain nodes="tile-cell:A pair,cache:The stored answers,check-pass:Hit: the stored answer comes back|cache:Miss,language-model:A model names the result,dataset-record:One more row" verbs="look up,hit|asks,saves"

**Voice.** That's the clearest case in the dataset of a language model deciding a rule in a shipped game, and it works because the decision only happens once. The cache turns an unpredictable model into a rule table that grows with play and gives everyone the same result. It bounds the bill too: the model only runs for pairs nobody has tried, so the cost grows with the number of new combinations and stays flat as players join.{{assert:field.llm-rule-adjudication.determinism_impact == mitigable}}

**Voice.** It also helps that a combination has no right answer. When researchers asked GPT-4 to predict the next state of text games, across 76,369 transitions, it got the whole state right at most 59.9 percent of the time [@src-wang-2024-text-world-simulators]. An Infinite Craft tile only has to be plausible once. A model asked to run a city's water table would have to be right every tick.

## 4. Where the techniques come from (2:04 to 3:00)

**Picture.** A timeline of the dataset's techniques by year: a thin trickle from 2006, then a wall of cards from 2023 on, most labelled with language models or world models.

**Frame.** timeline kind=techniques current=generative-world-model

**Voice.** The techniques in the dataset are recent. {{stat:n_technique_since_2023}} of the {{count:technique}} are dated 2023 or later, and the biggest single group is world models, the systems that generate a playable scene frame by frame.{{assert:n_technique_since_2023 > 20}} The set was built by looking for dated results that change a named game mechanic, so it probably leans toward fields that publish constantly and say so when they apply to games. A scheduling method from operations research that could balance a game's economy only gets in once someone applies it to a game and writes it down.

## 5. Seven kinds of change (3:00 to 4:09)

**Picture.** Seven quick clips, each labelled with one effect: a Zoi crossing a room on a model's decision, "replaces"; a GT Sophy car on the limit, "deepens"; a teammate following a spoken order, "enables"; a scene appearing from a typed prompt, "cuts authoring"; a tooltip, "explains"; a bot running a test level, "tunes"; a flight sim at a higher frame rate, "accelerates."

**Frame.** count kind=tally of=link field=effect

**Voice.** Every technique in the dataset is linked to each mechanic it changes, and every link says how. It can replace how a mechanic works, the way inZOI's small model reads a Zoi's needs and surroundings to help pick its next action. It can deepen a mechanic, the way GT Sophy drives the same physics you do at a champion's level. It can enable a new version, like a teammate who takes spoken orders. It can cut the cost of making content, explain a mechanic to the player, tune it, or run it faster. Across {{stat:n_affects_edges}} links, the most common is deepening. The rarest is explaining: {{stat:n_effect_explains}} links, from {{stat:n_explains_techniques}} techniques, and only {{stat:n_effect_explains_shipped}} of those links comes from something that has shipped.{{assert:top_effect == Deepens}}{{assert:rarest_effect == Explains}}{{assert:n_effect_explains_shipped == 1}}

## 6. Explanation by hand (4:09 to 5:21)

**Picture.** RimWorld's needs tab, every thought listed with a number and a timer. Victoria 3: a tooltip, then a tooltip inside the tooltip, then another. Dwarf Fortress: a dwarf throwing a tantrum, with nothing on screen saying why.

**Frame.** compare a="Explained by hand" a_items="memories-thoughts:RimWorld lists every thought,causal-tooltips:A tooltip inside a tooltip" b="Never shown" b_items="stress-accumulation:Dwarf Fortress keeps stress hidden"

**Frame.** record at="A model that reads the simulation" technique=llm-explanation-of-state fields=summary,maturity,determinism_impact

**Voice.** Today, games that explain themselves do it by hand. RimWorld lists every thought behind a colonist's mood, with its value and when it expires; its systems were chosen partly for how readable their results are. In Crusader Kings III and Victoria 3 you can hover any number to see what produced it, then hover a term inside that tooltip to open another one. Dwarf Fortress keeps each dwarf's stress as a hidden number between minus and plus a million. You see the tantrum and never the account behind it.{{assert:derived.causal-tooltips.prevalence <= 5}}

**Voice.** A model that reads the simulation's own modifier lists and event log could give any game the Paradox treatment, as long as it reports what the simulation computed instead of guessing. The technique that does this is still a prototype.{{assert:field.llm-explanation-of-state.maturity == prototype}}

## 7. Counting exposure (5:21 to 6:12)

**Picture.** The technique-flows figure builds: techniques on the left, effects in the middle, mechanic families on the right, ribbons running between them. Four families on the right collect most of the ribbons.

**Voice.** Add the links up, counting a shipped technique for more than a paper, and you get a measure of where the field is pointed. The dataset calls it exposure. In total, it piles up in four families: narrative, agents, control, and physics.{{assert:top_exposed_family == Narrative & generation}}{{assert:rank.family-summary.agents-behavior <= 4}}{{assert:rank.family-summary.control-automation <= 4}}{{assert:rank.family-summary.physics-materials <= 4}} Those are the places where content is expensive to write, like events and dialogue, or behavior is expensive to compute, like bodies and crowds. Divide by how many mechanics each family holds and narrative still leads, with world generation second.{{assert:top_mean_exposed_family == Narrative & generation}}{{assert:rank.family-mean-exposure.world-generation <= 2}}

## 8. The most exposed mechanics (6:12 to 7:15)

**Picture.** A ranked list builds: generative content, procedural terrain, utility action selection. Beside each, a small bar of how many catalog games use it. The first bar is tiny.

**Frame.** count kind=bars rank_by=exposure ids=generative-content,procedural-terrain,utility-action-selection

**Voice.** The most exposed single mechanic is generative content, and only {{derived:generative-content.prevalence}} catalog games use it, almost all of them AI-native.{{assert:rank.most-exposed-mechanics.generative-content <= 2}}{{assert:derived.generative-content.prevalence < 10}} Exposure measures where research looks, and the games are mostly built from somewhere else.

**Voice.** Procedural terrain comes next. Satellite reconstruction rebuilt the planet for Microsoft Flight Simulator, learned generators would replace hand-tuned noise, and world models make a scene from a sentence and forget it a minute later.{{assert:rank.most-exposed-mechanics.procedural-terrain <= 2}} Its neighbour in the same family, simulated history, has nothing pointed at it at all. Third is the scoring that picks a character's next action, which runs the characters of {{derived:utility-action-selection.prevalence}} catalog games, from Theme Park in 1994 to RimWorld.{{assert:rank.most-exposed-mechanics.utility-action-selection == 3}}{{assert:derived.utility-action-selection.earliest_game == theme-park}}

## 9. What they'd change (7:15 to 8:44)

**Picture.** Crusader Kings III: an event window about a rival's illness, then a second event weeks later about a succession dispute. The Sims: a Sim choosing between a fridge, a bed, and a TV, each with a diagram score drawn above it.

**Frame.** compare a="Authored event chains" a_items="triggered-event-chains:Fire when conditions hold" b="A language-model game master" b_items="llm-game-master:Writes the next event for your game"

**Frame.** compare at="Many simulated characters pick" a="A score from needs" a_items="utility-action-selection:Score each option and take the best" b="A prompt" b_items="on-device-language-models:A small model helps choose"

**Voice.** Crusader Kings III's stories come from authored event templates that fire when conditions hold and schedule a follow-up weeks later. A language-model game master would write the next event for the exact state of your game instead.{{assert:field.llm-game-master.maturity == shipped-niche}} Authored chains repeat once you've seen them all. Generated ones agree to things a human game master would refuse, and invent quests that don't exist [@src-gallotta-2024-llms-games-survey].

**Voice.** Many simulated characters pick their next action by giving each option a score from their needs and taking the best. Language-model characters replace the score with a prompt, and inZOI ships a small model that helps make that choice. In control, menus give way to speech: a teammate that takes spoken orders mid-match, research agents that play commercial games through the screen and explain what they intend to do [@src-deepmind-2025-sima-2-blog], and agents that write and keep their own library of skills [@src-wang-2023-voyager].{{assert:field.generalist-game-agents.maturity == research}} In physics, the proposals that would replace the engine outright are video and world models, and none of them has shipped.{{assert:field.open-interactive-video-models.maturity == prototype}}

## 10. The economic core (8:44 to 10:34)

**Picture.** Factorio. A long production line; one furnace far upstream sits idle while the player inspects an assembler at the end of the line. The family-exposure bars rearranged per mechanic, resources and logistics at the bottom.

**Frame.** count kind=tiles family=resources-production lit=affected

**Frame.** count at="Economy and finance has" kind=tiles family=economy-finance lit=affected

**Frame.** record at="The production chain's own record" mechanic=production-chain fields=failure_modes

**On screen.** Resources and production: {{stat:n_family_mechanics_resources_production}} mechanics, {{stat:n_family_zero_exposure_resources_production}} with no technique.

**Voice.** Now look at the families most simulation games are built from. Resources and production is the most used family in the catalog, and of its {{stat:n_family_mechanics_resources_production}} mechanics, {{stat:n_family_zero_exposure_resources_production}} have no technique in the dataset pointed at them.{{assert:most_used_family == Resources & production}}{{assert:n_family_zero_exposure_resources_production >= 10}} Production chains, extraction, storage, crops: nothing.{{assert:derived.production-chain.technique_exposure == 0}} Economy and finance has {{stat:n_family_zero_exposure_economy_finance}} of its {{stat:n_family_mechanics_economy_finance}} mechanics untouched, and the one shipped technique that reaches it is tree search, for rival firms. Every link into logistics comes from research. Per mechanic, the economic families sit near the bottom of the table, and checklists and repair sit at zero.{{assert:rank.family-mean-exposure.resources-production >= 16}}{{assert:rank.family-mean-exposure.logistics-networks >= 16}}{{assert:least_exposed_family == Operation & procedure}}

**Voice.** The production chain's own record lists the problems a technique could take on. A single optimal ratio, once solved, turns play into copying calculator output. And without flow statistics, starvation far upstream is hard to diagnose, so players blame the wrong building. The first is a design problem that search could expose before release. The second is an explanation problem. Both are things the field already has tools for: bots that playtest a build shipped years ago.{{assert:field.automated-playtesting.maturity == shipped-niche}} Victoria 3 shows the second problem with prices. It sets each good's price from the buy and sell orders in each market, and its tooltips break a price into modifiers, yet the market mechanic's record lists boom-and-bust cycles that players still read as random.

## 11. Judgment against evidence (10:34 to 11:49)

**Picture.** A scatter of mechanics: judged AI leverage on one axis, exposure on the other. A handful of points sit high on judgment and flat on exposure, labelled: mod support, simulated history, blueprints, creature care.

**Voice.** Every mechanic also carries a judged score for how much AI could change it. Judgment and exposure line up at a correlation of {{stat:rho_ai_leverage_exposure}}.{{assert:rho_ai_leverage_exposure >= 0.3}} That's a check on consistency: the original model rater scored the judgment, wrote the links, and rated each technique's maturity. Independent second ratings now cover part of the mechanic scores; the links and maturity judgments retain their original authorship.

**Voice.** The disagreements point at specific mechanics. Mod support is used by {{derived:modding-api.prevalence}} catalog games, is judged highly open to AI, and has no technique attached.{{assert:derived.modding-api.technique_exposure == 0}} Simulated history, the centuries Dwarf Fortress runs before your fortress begins, is in the same position.{{assert:derived.history-generation.technique_exposure == 0}} So are blueprints, creature care, diagnosis, and the rule-checking that Papers, Please is built on.{{assert:derived.blueprints.technique_exposure == 0}}{{assert:derived.rule-checking-inspection.technique_exposure == 0}} A general-purpose model can write mod code today. A zero in this column means nobody has published or shipped that use for a named mechanic yet, and one pull request adding the evidence would change it.

## 12. Close (11:49 to 12:18)

**Picture.** The family bars again, the economic core dark at the bottom. Cut to a city at night with no events on screen.

**Voice.** Next episode looks for a different kind of gap: pairs of common mechanics that almost never appear in the same game, starting with a city builder that never tells a story.

**On screen.** The dataset, the sources, and the book: simgrammar.com
