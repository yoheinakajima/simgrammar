# Episode 2. Where the parts came from

Target runtime about 12 minutes: about 1,270 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 3. Footage: Hamurabi (a period BASIC listing run in an emulator), SimCity (1989), M.U.L.E., Little Computer People, Dwarf Fortress, Factorio, The Oregon Trail, Minecraft, Stardew Valley, Harvest Moon; publisher video policies are tracked in `media/rights.yaml` and must be checked before release. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** Hamurabi, from 1968, already used parts that games still use. Most of the vocabulary was in a catalog game by 2000, a test against chance shows how much of that comes from parts being widely shared, and recent games are built mostly from old parts.

## 1. Cold open (0:00 to 0:40)

**Picture.** A teletype printing on paper. A steward's yearly report scrolls up: people starved, people arrived, bushels per acre, bushels eaten by rats, the price of land. A cursor blinks after a question about how many acres to plant.

**Frame.** moment panels="teletype:Once a year the steward reports|crop-cultivation:You answer: land, grain, acres to plant|grave:Starve too many and you lose the throne"

**Voice.** In 1968 a city game ran on a minicomputer. Once a year your steward reports, and you answer with three numbers: land to buy, grain to feed people, acres to plant. Grain is food, seed, and money at once. Feed too little and people starve. Starve too many in one year and you lose the throne.

**Picture.** The player types an answer. The next report says a plague has struck and half the people are dead. Hard cut to black.

**Frame.** moment panels="teletype:You type an answer|random-disasters:A plague strikes|grave:Half the people are dead"

## 2. Title (0:40 to 0:50)

**Picture.** Title card over the stacked chart of the vocabulary, out of focus.

**On screen.** Where the parts came from. Episode 2.

## 3. Hamurabi in parts (0:50 to 1:21)

**Picture.** Hamurabi's six mechanics peel off the terminal as labelled cards: crops, random disasters, consumption, turns, spoilage, an advisor.

**Frame.** anatomy game=hamurabi parts=all

**Voice.** That game is Hamurabi. The dataset behind this series lists {{derived:hamurabi.mechanic_count}} mechanics in it, and all of them are still in use. Crop growing turns up in {{derived:crop-cultivation.prevalence}} games in the catalog, including Stardew Valley.{{assert:derived.crop-cultivation.earliest_game == hamurabi}}{{assert:derived.crop-cultivation.prevalence >= 20}}

## 4. A date is a lower bound (1:21 to 2:52)

**Picture.** A timeline. Each mechanic card drops onto the year of its first catalog game. Then a second, faded track appears above the first, labelled "outside the catalog": a mainframe program, a book cover, two board games, a Minecraft mod.

**Frame.** timeline ids=variable-speed,free-placement,tech-tree,dynasty-succession,culture-religion-conversion

**Voice.** Each date is the first game in this catalog with that part, so it is a floor: Hamurabi itself was written from a description of an older program, The Sumerian Game, from 1964.

**Voice.** Plenty of the rest came from outside games altogether. SimCity took its model of urban growth from Jay Forrester's book Urban Dynamics. Civilization took its technology tree from a board game, and Railroad Tycoon started from another board game, 1830. The Sims borrowed its idea of a house from an architecture book, A Pattern Language. Factorio grew out of two Minecraft mods that added pipes and machines.

**Voice.** The catalog's edges make odd firsts. Its earliest pause button and its earliest free placement belong to Conway's Game of Life, from 1970, where seeding cells and choosing how fast generations run are those two mechanics at their barest.{{assert:derived.variable-speed.earliest_game == game-of-life}}{{assert:derived.free-placement.earliest_game == game-of-life}} Europa Universalis IV gets the credit for dynasties and religious conversion, and the catalog holds no earlier Europa Universalis game.{{assert:derived.dynasty-succession.earliest_game == europa-universalis-4}}

## 5. Most of it by 2000 (2:52 to 3:36)

**Picture.** The stacked chart builds year by year, one coloured layer per family, oldest families at the bottom. Two years spike: 1989 and 2013.

**Voice.** With that caveat, the count is lopsided. Of {{stat:n_mechanic}} mechanics, {{stat:pct_mechanics_seen_by_2000}} percent appear in a catalog game from 2000 or earlier.{{assert:pct_mechanics_seen_by_2000 >= 60}} Those early games are only {{stat:pct_games_by_2000}} percent of the catalog. The 1990s alone added {{stat:n_mechanics_first_1990s}} mechanics, the most of any decade.{{assert:peak_origin_decade == "1990s"}}

**Voice.** The two steepest years are 1989, when SimCity and Populous came out, and 2013, the year of Europa Universalis IV, Factorio, and Papers, Please.

**On screen.** {{stat:pct_mechanics_seen_by_2000}}% of the vocabulary by 2000. {{stat:pct_games_by_2000}}% of the games.

## 6. Testing the story (3:36 to 4:44)

**Picture.** Thirty-seven cards shuffle out of the full catalog at random, then shrink to the sizes of the early games. A counter tallies the mechanics they cover. The shuffle repeats, fast, and a histogram of counts builds up. A marker shows where the real early games land.

**Voice.** It looks like a golden age, and chance comes close to it. {{stat:n_games_by_2000}} games drawn at random from every era cover {{stat:n_mechanics_seen_null_mean}} mechanics on average, against {{stat:n_mechanics_seen_by_2000}} for the real early games.{{assert:n_mechanics_seen_null_mean <= n_mechanics_seen_by_2000}}{{assert:p_mechanics_seen_by_2000 > 0.05}}{{assert:p_mechanics_seen_by_2000 < 0.2}} A few dozen games from any period show most of the vocabulary. What holds up is narrower: new parts come from a handful of games in every decade, and later games are built mostly from parts that already existed.

## 7. The founding games (4:44 to 7:03)

**Picture.** SimCity, 1989. The land value overlay washes over the map, then crime, then pollution. A line of the Micropolis source code fades in over the crime map.

**Frame.** anatomy game=simcity-1989 parts=firsts

**Frame.** formula at="crime in a block is" result="crime-policing:Crime" terms="128,-land-value:Land value,+house:Density,-police:Police" from=simcity-1989:crime-policing

**Voice.** SimCity is credited with {{derived:simcity-1989.introduced_count}} mechanics, among them zoning, land value, demand for homes, shops, and industry, the power grid, crime, pollution, and traffic.{{assert:derived.zoning.earliest_game == simcity-1989}}{{assert:derived.land-value.earliest_game == simcity-1989}} The city is a stack of coarse maps recomputed in passes. When the code was released in 2008 the rules became readable: crime in a block is 128, minus land value, plus density, minus police.

**Picture.** M.U.L.E., 1983. Four players walk their avatars toward a price line in a live auction for smithore.

**Frame.** anatomy game=mule parts=firsts

**Voice.** M.U.L.E., from 1983, introduced production chains and prices set by supply and demand.{{assert:derived.production-chain.earliest_game == mule}}{{assert:derived.supply-demand-pricing.earliest_game == mule}} Food sets how long your turn lasts, energy shortages stop your plots, and players walk toward a price to make a trade. Ties go to whoever is behind.

**Picture.** Little Computer People, 1985. A small man in a cross-section of a three-storey house reads a typed request and shakes his head.

**Frame.** anatomy game=little-computer-people parts=firsts

**Picture.** Elite, 1984: a wireframe ship docks at a rotating station; the galaxy map shows hundreds of named systems.

**Frame.** anatomy game=elite parts=firsts

**Frame.** anatomy at="The Incredible Machine, from 1993" game=the-incredible-machine parts=firsts

**Frame.** anatomy at="Little Computer People, from 1985" game=little-computer-people parts=firsts

**Voice.** Elite, from 1984, regenerated eight galaxies of 256 systems from a seed instead of storing them, which let a universe fit on an eight-bit machine. It is the catalog's first game with generated terrain and with trade routes.{{assert:derived.procedural-terrain.earliest_game == elite}}{{assert:derived.trade-routes.earliest_game == elite}} The Incredible Machine, from 1993, brought rigid-body physics and sharing your designs with other players, and its physics has no random numbers, so a machine that works once works every time.{{assert:derived.rigid-body-physics.earliest_game == the-incredible-machine}}{{assert:derived.content-sharing.earliest_game == the-incredible-machine}}

**Voice.** Little Computer People, from 1985, introduced needs that decay, personality traits, and typing requests in plain English to a character who decides, depending on his mood, whether to do what you ask.{{assert:derived.needs-decay.earliest_game == little-computer-people}}{{assert:derived.natural-language-interaction.earliest_game == little-computer-people}} Each disk's serial number seeded a different resident.

**Picture.** Theme Park, 1994: a crowd of visitors, each with a thought bubble; one walks past a ride with a long queue toward a shop.

**Frame.** anatomy game=theme-park parts=firsts

**Voice.** Theme Park, from 1994, gave every visitor a record of about 200 bytes and let each one choose what to do next by scoring the options against its needs. The catalog dates that architecture, utility action selection, to Theme Park, six years before The Sims made it famous.{{assert:derived.utility-action-selection.earliest_game == theme-park}} You could also change the recipe as well as the price: more sugar in the ice cream cost more, and brought customers back.

## 8. After 2000 (7:03 to 8:59)

**Picture.** A Tale in the Desert: a crowd of player avatars around a voting monument. Then EVE Online's market screen, columns of buy and sell orders.

**Frame.** anatomy game=a-tale-in-the-desert parts=firsts

**Frame.** anatomy at="market, from the same year" game=eve-online parts=firsts

**Voice.** The 2000s added {{stat:n_mechanics_first_2000s}} mechanics, several from online worlds where the other players are part of the simulation. In A Tale in the Desert, from 2003, players write laws and vote on them. EVE Online's market, from the same year, is almost entirely player-made.{{assert:derived.player-legislation.earliest_game == a-tale-in-the-desert}}{{assert:derived.player-driven-market.earliest_game == eve-online}}

**Picture.** Dwarf Fortress. A miner breaches a cavern wall; water pours tile by tile down a corridor and fills a workshop level by level.

**Frame.** anatomy game=dwarf-fortress parts=firsts

**Voice.** The single largest source of new parts in the catalog came after the 2000 line. Dwarf Fortress, from 2006, is credited with {{stat:top_introducer_count}}, more than any other game: water and magma that flow tile by tile, heat, mood breaks, bodies made of layered tissue, migrants drawn by success, and a simulated history that runs for centuries before you arrive.{{assert:top_introducer == Dwarf Fortress}}{{assert:derived.fluid-gas-simulation.earliest_game == dwarf-fortress}}

**Picture.** Factorio: a belt of iron ore splits into two lanes and feeds a row of furnaces. Then Papers, Please: a passport stamped DENIED. Then BeamNG.drive: a car's frame folds against a pole.

**Frame.** count kind=set groups="factory games,grand strategy,job simulators,physics sandboxes" ids="conveyor-transport,request-provider-logistics|interest-groups,war-score-peace,dynasty-succession|rule-checking-inspection,diagnose-repair|soft-body-deformation,terrain-deformation" dates

**Frame.** count at="The newest arrivals come from language models" kind=set ids=generative-content,gossip-propagation dates

**Frame.** count at="Belts spread fast for a recent part" kind=spread id=conveyor-transport

**Voice.** Since 2010 the catalog adds {{stat:n_mechanics_since_2010}} mechanics, mostly from four lineages. Factory games brought conveyor belts and logistics robots. Grand strategy brought interest groups, war score, and dynasties. Job simulators brought document checks and repair. And physics sandboxes brought vehicles that bend and terrain that deforms.{{assert:derived.conveyor-transport.earliest_game == factorio}}{{assert:derived.rule-checking-inspection.earliest_game == papers-please}}{{assert:derived.soft-body-deformation.earliest_game == beamng-drive}}

**Voice.** The newest arrivals come from language models. AI Dungeon, from 2019, continues the story after every line you type, with no world state outside the text. The research town of Generative Agents, from 2023, added gossip: seed one character with a plan for a party, and over two game days the news reaches about half the town.{{assert:derived.generative-content.earliest_game == ai-dungeon}}{{assert:derived.gossip-propagation.earliest_game == generative-agents-smallville}}

**Voice.** Belts spread fast for a recent part. They reached a fifth catalog game in {{derived:conveyor-transport.year_fifth_game}}, and {{derived:conveyor-transport.prevalence}} games use them today.{{assert:derived.conveyor-transport.prevalence >= 5}}

## 9. Parts that waited (8:59 to 10:06)

**Picture.** The Oregon Trail: a supply screen with food, clothing, and medicine counters ticking down. Match cut to Minecraft's hunger bar draining.

**Frame.** timeline kind=gap ids=survival-meters,crop-cultivation,work-priorities current=survival-meters

**Voice.** Other parts sat still for decades. Survival meters, stocks of food and medicine that run down, are core in The Oregon Trail, from 1971. The next catalog game with them is Minecraft, in {{derived:survival-meters.second_year}}.{{assert:derived.survival-meters.earliest_game == oregon-trail}}{{assert:derived.survival-meters.second_game == minecraft}}

**Voice.** Crops waited from Hamurabi to Harvest Moon, in {{derived:crop-cultivation.second_year}}.{{assert:derived.crop-cultivation.second_game == harvest-moon}} RimWorld's work grid, colonists down one side and jobs across the top, first shows up as a minor part of SimAnt in 1991, where you balance an ant colony's workers, soldiers, and breeders. The next catalog game with it is Kenshi, in {{derived:work-priorities.second_year}}.{{assert:derived.work-priorities.earliest_game == simant}}{{assert:derived.work-priorities.second_game == kenshi}} Some of those gaps come from the catalog being thin before 1990. Some are real: a part sat in a few games until a later design gave it a central job.

## 10. Built from older parts (10:06 to 11:15)

**Picture.** Stardew Valley, a spring morning: the energy bar full, a field of parsnips, a villager's heart meter. Each part gets a small date tag as it appears: 1968, 1993, 1996, 1996, 1997.

**Frame.** anatomy game=stardew-valley parts=core dates

**Frame.** formula at="Friendship is" result="relationship-values:One heart" terms="250:friendship points" from=stardew-valley:relationship-values

**Frame.** formula at="you lose two points" result="relationship-values:A day without talking" terms="-2:friendship points" from=stardew-valley:relationship-values

**Voice.** Games released since 2010 draw {{stat:pct_uses_since_2010_on_pre2001}} percent of their mechanics from parts that existed in the catalog by 2000.{{assert:pct_uses_since_2010_on_pre2001 >= 75}} Stardew Valley introduced none. Its designer built it in response to Harvest Moon, the catalog's first game with seasons and with relationships to villagers.{{assert:derived.stardew-valley.introduced_count == 0}}{{assert:derived.seasons.earliest_game == harvest-moon}}

**Voice.** Stardew sets its own numbers. Friendship is 250 points a heart, and you lose two points on each day you don't talk to a villager. A day ends when your energy or the clock runs out.

**Picture.** Factorio's core parts lay out as date tags: 1982, 1983, 1989, 1991, 1998, 2006, and one tag reading 2013 on the conveyor belt.

**Frame.** anatomy game=factorio parts=core dates current=conveyor-transport

**Voice.** Factorio's core has the same history, plus one new part. Its extraction, production chains, power grid, pollution, tech tree, raids, and escalating enemies all predate it in the catalog. The conveyor belt is the exception, and the game is built around it.{{assert:derived.conveyor-transport.earliest_game == factorio}}{{assert:derived.adaptive-threat-scaling.earliest_game == dwarf-fortress}}{{assert:derived.tech-tree.earliest_game == civilization}}

## 11. Close (11:15 to 12:04)

**Picture.** A blank list with a year column beside it.

**Frame.** anatomy blank dates

**Voice.** Try it with a game from this year. List its parts, look up the first catalog game for each, and count the new ones. Most of the time you will find a few, and they are usually the parts the game is known for.

**Picture.** The design map of the catalog fades in, islands of games, with Factorio and Anno 1800 highlighted on different islands.

**Voice.** Factorio and Anno 1800 are both built on production chains, and the dataset puts them in different families. Next episode: how those families are drawn, and the games they put side by side.{{assert:cocluster.factorio.anno-1800 < 0.5}}

**On screen.** Every part and the first game that had it: simgrammar.com
