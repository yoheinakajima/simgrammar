## 4. A grammar of simulation games

### 4.1 Six layers

This report proposes six layers as a frame for reading any simulation game, with each mechanic filed under the layer where it does most of its work. The dataset does not tag layers, so the frame organizes the analysis and is not tested by it.

1. **Substrate: what exists.** State is held as aggregate stocks (a treasury, a population count), individual agents (a colonist with needs), fields on a grid (pollution, temperature, land value), networks (roads, pipes, social ties), or continuous bodies (a wing, a chassis). The substrate fixes the cost curve: aggregates are cheap and faceless, agents are expensive and legible, fields scale with map area, continuous physics scales with contacts and timestep. The `substrate` field on every mechanic records this (first table below).
2. **Dynamics: how it changes.** Update rules form feedback loops. Most simulation games pair a reinforcing growth loop (more citizens, more taxes, more buildings) with balancing loops that resist it (congestion, pollution, unrest, raids). On this frame's reading, difficulty is the relative strength of those loops, and a death spiral is a reinforcing loop running in reverse. The `feedback` field records the dominant polarity per mechanic.
3. **Coupling: how subsystems touch.** The frame's hypothesis is that depth comes less from the number of systems than from how many share state. Systems couple through shared stocks (power, money, labor), shared space (a factory lowers neighboring land value), and shared agents (the same colonist hauls, eats, and grieves). [[dwarf-fortress]], where nearly everything touches nearly everything else, is consistent with the hypothesis, and a game with many isolated systems can feel like many small games; the dataset measures neither depth nor coupling. The couplings it does record are judged edges between mechanics, {{count:edge:synergy}} `synergy` and {{count:edge:tension}} `tension`, which one run added in a single pass over the taxonomy against one-line definitions rather than operational criteria (§2.5). They record that run's judgment, and a pair with no tension edge is unmeasured, not known to be compatible.
4. **Control: how intent enters.** The player acts directly (an avatar, a unit), places and zones, sets parameters, issues orders that agents pick up, writes programs, or speaks. Each step away from direct control widens the *control gap*, the designed distance between what the player wants and what happens. Too narrow and the game is a toy; too wide and the player is a spectator (second table below).
5. **Legibility: how state leaves.** Overlays, inspectors, tooltips, advisors, alerts, graphs, chronicles, and forecasts expose hidden state. The frame proposes that this layer is what lets deep simulations ship: [[rimworld]] itemizes every mood modifier, and Paradox games nest tooltips until each number decomposes into causes. Legibility mechanics own no simulation state of their own; they are the interface between coupling and comprehension.
6. **Pacing and stakes: when the player looks and what can be lost.** Time models (pause, speed, turns, wall clock), failure models (soft setbacks, permadeath, cascading collapse), and narrative directors decide when attention is demanded and what a mistake costs (third table below).

{{table:mechanics-by-substrate}}

*Mechanics by the kinds of state they hold (`substrate`). A mechanic can hold more than one kind and is counted once under each, so the unit is a mechanic-substrate pair and the column can sum to more than the {{count:mechanic}} mechanics.*

{{table:games-by-agency}}

*Games by agency model (`agency_model`). A game can combine several ways of acting and is counted once under each, so the unit is a game-agency pair and the column can sum to more than the {{count:game}} games.*

{{table:games-by-time-model}}

*Games by time model (`time_model`). Each game has exactly one, so the unit is a game and the column sums to the {{count:game}} games.*

A compact description of a simulation game is its investment profile across these layers. City builders invest in substrate (fields and networks) and legibility (overlays); colony sims in agents, coupling, and pacing (storytellers); vehicle sims in continuous substrate and direct control; programming games in control alone, with nearly no hidden state. These profiles are a reading of the catalog; the clustering (§5) works from each game's mechanics alone and is told neither the subgenres nor the layers.

The next table is this paper's proposal for how its three frames fit together: for each family of §4.2, the layer where its mechanics mostly work, and the ceilings of §6 that bear on it most. The dataset tags each mechanic's family and tags neither layers nor ceilings, so the table organizes the reading and is not a result. The ceilings are a judgment drawn from §6 and from the family means in its ceilings figure; determinism is a property of techniques (§6.4), so it is listed where a family's mechanics depend on reproducible or shared state.

| Family | Primary layer | Ceilings that bear on it |
|---|---|---|
| {{vocab:mechanic_family:resources-production}} | Dynamics | none in particular |
| {{vocab:mechanic_family:logistics-networks}} | Coupling | compute, legibility |
| {{vocab:mechanic_family:economy-finance}} | Dynamics | none in particular |
| {{vocab:mechanic_family:agents-behavior}} | Dynamics | believability, authoring, compute |
| {{vocab:mechanic_family:social-relations}} | Coupling | believability, authoring, legibility |
| {{vocab:mechanic_family:population-lineage}} | Dynamics | compute, legibility |
| {{vocab:mechanic_family:governance-policy}} | Control | legibility |
| {{vocab:mechanic_family:space-construction}} | Control | authoring |
| {{vocab:mechanic_family:physics-materials}} | Substrate | compute, determinism |
| {{vocab:mechanic_family:environment-ecology}} | Dynamics | compute, legibility |
| {{vocab:mechanic_family:biology-health}} | Dynamics | authoring, believability |
| {{vocab:mechanic_family:time-pacing}} | Pacing and stakes | none in particular |
| {{vocab:mechanic_family:information-legibility}} | Legibility | legibility, as the answer to it |
| {{vocab:mechanic_family:control-automation}} | Control | compute, determinism |
| {{vocab:mechanic_family:progression-goals}} | Pacing and stakes | authoring |
| {{vocab:mechanic_family:risk-failure}} | Pacing and stakes | none in particular |
| {{vocab:mechanic_family:narrative-generation}} | Pacing and stakes | authoring, determinism |
| {{vocab:mechanic_family:world-generation}} | Substrate | compute |
| {{vocab:mechanic_family:multiplayer-persistence}} | Pacing and stakes | determinism, compute |
| {{vocab:mechanic_family:conflict-defense}} | Pacing and stakes | compute, legibility |
| {{vocab:mechanic_family:operation-procedure}} | Control | authoring |

*The paper's proposal, not a tagged field: each mechanic family's primary layer (§4.1) and the ceilings (§6) that bear on it most. Authoring is the authoring-cost ceiling, believability the believability of agents.*

The word legibility does four jobs here, and they differ in what stands behind them. The legibility layer is the job of getting state out to the player; the information-and-legibility family is the mechanics that do that job (§4.2); the legibility ceiling is the limit on how much hidden state a player can follow (§6.3); and the legibility score is one rater's reading of how easily a player forms an accurate model of a single mechanic (§2.3). The family is a tagged field and the score a judged number, while the layer and the ceiling are this paper's frames.

{{viz:layer-profile}}

### 4.2 The families, one at a time

Each family below is described by the state it owns, its canonical mechanics, how it characteristically fails, and what it couples to. Tables list every mechanic in the family with how many catalog games use it and its rubric scores; each mechanic's full analysis (definition, levers, failure modes, dynamics, open questions) is on its wiki page.

#### Resources and production
Owns stocks of goods and the recipes that transform them. [[production-chain]] is the backbone of city builders, factory games, and colony sims alike; [[storage-capacity]], [[spoilage]], and [[byproducts-waste]] decide whether a chain is a puzzle or a ledger. The characteristic failure is the spreadsheet: chains whose only decision is ratio arithmetic. The best implementations make chains spatial ([[conveyor-transport]]) or social (who does the work, and in what mood).
{{table:family-resources-production}}

#### Logistics and networks
Owns movement across space or graphs: roads, belts, pipes, rails, transit lines, service reach. These mechanics turn production into geography, and they are where compute and legibility first bind: [[traffic-congestion]] is the most visible place a city builder can be wrong, and [[walker-service-delivery]] made service coverage legible by putting it on walking bodies. Networks couple to almost everything, so their bugs (pathfinding loops, gridlock) spread to every system they feed.
{{table:family-logistics-networks}}

#### Economy and finance
Owns money, prices, and valuation. Most games use only [[budget-treasury]] and [[taxation]] as a scorekeeping layer; fewer simulate markets with [[supply-demand-pricing]], competitors ([[rival-firms]]), or player-made prices ([[player-driven-market]]). The characteristic failure is the dominant strategy: a price or loan loophole that converts the economy into an exploit, which is why economies are the first target for automated balancing (§9).
{{table:family-economy-finance}}

#### Agents and behavior
Owns individual minds: needs, utilities, moods, memories, skills, schedules. [[needs-decay]] plus [[utility-action-selection]] is the standard architecture since [[the-sims]]; [[smart-objects]] moved behavior knowledge into the world so new objects bring new behaviors. Its variety is paid for in animations, thoughts, and dialogue, which is why it is among the families most exposed to language-model techniques (§8).
{{table:family-agents-behavior}}

#### Social relations
Owns ties between agents: relationship values, opinion modifiers, reputation, factions, gossip, romance, and conversation. Rule-based social systems are cheap but read as formulaic; [[social-exchanges]] in [[prom-week]] and [[versu]] showed richer social logic is possible at high authoring cost, and [[natural-language-interaction]] opened conversation as an input. The characteristic failure is the visible formula: players learn that one compliment always adds a fixed amount.
{{table:family-social-relations}}

#### Population and lineage
Owns birth, death, migration, inheritance, and structure. [[immigration-attractiveness]] is the city builder's growth engine; [[population-strata]] turns growth into progression; [[trait-inheritance]] and [[dynasty-succession]] stretch play across generations. These mechanics define the time horizon of a game more than its time model does.
{{table:family-population-lineage}}

#### Governance and policy
Owns rules about rules: policies, laws, elections, interest groups, satisfaction, unrest. Policy menus ([[policy-toggles]]) are universal; [[policy-influence-network]] in [[democracy-4]] made the causal web itself the interface; [[player-legislation]] in [[eco]] and [[a-tale-in-the-desert]] let players write rules for each other. The failure is the menu: a fixed list of authored options that no player can extend.
{{table:family-governance-policy}}

#### Space and construction
Owns layout: zoning, placement, adjacency, rooms, structure, terrain, and the scoring of player-built designs. [[zoning]] is indirect construction; [[free-placement]] is direct; [[procedural-build-assist]] sits between them, letting rough gestures produce detailed structure. [[design-performance-rating]] closes the build-test loop in coaster, bridge, and machine builders.
{{table:family-space-construction}}

#### Physics and materials
Owns continuous dynamics: rigid bodies, vehicles, flight, orbits, fluids, heat, deformation, destruction, material interactions. These are, on average, the most compute-bound mechanics in the taxonomy,{{assert:top_compute_family == Physics & materials}} and their legibility depends on how closely they match the physical intuitions players bring. The failure is the uncanny edge: a physics model accurate enough to invite intuition but wrong in the cases players probe.
{{table:family-physics-materials}}

#### Environment and ecology
Owns the world's own processes: weather, seasons, food webs, habitats, pollution, fire, contagion, water, climate. Environmental mechanics are where simulation games most often lean on real science ([[contagion]] follows compartment models; [[food-web]] follows predator-prey dynamics) and where calibrated learned models can substitute for hand-tuned approximations.
{{table:family-environment-ecology}}

#### Biology and health
Owns bodies: survival meters, injuries, diagnosis, creature care, husbandry. [[survival-meters]] define a subgenre; [[injury-body-model]] tracks wounds per body part in colony sims; [[creature-care]] is the oldest bond between player and simulated being.
{{table:family-biology-health}}

#### Time and pacing
Owns the clock. [[variable-speed]] is near-universal in real-time management games; [[real-time-clock]] ties play to the calendar; [[daily-action-budget]] makes days a scarce resource; [[crisis-countdown]] turns the future into a deadline. Time mechanics are where multiplayer and persistence constraints bite: a shared world cannot pause.
{{table:family-time-pacing}}

#### Information and legibility
Owns nothing in the simulation and decides whether anyone can understand it. Overlays, inspectors, tooltips, dashboards, alerts, advisors, forecasts, fog of war, scouting, and comparative histograms. This family is the counterweight to emergence and the most direct beneficiary of language models that can read state and explain it (§8).
{{table:family-information-legibility}}

#### Control and automation
Owns the channel from intent to action: avatars, unit commands, designations, programming, circuits, blueprints, delegation, god powers, and embodied skill. The history of the family is a steady move away from direct control toward specification: from clicking each unit to drawing zones, from wiring logic to writing code, and now toward stating intent in language.
{{table:family-control-automation}}

#### Progression and goals
Owns what the player is working toward: tech trees, milestones, scenarios, career ladders, collections. Simulation games are often sandbox-first, and these mechanics supply direction without scripting outcomes.
{{table:family-progression-goals}}

#### Risk and failure
Owns what goes wrong: disasters, wear, permadeath, threat scaling, crime. Failure mechanics are the main source of stakes, and [[adaptive-threat-scaling]] is the genre's most consequential balancing decision: whether growth makes the game easier or harder.
{{table:family-risk-failure}}

#### Narrative and generation
Owns what events happen and how they are told: storytellers, dilemma cards, triggered event chains, requests, chronicles, and runtime-generated content. Emergent narrative needs both a director (what happens) and a chronicle (what it meant). This family is bounded by writing budgets, which is why it is a primary target for generative techniques and the place where their risks (inconsistency, tone, disclosure) are most visible.
{{table:family-narrative-generation}}

#### World generation
Owns initial conditions: terrain, simulated history, characters. [[history-generation]] in [[dwarf-fortress]] simulates centuries of events before play, so the world has a past before the player arrives.
{{table:family-world-generation}}

#### Multiplayer and persistence
Owns other people: persistent worlds, organizations, content sharing, modding, asynchronous regions. These mechanics turn a simulation into a society of players, and they impose the strictest determinism and fairness constraints on everything else.
{{table:family-multiplayer-persistence}}

#### Conflict and defense
Owns violence as a system: raids and operational military simulation. In most simulation games conflict is a stress test of the economy rather than the point.
{{table:family-conflict-defense}}

#### Operation and procedure
Owns hands-on work: checklists, tool use on surfaces, diagnosis and repair, rule-checking. The job-sim boom of the 2010s and 2020s made procedure itself pleasurable when tool feedback is good.
{{table:family-operation-procedure}}
