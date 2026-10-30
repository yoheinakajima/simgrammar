# Episode 5. The five ceilings

Target runtime about 12 minutes: about 1,260 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 6. Footage: The Sims, Crusader Kings III, Reigns, RimWorld, Noita, SimCity (2013), Dwarf Fortress, Factorio, Infinite Craft, RollerCoaster Tycoon, Creatures, all captured by us; stills and published figures from the Generative Agents paper and of Façade. Publisher video policies are tracked in `media/rights.yaml` and must be checked before release. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** Five limits on simulation games: content made by hand, ticks per second, what a player can follow, the same inputs giving the same world, and believable minds. Lifting one usually spends another, and the cost of authoring is falling fastest.

## 1. Cold open (0:00 to 0:29)

**Picture.** The Sims (2000). A Sim with a low Hunger bar. The player opens Buy mode; the clock stops. A new refrigerator goes against the kitchen wall. Time starts. The Sim turns away from the television, crosses the house, opens the refrigerator, and starts cooking.

**Frame.** moment panels="hunger:She is hungry|refrigerator:You buy a refrigerator|person-walking:She walks straight to it|cooking:The refrigerator told her how"

**Voice.** Your Sim is hungry. You buy a refrigerator, put it in the kitchen, and she walks straight to it. She didn't know how to use a refrigerator. The refrigerator told her.

## 2. Title (0:29 to 0:39)

**Picture.** Title card over the kitchen, frozen.

**On screen.** The five ceilings. Episode 5.

## 3. Behavior that lives in objects (0:39 to 2:36)

**Picture.** The kitchen again, with diagram labels popping off each object: refrigerator, Hunger; bed, Energy; toilet, Bladder 0 to 70. Lines run from the Sim to each label, thicker for the ones she needs most.

**Frame.** anatomy hub=person spokes="refrigerator:Hunger,bed:Energy,toilet:Bladder" weights=illustrative from=the-sims:smart-objects

**Frame.** chain at="each expansion pack extended" nodes="box:An expansion,smart-objects:New objects,menu:New actions" verbs="sells,bring" from=the-sims

**Frame.** scale at="The dataset scores the mechanic" field=smart-objects.authoring_cost

**Voice.** In The Sims, a Sim carries no knowledge of how to use anything. Each object advertises what it offers. A refrigerator advertises Hunger, a bed advertises Energy. When a Sim decides what to do, she collects the advertisements of everything she can reach, weighs them by what she needs and how far she'd have to walk, and picks one. The object supplies the rest: the script she runs and the animations she plays [@src-forbus-2001-programming-objects-sims].

**Voice.** That's why The Sims could keep growing. A new object brought new behavior without any change to the Sims, so each expansion pack extended what they could do by adding things to buy. The base game shipped with more than 150 objects. Every one of them was designed, scripted, animated, and tuned by hand. The dataset scores the mechanic 4 out of 5 for authoring cost.{{assert:field.smart-objects.authoring_cost == 4}} It brought its own bugs, too. Tune one object's advertisement too high and Sims queue for it whatever they need. Break an object that keeps advertising and Sims try to use it again and again.

**Picture.** A row of five ceiling tiles above the kitchen, each labelled: authoring, compute, legibility, determinism, believability.

**Frame.** count kind=set ids=ceiling-authoring,ceiling-compute,ceiling-legibility,ceiling-determinism,ceiling-believability

**Voice.** Authoring cost is one of five limits that have shaped what simulation mechanics can be. The others are the compute a machine can spend each tick, how much hidden state a player can follow, the need for the same inputs to produce the same world, and how believable a mind made of formulas can be.

## 4. Content made by hand (2:36 to 4:24)

**Picture.** Crusader Kings III: an event window about a rival's illness; a few game months later, a follow-up event about the succession; then a war declaration. Cut to Reigns: cards swiped left and right, four meters at the top of the screen moving.

**Frame.** scale ids=triggered-event-chains,dilemma-cards fields=authoring_cost

**Frame.** chain at="In Crusader Kings III an event fires" nodes="triggered-event-chains:A rival falls ill,dynasty-succession:A succession fight,war-score-peace:A war" verbs="months later,then" from=crusader-kings-3

**Frame.** chain at="Reigns runs a kingdom" nodes="dilemma-cards:A deck of cards,survival-meters:Four meters" verbs="each swipe moves" from=reigns

**Voice.** The two mechanics that eat the most content, by the dataset's scores, are both about story: chains of triggered events, and dilemma cards.{{assert:field.triggered-event-chains.authoring_cost == 5}}{{assert:field.dilemma-cards.authoring_cost == 5}} In Crusader Kings III an event fires from a birth, a death, or a yearly check, and schedules its own follow-up months later, so a rival's illness becomes a succession fight and then a war [@src-paradoxwikis-2026-ck3-event-modding]. Every branch is written by hand, and players who've played enough start seeing the same chains. Reigns runs a kingdom on four meters and a deck of cards, and after enough reigns you answer from memory.

**Picture.** Façade: the couple at their dinner, a text box, the player typing. A diagram fans the typed sentence into a short list of labels: agree, criticize, flirt.

**Frame.** chain nodes="prompt-box:Type anything,social-exchanges:One of a few social moves,storyteller-director:The drama manager picks the next scene" verbs="maps to,feeds" from=facade

**Frame.** count at="The rater who scored every mechanic also judged" kind=stat stat=rho_authoring_cost_ai_leverage label="between authoring cost and judged openness to AI, across every mechanic"

**Voice.** Open input hits the same ceiling. Façade, from 2005, let you type anything to a married couple at dinner. Behind the text box, each sentence was mapped to one of a small set of social moves, and a drama manager picked the next scene from a library its authors had written. One analysis counted 30 kinds of speech act and 27 story beats [@src-evans-2014-versu].

**Voice.** The rater who scored every mechanic also judged how open each one is to AI, and the two judgments line up. The mechanics that cost the most to author are the ones rated most open to generative models.{{assert:rho_authoring_cost_ai_leverage > 0.2}}{{assert:mean_ai_leverage_authoring_4plus > mean_ai_leverage_authoring_2_or_less}} It's one rater, so that's a consistent reading, not a finding twice confirmed.

## 5. Ticks per second (4:24 to 6:05)

**Picture.** RimWorld late in a long game: a large colony, the speed set to fastest. A graphic overlay, added in the edit, reads the speed the game is actually managing; it falls below the speed on the button.

**Frame.** count kind=set ids="agent-pathfinding:Paths recomputed after an edit,heat-transfer:Heat moving between thousands of cells,request-provider-logistics:A sky full of logistics robots"

**Voice.** Every real-time simulation advances its whole world many times a second while drawing the screen. When fast-forward can't keep up late in a game, you're seeing every other system's cost at once: paths recomputed after you edit the map, heat moving between thousands of cells, a sky full of logistics robots in a big factory. The records list each of those as a failure mode.

**Picture.** Noita: a pool of oil catches fire, steam bursts out of a flooded chamber, a ceiling of sand collapses. Every pixel moves.

**Frame.** toysim sim=sand from=noita:falling-sand-materials

**Frame.** count at="Falling-sand materials, where every pixel" kind=bars ids=falling-sand-materials

**Voice.** Physics and materials is the costliest family to compute: falling sand, fluids and gases, destruction down to the voxel.{{assert:top_compute_family == Physics & materials}}{{assert:n_mechanics_compute_4plus >= 5}} They're also among the rarest. Falling-sand materials, where every pixel is a material with its own rules, appear in {{derived:falling-sand-materials.prevalence}} catalog games. Noita is one of them, and it's a 2D game.{{assert:derived.falling-sand-materials.prevalence <= 2}}

**Picture.** SimCity (2013): agents carrying water and workers along the roads of a small city that stops at the edge of a tight boundary.

**Frame.** compare a="Most city builders" a_items="crowd:People as totals" b="SimCity, 2013" b_items="person-walking:Agents that carry workers and goods" from=simcity-2013:agent-pathfinding

**Frame.** chain at="Dwarf Fortress moves some of its cost" nodes="history-generation:Thousands of years simulated,save-file:A very large save" verbs="before you start" from=dwarf-fortress

**Voice.** The ceiling explains city builders too. Most simulate their people as totals with a few visible faces. When SimCity in 2013 switched to agents that carry workers, water, and goods between buildings, its cities were smaller than earlier games' by design. Dwarf Fortress moves some of its cost to before you start: it can simulate thousands of years of a world's history while generating it, which takes a long time and leaves you with a very large save.

## 6. What a player can follow (6:05 to 6:44)

**Picture.** Callback: Dwarf Fortress's flooded dining hall, then RimWorld's list of thoughts.

**Frame.** count kind=set ids=data-overlays,causal-tooltips,agent-inspection

**Voice.** The third ceiling was the last episode. On the dataset's scores, the mechanics that produce the most variety are the hardest to read, so every system a game connects to the others needs a way to be understood: an overlay, a tooltip, an inspection panel. Each one costs design time and screen space.{{assert:rho_legibility_emergence_potential < -0.2}}

## 7. Same inputs, same world (6:44 to 8:04)

**Picture.** Factorio: a belt of iron plates, items moving in exact single file. The camera pulls back to two players' screens side by side, the same factory, the same item at the same spot on the same belt.

**Frame.** moment panels="cursor:Only inputs cross the network|monitor+monitor:Every machine runs the whole simulation|check-pass:Every machine computes the identical factory"

**Frame.** count at="That requirement has kept learned models out" kind=tally of=technique field=determinism_impact where=in-play

**Voice.** Replays, bug reports from save files, leaderboards, and lockstep multiplayer all depend on the same inputs producing exactly the same world. In lockstep play, every player's machine runs the whole simulation and only inputs cross the network. Factorio is built around it. Its items move in exact, discrete steps, a belt carrying 15, 30, 45, or 60 items a second depending on its tier, so every machine in a multiplayer game computes the identical factory [@src-factoriowiki-2026-transport-belt-physics].

**Voice.** That requirement has kept learned models out of the parts of games that decide what happens. The dataset sorts every AI technique that can run during play by what it does to reproducibility. Some break it outright. More can be made reproducible by fixing a seed, caching an answer, or logging what the model said. Episode 10 is about what happens when they meet a game that depends on it.{{assert:n_technique_runtime_breaks < n_technique_runtime_mitigable}}

## 8. Minds made of formulas (8:04 to 10:07)

**Picture.** RollerCoaster Tycoon: hundreds of guests on the paths. One is clicked; a thought reads that a ride is too intense. Then RimWorld: one colonist's thought list, long and specific.

**Frame.** formula result="utility-action-selection:The next action" terms="needs-decay:What she needs,×refrigerator:What each option offers"

**Frame.** compare at="Designers worked within it in a few ways" a="Many shallow guests" a_items="crowd:RollerCoaster Tycoon" b="A few deep characters" b_items="memories-thoughts:RimWorld,injury-body-model:Dwarf Fortress"

**Voice.** The fifth ceiling is believability. Many simulated people choose by scoring their options against their needs and picking the best. It's cheap and readable, and it fails in recognizable ways: two options score the same and a character flips between them, or one need drowns out everything else. Designers worked within it in a few ways. RollerCoaster Tycoon made many shallow guests, each with some money, a taste for intensity, a tolerance for nausea, and a stream of one-line thoughts [@src-openrct2-2026-guest-behaviour]. RimWorld and Dwarf Fortress made a few deep characters with long memories and bodies that remember every wound.

**Picture.** Creatures (1996): a Norn being tickled, then slapped; a diagram of its brain, chemistry, and genome.

**Frame.** anatomy game=creatures parts=core

**Voice.** Creatures, in 1996, tried to grow minds instead. Each Norn had a neural network for a brain, a simulated body chemistry, and a genome that built both, and it learned from what reduced its drives. Players bred and traded mutants online. Learning creatures appear in {{derived:creature-learning.prevalence}} catalog games.{{assert:derived.creature-learning.prevalence <= 5}}

**Picture.** Figures from the Generative Agents paper: the small town, agents' speech bubbles, a diagram of word spreading from one agent to many.

**Frame.** count kind=units total=25 on=13 also=5 labels="heard the news,came" from=generative-agents-smallville:gossip-propagation

**Voice.** In 2023 a research team put 25 language-model agents in a town modeled on The Sims. Each kept a written memory, reflected on it, and planned its day. Told that one of them wanted to throw a Valentine's Day party, the town spread the news by talking: over two game days, 13 of the 25 heard and five came. Running it cost thousands of dollars in API credits [@src-park-2023-generative-agents]. They held conversations no Sim can hold. Every choice they make costs money while you play, and none of them can be replayed from the inputs.

## 9. Lifting one ceiling spends another (10:07 to 10:46)

**Picture.** The five ceiling tiles again. As each example is named, one tile lifts and another lowers.

**Frame.** count kind=set ids=ceiling-authoring,ceiling-compute,ceiling-legibility,ceiling-determinism,ceiling-believability

**Voice.** Smart objects let The Sims add behavior without touching its people, and every behavior became something to author. Individual cars let Cities: Skylines show you a jam, and cost compute and a traffic model players couldn't read. Generative Agents bought conversation with inference and reproducibility. Infinite Craft kept determinism by caching every answer.

## 10. Close (10:46 to 11:44)

**Picture.** A board with the five ceilings as columns and recent techniques as cards being pinned under them. Most cards pile up under authoring and rendering; one card, neural upscaling, is marked shipped everywhere.

**Voice.** The five ceilings aren't moving together. Authoring cost is giving way fastest: generated assets, learned motion, and language characters have all shipped.{{assert:field.text-to-3d-assets.maturity == shipped-niche}}{{assert:field.learned-motion-synthesis.maturity == shipped-niche}} Compute is giving way mostly in graphics. Neural upscaling and frame generation are the one AI technique in the dataset that's standard in shipped games, and they never touch what the simulation decides.{{assert:n_technique_shipped_mainstream == 1}}{{assert:field.neural-rendering-shaders.determinism_impact == preserves}} Learned replacements for physics, fluids, and weather are still prototypes and research.{{assert:field.subspace-neural-physics.maturity == prototype}}{{assert:field.graph-network-simulators.maturity == research}}

**Voice.** Next episode: what AI has shipped in games so far, starting in 2019 with a text adventure that had no rules at all, just a language model continuing the story.

**On screen.** The dataset, the paper, and every source: simgrammar.com
