# Episode 4. Why deep systems are hard to read

Target runtime about 12 minutes: about 1,210 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 5. Footage: Dwarf Fortress, RimWorld, Oxygen Not Included, Cities: Skylines, SimCity (1989) through Micropolis, Victoria 3, RollerCoaster Tycoon, EVE Online, all captured by us; Conway's Game of Life in an open-source simulator. Publisher video policies are tracked in `media/rights.yaml` and must be checked before release. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** A flooded fortress in Dwarf Fortress shows a chain of causes the player never sees. Mechanics that produce more variety are rated harder to read and harder to balance, and designers answered with mechanics that simulate nothing and only show what the others hold.

## 1. Cold open (0:00 to 0:45)

**Picture.** Dwarf Fortress, side view of a fortress three levels deep. A miner cuts the last tile of a tunnel to the river. Water spills down the tunnel, fills a cistern, and keeps coming: down a stairwell, across the dining hall, into a row of bedrooms. Depth numbers flicker on the flooded tiles, one to seven.

**Frame.** toysim sim=flow from=dwarf-fortress:fluid-gas-simulation levels=7

**Voice.** The plan was a cistern under the dining hall: dig to the river, build a floodgate, then cut the last tile. The miner cut the last tile first. Water in Dwarf Fortress moves tile by tile, one to seven levels deep, downhill through every opening it can find. By the time you wall off the tunnel, the bedrooms are full and several dwarves have drowned in their beds.

## 2. Title (0:45 to 0:55)

**Picture.** Title card over a still of the flooded dining hall.

**On screen.** Why deep systems are hard to read. Episode 4.

## 3. The chain you cannot see (0:55 to 2:12)

**Picture.** The water pumped out, dwarves back at work. A dwarf's portrait with a meter beside it that the game never shows, labelled "stress (hidden)". The meter creeps up. Months pass on a calendar in the corner. The metalsmith throws a tantrum and smashes a table while the other dwarves watch.

**Frame.** chain nodes="grave:Grief,stress-accumulation:Stress the game never shows,mood-breakdown:A tantrum,memories-thoughts:New unhappy memories" verbs="adds to,past a threshold,for everyone who watches" loops=R from=dwarf-fortress

**Voice.** The fortress looks fine afterward. What you can't see is a number each survivor carries: a stress value that runs from minus a million to plus a million. Grief adds to it, scaled by personality, and strong memories keep adding to it whenever they come back. Past ten thousand, twenty-five thousand, and fifty thousand, dwarves start throwing tantrums, falling into depression, and wandering off [@src-dfwiki-2026-stress].

**Voice.** Months later the metalsmith smashes a table in the dining hall, and everyone who watches gets a new unhappy memory. One of them lost a brother in the flood. By spring the fortress can't feed itself.

**Picture.** A later game in the same world. Legends mode: the fortress listed as a site, the flood among its events. An adventurer walks into the dry, empty hall.

**Frame.** chain nodes="water:Water flows downhill,grave:Grief,stress-accumulation:Stress,mood-breakdown:Tantrums" verbs="drowns,adds,past a threshold,spread it" loops=R from=dwarf-fortress

**Voice.** Every link in that chain is simple. Water flows downhill. Grief adds stress. Tantrums spread it. The chain is hard to see because it runs through months of game time and a number the game never puts on screen. 

## 4. Two scores (2:12 to 3:34)

**Picture.** Two five-step scales slide in, each step labelled with its anchor text: legibility and emergence potential. Three mechanic cards drop onto them: stress, simulated history, the pause button.

**Frame.** scale ids=stress-accumulation,history-generation,variable-speed fields=legibility,emergence_potential

**Voice.** Two scores matter here. Legibility asks how easily a player builds an accurate picture of the mechanic from play: a 2 means you need a wiki, and a 5 means it's clear at a glance. Emergence potential asks how much unscripted variety the mechanic produces when it's connected to others: a 4 means it often sets off chains of consequences across systems.

**Voice.** Dwarf Fortress's stress system scores 3 and 4.{{assert:field.stress-accumulation.legibility == 3}}{{assert:field.stress-accumulation.emergence_potential == 4}} Its simulated history, which can run a world forward thousands of years before you arrive, scores 2 and 5.{{assert:field.history-generation.legibility == 2}}{{assert:field.history-generation.emergence_potential == 5}} The pause button scores 5 and 1.{{assert:field.variable-speed.legibility == 5}}{{assert:field.variable-speed.emergence_potential == 1}}

**Voice.** A language model assigned these scores against written anchors, and independent second ratings now cover {{stat:n_scores_independently_rated}} of them.{{assert:n_scores_independently_rated > 0}} They are judgments about design, read from what developers and players have written about each mechanic, and they aren't measurements of players.

## 5. The slope (3:34 to 4:30)

**Picture.** The scatter of every mechanic, legibility across, emergence up, each dot sized by how many games use it. The dots settle into a cloud that leans down to the right.

**Voice.** Plot all {{stat:n_mechanic}} mechanics and the cloud leans. The more variety a mechanic produces, the harder it's rated to read. The {{stat:n_mechanics_emergence_1}} mechanics at the bottom of the emergence scale average {{stat:mean_legibility_emergence_1}} for legibility. The {{stat:n_mechanics_emergence_4plus}} at 4 or 5 average {{stat:mean_legibility_emergence_4plus}}.{{assert:mean_legibility_emergence_1 > mean_legibility_emergence_4plus}}{{assert:rho_legibility_emergence_potential < -0.2}}

**Picture.** The interface mechanics, overlays, tooltips, speed controls, light up in the bottom right corner, then fade out of the plot. The cloud still leans.

**Voice.** Part of that lean is built in: overlays and pause buttons generate nothing, and they're easy to read because reading them is their job. Take them out and the lean weakens but keeps its direction.{{assert:rho_legibility_emergence_potential_excl_interface < 0}}

## 6. Rules you can read (4:30 to 5:34)

**Picture.** Conway's Game of Life in a simulator. The rule written across the top: born with 3 neighbors, survives with 2 or 3. A five-cell R-pentomino starts to grow and doesn't stop; a generation counter climbs past a thousand.

**Frame.** toysim sim=life from=game-of-life:turn-structure gens=1103

**Voice.** Conway's Game of Life has one rule, and it fits on a line. A dead cell with three live neighbors comes alive. A live cell with two or three survives. That's all of it, and you still can't read a pattern's future from it. This five-cell shape keeps changing for 1,103 generations before it settles.

**Picture.** EVE Online: a market window with a price history chart, then a fleet battle, wrecks drifting.

**Frame.** chain nodes="player-driven-market:Players make and sell nearly every ship,ship:Fleets fight,loss-on-death:Destroyed ships are gone for good" verbs="buy,lose" loops=R from=eve-online

**Voice.** EVE Online is the same at the scale of a society. Players make nearly every ship, destroyed ships are gone for good, and every price history is public. The rules of one trade are simple. The economy those trades add up to was complicated enough that the developer hired an economist in 2007 to watch it.

## 7. Harder to balance (5:34 to 6:32)

**Picture.** RimWorld. A colony with gold statues and fine furniture; a raid letter; an enormous raid. Then the raid points formula builds on screen term by term.

**Frame.** formula result="adaptive-threat-scaling:Raid points" terms="(coins:Wealth points,+person:Colonist points),×dial:Threat scale,×dial:Starting factor,×dial:Adaptation factor" from=rimworld:adaptive-threat-scaling

**Frame.** scale at="The mechanic scores 2 for legibility" ids=adaptive-threat-scaling fields=legibility,tuning_difficulty

**Voice.** Mechanics that produce more of it are rated harder to balance, and that's the strongest relationship among all six scales.{{assert:rho_emergence_potential_tuning_difficulty > 0.5}}

**On screen.** Raid points = (wealth points + colonist points) × threat scale × starting factor × adaptation factor. Capped at 10,000.

**Voice.** Before each raid, RimWorld computes a budget of raid points from your colony's wealth and your colonists, then multiplies it by a few factors, one of which drops after colonists die [@src-rimworldwiki-2026-raid-points]. None of that is on screen. Players who look it up on the wiki learn to keep their wealth down: they skip the statues and the fine furniture so the raids stay small. The mechanic scores 2 for legibility and 4 for tuning difficulty.{{assert:field.adaptive-threat-scaling.legibility == 2}}{{assert:field.adaptive-threat-scaling.tuning_difficulty == 4}}

## 8. Expensive and hidden (6:32 to 7:53)

**Picture.** Oxygen Not Included. A base in normal view, then the oxygen overlay washes over it: pockets of carbon dioxide where the duplicants are about to walk. Then the temperature overlay.

**Frame.** compare a="Without overlays" a_items="tile-cell:Tinted tiles" b="With an overlay" b_items="map-overlay:One field recoloured" from=oxygen-not-included:data-overlays

**Voice.** Legibility also falls as compute cost rises.{{assert:rho_legibility_compute_cost < 0}} The expensive mechanics tend to be fields and crowds, and you can't watch a field the way you watch one colonist. In Oxygen Not Included every tile of the asteroid holds one element with a mass and a temperature, and gases spread and sort themselves cell by cell. Without overlays, all of that is tinted tiles.

**Picture.** SimCity (1989), the traffic map: a heat map of density, no cars anywhere. Cut to Cities: Skylines, a jam forming at one intersection, cars stacked in one lane while the lane beside it is empty.

**Frame.** compare a="SimCity, 1989" a_items="map-overlay:A traffic number on the map" b="Cities: Skylines" b_items="car:Every vehicle simulated" from=cities-skylines:traffic-congestion

**Frame.** scale at="Traffic congestion scores 2" field=traffic-congestion.legibility

**Voice.** The original SimCity has no cars. A zone looking for a destination takes a random walk of up to 30 steps along the roads, and each success adds to a traffic number on the map [@src-hopkins-2008-micropolis]. Cities: Skylines simulates every vehicle, so you can watch a jam form. Players could see the jams and still not understand them. Cars crowd into one lane while the next one sits empty, and stuck cars disappear by default, which hides the real problem. Traffic congestion scores 2 for legibility.{{assert:field.traffic-congestion.legibility == 2}}

## 9. Mechanics that own nothing (7:53 to 9:35)

**Picture.** A montage of interface: SimCity's land value map, a Victoria 3 tooltip opening a second tooltip inside it, a RollerCoaster Tycoon guest window with a thought reading that a ride was too intense, Dwarf Fortress Legends scrolling.

**Frame.** count kind=tiles family=information-legibility lit=none dates

**Voice.** Designers answered with a family of mechanics that simulate nothing. They read state other mechanics own, and they show it. The dataset has {{stat:n_mechanics_family_information_legibility}} of them, and they're old. Hamurabi's steward reported the harvest in 1968. Lemonade Stand gave you a weather report every morning in 1973.{{assert:derived.advisors.earliest_game == hamurabi}}{{assert:derived.forecasting.earliest_game == lemonade-stand}}

**Voice.** Overlays recolor the map by one hidden field. Causal tooltips let you hover a number and see the named terms that add up to it, and hover the terms inside that list in turn; Paradox's strategy games are built on them [@src-pcgamesn-2022-victoria-3-nested-tooltips]. Inspection panels open one agent's head. RollerCoaster Tycoon gave every guest a stream of thoughts, so you could click a guest, read that the drinks cost too much, and change the price. Chronicles record what happened: Dwarf Fortress's Legends archive can run to about a gigabyte for a long history [@src-dfwiki-2026-legends].

**Voice.** Each of these fails in its own way. A color ramp that rescales itself makes a small problem look as red as a big one. Tooltips grow into walls of numbers late in a game. An inspection panel that shows what a character wants but not how it decided still leaves its behavior looking random.

## 10. Choosing a point (9:35 to 10:42)

**Picture.** Split screen: Dwarf Fortress on the left, RimWorld on the right. The same event on each side: a character breaking down. On the left, a dwarf storming about with no explanation on screen. On the right, a mood bar with its thresholds and a list of thoughts.

**Frame.** compare games=dwarf-fortress,rimworld show=own

**Frame.** compare at="Oxygen Not Included puts much of its depth" a="Oxygen Not Included" a_items="heat-transfer:One rule for heat,map-overlay:Overlays to read it" b="Victoria 3" b_items="causal-tooltips:The explanation inside the numbers"

**Voice.** Dwarf Fortress was built to break each system into parts and base each one on something real [@src-adams-2015-df-simulation-principles]. It has more mechanics than any other game in the catalog, {{stat:max_mechanics_per_game}}.{{assert:most_mechanics_game == Dwarf Fortress}} The stress numbers at the start of this episode come from the community wiki, because the game doesn't show them. RimWorld took several of the same systems and chose them for how readable their results are. Its stress is a mood bar with visible break lines, and every thought has a number and a timer.

**Voice.** Oxygen Not Included puts much of its depth in one rule for heat, applied to every cell, and gives you overlays to read the result. Victoria 3 puts its explanation inside the numbers.

## 11. Close (10:42 to 11:38)

**Picture.** A blank sheet with a chain of boxes, each labelled "visible", "findable", or "hidden".

**Frame.** chain nodes="eye-open:Visible,magnifier:Findable,eye-closed:Hidden"

**Voice.** Try this with a disaster from your own games. Write the chain from the first event to the collapse, one link per line, and mark each link visible, findable, or hidden. For the first hidden link, design the overlay, tooltip, or alert that would have shown it.

**Voice.** Explaining a game from its own logs needs tools that already exist, and explanation is still the rarest thing any AI technique in this dataset does to a mechanic.{{assert:rarest_effect == Explains}} Next episode: the five ceilings that have shaped simulation games, starting with a refrigerator in The Sims.

**On screen.** Every mechanic and how hard it is to read: simgrammar.com
