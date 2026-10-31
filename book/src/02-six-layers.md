# Chapter 2. Six layers

Zone a block of houses in [[simcity-1989|SimCity]], run a power line to it, and for a while nothing happens. Then small houses appear, then more, and then the block stops growing and the houses nearest the industrial strip begin to empty. The game explains itself with maps. Open the crime map and a red patch sits over the empty houses; open land value and the same area is dark. Crime in SimCity is computed for each cell as 128 minus land value plus population density minus the police effect, held between 0 and 250, and land value falls with distance from the city's center and with the pollution your industry writes into a map of its own [@src-hopkins-2008-micropolis]. The game recomputes these maps in passes, and a zone grows when its local score plus a city-wide demand valve passes a random test.

The six rules in that paragraph do six different jobs. The maps, the zones, and the treasury hold the city's state. The crime formula and the spread of pollution change it. Pollution lowering land value connects one system to another. Painting zones and setting the tax rate take in what the player wants. The maps on screen show the player what the simulation is doing. Disasters and the year-end budget decide when the player has to pay attention and what a mistake costs.

This book proposes six jobs that every simulation game does, and it files each mechanic under the job it mainly does. The dataset does not tag layers, so the six are a way of reading the catalog that its data does not test:

1. **Substrate:** what exists, and how it is stored.
2. **Dynamics:** the rules that change it.
3. **Coupling:** where one system reads or writes another's state.
4. **Control:** how the player's intent gets in.
5. **Legibility:** how the state gets out to the player.
6. **Pacing and stakes:** when the player must look, and what can be lost.

A game's character comes from which layers it spends on.

## Substrate: what exists

A simulation has to store its world somehow, and the choice fixes what the game can afford. Aggregate stocks, such as a treasury or a population count, are cheap and faceless. Individual agents, such as a colonist with needs, are expensive and legible: the player can follow one. Fields on a grid, such as pollution or temperature, cost in proportion to the map's area. Networks of roads, pipes, or friendships cost in proportion to their links. Continuous bodies, such as a wing or a chassis, cost in proportion to contacts and how small the time step is. Each mechanic record names the kinds of state it holds, and a mechanic can hold more than one.

{{table:mechanics-by-substrate}}

The 1989 SimCity stores its citizens as numbers in map cells. [[simcity-2013|SimCity (2013)]] replaced the statistical maps with its GlassBox engine, in which agents carry workers, power, water, and goods between buildings, so that a traffic jam is the visible sum of commuting agents [@src-cifaldi-2012-glassbox-engine]. Players could now follow a single citizen home; chapter 5 describes what they found. The table's learned-model row holds combination discovery, creature learning, generated content, and natural-language interaction. Natural-language interaction and combination discovery are both older than language models. [[little-computer-people|Little Computer People]] matched typed requests such as "Please play piano" against a keyword vocabulary in 1985, and its resident could refuse when sad or sick; [[noita|Noita]]'s two secret recipes are fixed by the world seed. [[infinite-craft|Infinite Craft]] hands the naming to a language model (chapter 8). Creature learning starts with the trick training of [[petz|Dogz]] in 1995 (chapter 3) and grows into the neural networks of Creatures (chapter 6), and generated content comes from AI Dungeon (chapter 7).{{assert:derived.creature-learning.earliest_game == petz}}

## Dynamics: how it changes

Rules that change state form loops. A reinforcing loop amplifies itself: more citizens pay more taxes, which build more services, which attract more citizens. A balancing loop resists change: more traffic lowers land value, which slows growth, which eases traffic. Each mechanic record names its dominant polarity. Of the {{stat:n_mechanic}} mechanics, {{stat:n_mechanics_feedback_balancing}} are mainly balancing, {{stat:n_mechanics_feedback_reinforcing}} mainly reinforcing, and {{stat:n_mechanics_feedback_both}} run both ways depending on state. The remaining {{stat:n_mechanics_feedback_none}} have no loop of their own: pause buttons, overlays, and the other controls and displays that sit on top of the simulation.{{assert:n_mechanics_feedback_none > n_mechanics_feedback_balancing}}

[[factorio|Factorio]] pairs the two kinds on purpose. Production is the reinforcing loop: more machines make more science packs, research unlocks better machines, and the factory grows. Pollution is the balancing one. Machines emit pollution into chunks of 32 by 32 tiles; a chunk holding more than 15 units passes 2 percent of it to each neighbor every 64 ticks; enemy nests that absorb it send attack groups, and an evolution factor that rises with time, total pollution, and destroyed nests unlocks larger enemies [@src-factoriowiki-2026-pollution; @src-factoriowiki-2026-enemies]. Difficulty in a game like this is the relative strength of the two loops.

A reinforcing loop can also run downhill. A mood break leaves bad memories in the agents who witness it, which lowers their mood and raises their own chance of breaking, so in a colony sim one bad raid can start a slide that ends the colony.

Each record also names the mathematics behind its rule. System dynamics, stocks that rise and fall through flows, is the most common basis, at {{stat:n_mechanics_math_system_dynamics}} mechanics; needs that decay are one, and so is a treasury.{{assert:n_mechanics_math_system_dynamics > n_mechanics_math_optimization}}{{assert:n_mechanics_math_optimization > n_mechanics_math_queueing}} Cellular automata, grids in which each cell updates from its neighbours, are among the bases of {{stat:n_mechanics_math_cellular_automata}} mechanics; they include the crime, pollution, land value, and zoning behind this chapter's opening maps, and fire spread.

Queueing underlies {{stat:n_mechanics_math_queueing}} mechanics. Service queues are the plainest case: a ride, a clinic room, or a checkout serves at a fixed rate, arriving agents join if the line is short enough for their tolerance, and their needs keep decaying while they wait. In [[theme-hospital|Theme Hospital]] and [[two-point-hospital|Two Point Hospital]], patients' health keeps falling in the queue outside a room, so long queues end in departures and deaths that lower the hospital's reputation.

Only {{stat:n_mechanics_math_epidemiology}} use epidemiology: contagion, and gossip that spreads between agents.{{assert:n_mechanics_math_epidemiology <= 3}} The contagion record is built on Kermack and McKendrick's 1927 compartment model, in which hosts move from susceptible to infected to recovered or dead, and an epidemic happens only above a threshold set by the rates of infection and recovery [@src-kermack-1927-epidemic-theory]. [[plague-inc|Plague Inc.]] spreads a pathogen the player evolves from country to country, and Theme Hospital's contagious patients infect others inside the building. The record also cites a disease that spread beyond the place it was designed for: World of Warcraft's Corrupted Blood debuff in 2005, which passed between players by proximity and escaped its raid through pets and fast travel into the cities [@src-lofgren-2007-corrupted-blood].

## Coupling: how systems touch

A game can have many systems and still feel thin if they never touch. Systems couple through shared stocks, shared space, and shared agents.

Shared stocks are the simplest. Factorio's power grid connects every machine, and when generation falls short the grid shares power evenly, so every machine in the factory slows by the same proportion, the shortage that opens chapter 4 [@src-factoriowiki-2026-electric-system]. Shared space works through neighbors: in SimCity, industry lowers the land value of the houses beside it. Shared agents work through bodies and minds: in RimWorld the same cook hauls, eats, grieves, and fights, so a death in a raid reaches the kitchen.

[[oxygen-not-included|Oxygen Not Included]] couples much of its world through one rule for heat. Every tile in its asteroid holds one element with a mass and a temperature, and every 0.2 seconds each tile exchanges heat with its neighbors by conduction [@src-oxygennotincludedwiki-2026-thermal-conductivity]. Insulation, melting, boiling, and machines that overheat all follow from that rule rather than from scripts written for each building. Machines also emit what they do not use: a natural gas generator makes 800 watts and, with them, polluted water and carbon dioxide [@src-oniwiki-2026-natural-gas-generator]. The long game is closing those loops so that one machine's waste becomes another's input.

[[dwarf-fortress|Dwarf Fortress]] is the catalog's largest decomposition, at {{derived:dwarf-fortress.mechanic_count}} mechanics,{{assert:game_most_mechanics == dwarf-fortress}} and its parts are coupled tightly. A dwarf seized by a strange mood takes over a workshop to make a named artifact and goes insane if the materials are missing, which turns the production system into a source of stories.

The records also link mechanics to one another by type. There are {{count:edge:synergy}} links where one mechanic makes another work better, and {{count:edge:requires}} links where one cannot run without another: loans and taxation need a treasury, hauling needs pathfinding, traffic needs roads, and romance needs relationship values to act on. A third type, tension, marks pairs that pull against each other (chapter 9). The note on one such link names the partner of needs that decay in The Sims: objects that advertise which need they restore turn decaying needs into autonomous daily behavior, the design chapter 6 opens with.

[[democracy-4|Democracy 4]] makes coupling the whole game.{{assert:derived.policy-influence-network.prevalence == 1}} A country is one visible causal graph. Policies in seven areas, set as sliders, statistics such as crime and air quality, situations, and voter groups are its nodes; weighted links carry effects between them, and every node is recomputed each turn within a fixed range. Its designer describes the engine as a homebrew neural network in which voters, policies, ministers, and events are neurons, and Democracy 4 added income values allowed to exceed the usual bound, because percentage effects on a scale from 0 to 1 had given wealthy voters more than poor ones [@src-harris-2020-democracy4-fixed-income]. The record's failure modes are coupling problems: dense graphs with small weights make most policies feel inert while a few dominate, and long delays without visible pending effects make players blame the wrong policy.

## Control: how intent enters

The player can act directly through an avatar or a unit, place and zone, set parameters such as a tax rate, issue orders that agents pick up, write programs, or speak. Each step away from direct action widens what this book calls the control gap: the designed distance between what the player wants and what happens. A gap too narrow and the game is a toy; too wide and the player is a spectator.

{{table:games-by-agency}}

[[the-sims|The Sims]] sets its gap deliberately. Sims with free will choose their own actions among what the objects around them offer, but paying bills, finding a job, exercising, and having children need explicit commands, so the player alternates between architect and caretaker [@src-wikipedia-the-sims]. [[spacechem|SpaceChem]] sits at the other extreme. The player programs two mechanical arms in a reactor ten cells wide and eight tall to grab, bond, and rotate atoms into molecules; execution is deterministic and visible, so a program either meets its quota or collides, and a finished solution is plotted against every other player's on histograms of cycles, reactors, and instructions [@src-wikipedia-spacechem].

Programs sit at the far end of the gap, and the catalog records how games ration them. In [[screeps|Screeps]] the player's JavaScript is the only input to a persistent world: the server runs it once per tick for every colony, including the colonies of players who are offline, and computation is the scarce resource, with a limit of 20 CPU per tick for an account without CPU Unlock and a bucket that banks up to 10,000 unused [@src-screeps-2026-docs-cpu-limit]. The Farmer Was Replaced meters its programs in simulated ticks instead: literals and assignment are free, and arithmetic costs a tick [@src-tfwrwiki-2026-operation-costs]. [[autonauts|Autonauts]] lets the player program by example. A bot watches the player perform a task, records it as blocks in a visual language, and repeats it inside the loops the player adds, up to an instruction limit set by the bot's head, from 12 to 32 [@src-autonautswiki-2026-bots].

The records also name the role each game gives the player: {{stat:n_player_roles}} roles are in use, from inhabitant and owner to mayor, ruler, engineer, and caretaker, and {{stat:n_games_role_god}} games make the player a god.{{assert:n_player_roles >= 10}} A god works mainly through the world. In [[populous|Populous]] the player raises and lowers land so that followers can build, houses produce followers, followers produce mana, and mana pays for earthquakes, swamps, volcanoes, and floods against a rival deity's people, so shaping the land is also running the economy [@src-wikipedia-populous]. [[simearth|SimEarth]] works through control panels that set rates such as continental drift, reproduction, and mutation, with interventions priced in energy [@src-wikipedia-simearth]. [[from-dust|From Dust]] replaces raising land with carrying it: the player moves sand, water, and lava, water erodes, lava cools into rock, and an island can be reshaped within minutes [@src-wikipedia-from-dust].

Without the divinity, {{stat:n_games_agency_indirect_incentive}} games give the player indirect control, shaping what autonomous agents do through their surroundings, priorities, or incentives.{{assert:n_games_agency_indirect_incentive > n_games_role_god}} In [[simant|SimAnt]] the player's main lever on the colony is the trail field that other ants follow, and rain washes trails away [@src-wikipedia-simant]. [[seaman|Seaman]], a 1999 Dreamcast pet, adds a microphone to its care: the player sets the tank's heat, cleans its water, and supplies food, and talks to a fish with a human face that at first repeats the player's words back as gibberish; about one check per real day keeps it alive [@src-wikipedia-seaman].

## Legibility: how the state gets out

A simulation the player cannot read plays as noise. Simulation games answer with a family of mechanics that own no simulation state at all: overlays, inspectors, tooltips, dashboards, alerts, advisors, forecasts. SimCity's maps are one. RimWorld's itemized thoughts, from chapter 1, are another. Paradox's grand strategy games break each number into nested tooltips of labeled causes, the form chapter 5 describes.

The catalog undercounts this layer. Data overlays are tagged in only {{derived:data-overlays.prevalence}} catalog games, yet the mechanic's own definition names the info views of [[cities-skylines|Cities: Skylines]], and the Cities: Skylines record does not tag them. The dataset's records were written game by game, and interface mechanics were the easiest to leave out.

## Pacing and stakes: when to look and what is lost

The time model sets the basic rhythm: real time with a pause is the most common, ahead of pure real time and turns. Other mechanics shape attention within it.

A crisis countdown announces a future disaster and lets the remaining time structure the play. Temperature in [[frostpunk|Frostpunk]] falls on a schedule toward the Great Storm, which the main scenario must outlast; in [[plague-inc|Plague Inc.]] the world's cure research climbs as a percentage, and the game ends when it completes [@src-wikipedia-frostpunk; @src-wikipedia-plague-inc]. The countdown is core in {{derived:crisis-countdown.core_count}} catalog games.{{assert:derived.crisis-countdown.core_count >= 5}}

A real-time clock ties the game to the calendar. [[tamagotchi|Tamagotchi]], in 1996, aged its pet through life stages in real time, and Animal Crossing follows the console's clock, so shops close at night and holidays arrive on their real dates; players who change the console clock to skip a wait call it time travel [@src-wikipedia-tamagotchi; @src-wikipedia-animal-crossing].{{assert:derived.real-time-clock.earliest_game == tamagotchi}} A daily action budget makes the day itself scarce. [[stardew-valley|Stardew Valley]] gives the farmer 270 energy, charges it for each swing of a tool, and makes the farmer pass out at 2 a.m., which away from home costs a tenth of the farmer's gold, up to 1,000 [@src-stardewvalleywiki-2026-energy].

Stakes come from the failure model. About half of catalog games let the player recover from a setback; fewer restart from scratch, and a smaller group, RimWorld and Dwarf Fortress among them, can collapse in a cascade where one failure causes the next.{{assert:field.dwarf-fortress.failure_model == cascading-collapse}}{{assert:field.rimworld.failure_model == cascading-collapse}}

{{table:games-by-failure}}

The catalog files {{stat:n_games_win_open_sandbox}} games, about half of it, as open sandboxes, with no set end and goals the player chooses, though some add optional ones, such as SimCity's timed scenarios and Factorio's rocket launch, which ends its base game. Of the others, {{stat:n_games_win_scenario_goals}} set scenario goals, {{stat:n_games_win_campaign}} run a campaign, and the rest end on completion, a score, a victory over rivals, or survival for a set time.{{assert:n_games_win_open_sandbox >= 80}}{{assert:n_games_win_open_sandbox > n_games_win_scenario_goals}}

Each game record also says where its stories come from. In {{stat:n_games_narrative_emergent}} games they emerge from the systems, as the cook's did in chapter 1; {{stat:n_games_narrative_none}} have no story to speak of; {{stat:n_games_narrative_hybrid}} mix authored events with emergent ones; {{stat:n_games_narrative_authored}} tell an authored story; and {{stat:n_games_narrative_generative}} generate their stories with a model: AI Dungeon, Suck Up!, Whispers from the Star, and two research sandboxes.{{assert:n_games_narrative_emergent > n_games_narrative_authored}}{{assert:field.ai-dungeon.narrative_mode == generative}}{{assert:field.suck-up.narrative_mode == generative}}{{assert:field.whispers-from-the-star.narrative_mode == generative}}{{assert:field.project-sid.narrative_mode == generative}}{{assert:field.generative-agents-smallville.narrative_mode == generative}}

## Where genres spend

With no layer tags, the closest measure is which families of mechanics a subgenre's games use most, since the book files most families under one layer. The table lists, for each subgenre with enough games, the three families that take the largest share of its games' mechanic uses.

{{viz:layer-profile}}

{{table:subgenre-spend}}

Life sims put about a third of their uses into agents and behavior and about a sixth into social relations.{{assert:top_family_life_sim == agents-behavior}}{{assert:top_family_pct_life_sim >= 30}} Colony sims also lead with agents, but resources and construction come next, because a colony has to feed and house itself.{{assert:top_family_colony_sim == agents-behavior}} Factory games lead with resources and production, followed by the logistics that move it.{{assert:top_family_factory_automation == resources-production}} Programming games lead with control.{{assert:top_family_programming_sim == control-automation}} Vehicle sims lead with progression and goals, ahead of the physics: careers, licenses, and missions are wrapped around the driving and flying.{{assert:top_family_vehicle_sim == progression-goals}} And the AI-native titles lead with social relations, the family where conversation with a language model lands.{{assert:top_family_ai_native == social-relations}}

Business sims are the most concentrated, with about a third of their uses in economy and finance.{{assert:top_family_business_economic_sim == economy-finance}}{{assert:top_family_pct_business_economic_sim > top_family_pct_life_sim}} Job sims also lead with economy, and their next largest share goes to operation and procedure, the family of checklists, surface tools, and repair that chapter 8 finds no technique aimed at.{{assert:top_family_job_sim == economy-finance}} Survival sims lead with resources and split their next shares evenly between the environment and the ways a run can fail.{{assert:top_family_survival_sim == resources-production}}

City builders spread their uses most evenly. No family takes more than about one use in six, and construction, production, and economy take nearly equal shares.{{assert:top_family_pct_city_builder <= 17}}

## Exercise: profile a game by layer

Take the game you decomposed in chapter 1.

1. Assign each of its mechanics to the layer where it does most of its work.
2. Count the mechanics per layer. Note which layer has the most and which has none.
3. For the layer with the most, name one coupling: a place where a mechanic there reads or writes another mechanic's state.
4. For the thinnest layer, add one mechanic from another game in the catalog and describe what changes for the player.

Most of the mechanics in this chapter are old. SimCity's maps date from 1989, Tamagotchi's clock from 1996, and The Sims' objects that advertise what they offer from 2000. Chapter 3 dates every mechanic in the vocabulary by the first catalog game that uses it, and tests how much of the old vocabulary was invented early and how much is simply shared.
