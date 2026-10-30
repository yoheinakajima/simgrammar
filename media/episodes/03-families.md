# Episode 3. Families across genres

Target runtime about 12 minutes: about 1,280 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 4. Footage: Factorio, Anno 1800, Papers, Please, Princess Maker 2, Job Simulator, Besiege, Farming Simulator 25, iRacing, Black & White, Creatures, inZOI, AI Dungeon, Elite, Elite Dangerous, M.U.L.E., Offworld Trading Company, Frostpunk, Frostpunk 2; publisher video policies are tracked in `media/rights.yaml` and must be checked before release. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** Group games by their mechanics instead of their genre and families appear: series that stay together, a sequel that moved, and odd couples like Papers, Please and Princess Maker 2. How the families are drawn, how far they match genre, and where they fall apart.

## 1. Cold open (0:00 to 0:45)

**Picture.** Factorio at night. A row of assemblers slows; the power graph shows demand above supply. Pollution clouds drift over a forest toward a nest of biters, which stir.

**Frame.** chain nodes="power-grid:The power is short,assembler:Every machine slows|furnace:Your furnaces,pollution-spread:Their smoke,enemy-nest:The nest about to attack" verbs="slows|make,feeds" from=factorio

**Voice.** In Factorio, the power is short, so every machine on the grid slows by the same fraction, and the smoke from your furnaces is feeding the nest that is about to attack you.

**Picture.** Anno 1800 by day. A street of artisans' houses with a needs panel open: canned food missing. A cargo ship crawls across the sea between two islands.

**Frame.** chain nodes="factory:Canned goulash on another island,trade-routes:A late ship,goods-consumption:A street of houses waits" verbs="ships,to" from=anno-1800

**Frame.** compare at="Both games run on production chains" games=factorio,anno-1800

**Voice.** In Anno 1800, a street of houses is waiting for canned goulash from another island, on a ship that is late. Both games run on production chains. The dataset puts them in different families.{{assert:cocluster.factorio.anno-1800 < 0.5}}

## 2. Title (0:45 to 0:55)

**Picture.** Title card over the design map of the catalog, islands of games, out of focus.

**On screen.** Families across genres. Episode 3.

## 3. Same chain, different games (0:55 to 1:53)

**Picture.** Factorio's mechanics on the left as cards, Anno's on the right. Six cards slide to the middle: production chains, storage, building placement, blueprints, vehicle routes, a late-game megaproject.

**Frame.** compare games=factorio,anno-1800 show=shared

**Voice.** Factorio and Anno 1800 share six mechanics. The two most common are production chains, in {{derived:production-chain.prevalence}} catalog games, and building placement, in {{derived:free-placement.prevalence}}.{{assert:derived.production-chain.prevalence >= 30}}{{assert:derived.free-placement.prevalence >= 60}}

**Picture.** The cards left on each side light up: belts, power grid, pollution, evolving enemies, circuits on the left; population tiers, consumption per house, trade between islands, rival companies on the right.

**Frame.** compare games=factorio,anno-1800 show=own

**Voice.** The parts each game has alone are rarer, and they decide what it feels like. Factorio is about throughput: belts, power, pollution, and enemies that evolve with the pollution you make. Anno is about demand: five tiers of residents whose needs decide whether their houses advance, and goods shipped between islands to meet them. Each tier also staffs its own factories, so when workers move up to artisans, a workers' chain loses its labour.

## 4. How the families are drawn (1:53 to 2:55)

**Picture.** Every game in the catalog becomes a bundle of cards. Common cards, like the pause button, shrink almost to nothing; rare cards grow. Bundles with similar large cards drift together into clumps.

**Voice.** To group games, the dataset turns each one into its list of mechanics. Core parts count double. Each part is weighted by how rare it is, so two games that share a rare part count as much closer than two games that share a pause button. Production chains, in {{derived:production-chain.prevalence}} games, count for little; conveyor belts, in {{derived:conveyor-transport.prevalence}}, count for a lot.{{assert:derived.conveyor-transport.prevalence < derived.production-chain.prevalence}} Then the build joins the closest games, and the closest groups, until it has a chosen number of clusters.

**Voice.** Factorio lands with Satisfactory, shapez 2, Dyson Sphere Program, and Captain of Industry. Anno 1800 lands with Manor Lords, Banished, Caesar III, and Pharaoh.{{assert:derived.satisfactory.cluster == derived.factorio.cluster}}{{assert:derived.captain-of-industry.cluster == derived.factorio.cluster}}{{assert:derived.manor-lords.cluster == derived.anno-1800.cluster}}{{assert:derived.caesar-3.cluster == derived.anno-1800.cluster}}

## 5. How many families (2:55 to 4:10)

**Picture.** The catalog drops a fifth of its games at random, re-clusters, and compares the result with the full clustering. A score ticks up and down. The process repeats, fast, a thousand times. A curve of average agreement against the number of clusters draws itself, nearly flat on the right.

**Voice.** The build re-clusters {{stat:cluster_subsamples}} random subsets of the games and checks how well each agrees with the full result. The stated rule takes the smallest number of clusters whose average agreement reaches {{stat:cluster_min_mean_ari}}. When it was last applied, that was {{stat:cluster_k}}. On today's data the same rule picks {{stat:cluster_rule_k}}.{{assert:cluster_rule_k != cluster_k}}{{assert:cluster_k_drift == 0}}

**Voice.** The curve is that flat. So the number of families is a weak fact, and this series only claims pairings that survive the resampling. When it says two games belong together, they share a cluster in at least {{stat:cocluster_together}} of those subsets. When it says they stand apart, in at most {{stat:cocluster_apart}}. Each claim is checked every time the dataset is built. By a separate measure, {{stat:n_stable_clusters}} of the {{stat:n_clusters}} clusters keep their shape across the resampling, and the rest shift as games come and go.{{assert:n_stable_clusters >= 10}}{{assert:n_stable_clusters < n_clusters}}

**On screen.** Together: ≥ {{stat:cocluster_together}} of subsamples. Apart: ≤ {{stat:cocluster_apart}}.

## 6. Odd couples (4:10 to 7:04)

**Picture.** Split screen. Left: Papers, Please, a passport under a lamp, a rulebook page, a clock. Right: Princess Maker 2, a month's calendar split into three slots, a daughter's attribute chart.

**Frame.** compare games=papers-please,princess-maker-2 show=shared

**Voice.** Papers, Please is about checking passports at a border. Princess Maker 2, from 1993, is about raising a daughter from ten to eighteen. They share a family.{{assert:derived.princess-maker-2.cluster == derived.papers-please.cluster}} In both, time comes in fixed slots, money is tight, and authored events keep arriving. At the border you are paid per correct decision, mistakes arrive as citations by fax, and the wages go to rent, food, and heat for your family. A shift at the border and a month of your daughter's life are the same kind of budget.

**Picture.** Job Simulator in VR: a hand throws a stapler across an office cubicle. Cut to Besiege: a wooden siege engine flips itself over.

**Frame.** compare games=job-simulator,besiege show=shared

**Frame.** compare at="Two other job sims" games=powerwash-simulator,house-flipper show=shared

**Voice.** Job Simulator belongs with Besiege and The Incredible Machine, because nearly every object in reach is a physics object you can grab, throw, or combine. Two other job sims, PowerWash Simulator and House Flipper, stand apart in a family of their own, built on tools and contracts.{{assert:derived.job-simulator.cluster == derived.besiege.cluster}}{{assert:derived.job-simulator.cluster != derived.powerwash-simulator.cluster}}

**Picture.** Farming Simulator 25: a combine harvester working a field in a straight GPS line. Cut to iRacing: a car in a pit lane.

**Frame.** compare games=farming-simulator-25,iracing show=shared

**Frame.** compare at="apart from Stardew Valley" games=farming-simulator-25,stardew-valley

**Voice.** Farming Simulator lands with the racing games, and apart from Stardew Valley and Harvest Moon.{{assert:derived.farming-simulator-25.cluster == derived.iracing.cluster}}{{assert:derived.farming-simulator-25.cluster != derived.stardew-valley.cluster}} Its farm is a fleet of more than four hundred licensed machines doing field work in order, and the skill is operating them.

**Picture.** Black & White: a giant creature being slapped for eating a villager. Cut to Creatures: a Norn being tickled.

**Frame.** compare games=black-and-white,populous

**Frame.** compare at="The creature you train" games=black-and-white,creatures show=shared

**Voice.** Black & White is a god game, and it stands apart from Populous, the god game that started the genre. The creature you train puts it with the virtual pets and with Creatures.{{assert:derived.black-and-white.cluster == derived.creatures.cluster}}{{assert:derived.black-and-white.cluster != derived.populous.cluster}}

**Picture.** Europa Universalis IV's map in political colours. Cut to Tropico 6: El Presidente on a balcony, a faction approval panel.

**Frame.** compare games=tropico-6,simcity-1989

**Frame.** compare at="Its family is the rulers" games=tropico-6,europa-universalis-4 show=shared

**Voice.** Tropico 6 is filed as a city builder, and it stands apart from SimCity. Its family is the rulers: Europa Universalis IV, Civilization, and Stellaris, held together by stability, policy choices, and interest groups.{{assert:derived.tropico-6.cluster == derived.europa-universalis-4.cluster}}{{assert:derived.civilization.cluster == derived.europa-universalis-4.cluster}}{{assert:derived.tropico-6.cluster != derived.simcity-1989.cluster}}

**Picture.** Theme Hospital: a corridor of patients with thought bubbles; a hiring screen of doctors.

**Frame.** compare games=theme-hospital,rollercoaster-tycoon show=shared

**Frame.** compare at="they still stand apart from the life sims" games=theme-hospital,the-sims

**Voice.** Theme Hospital, RollerCoaster Tycoon, and Game Dev Tycoon hold together on hiring staff, research, and crowds with preferences. Their patients and visitors have needs, as The Sims' characters do, and they still stand apart from the life sims. The player is running a business that serves a crowd.{{assert:derived.rollercoaster-tycoon.cluster == derived.theme-hospital.cluster}}{{assert:derived.theme-hospital.cluster != derived.the-sims.cluster}}

**Picture.** RimWorld's colony and The Sims' house, side by side.

**Frame.** compare games=rimworld,dwarf-fortress show=shared

**Frame.** compare at="and so do the life sims" games=the-sims,paralives show=shared

**Voice.** The colony sims hold together, RimWorld with Dwarf Fortress and Oxygen Not Included, and so do the life sims, The Sims with Paralives. The two groups share a cluster in most resamplings, less often than either holds together.{{assert:derived.oxygen-not-included.cluster == derived.rimworld.cluster}}{{assert:derived.paralives.cluster == derived.the-sims.cluster}}{{assert:cocluster.rimworld.the-sims > 0.5}}{{assert:cocluster.rimworld.the-sims < cocluster.rimworld.dwarf-fortress}}

**Picture.** inZOI: a character in a kitchen with a thought line written in plain sentences. Cut to AI Dungeon: a column of generated story text.

**Frame.** compare games=inzoi,the-sims show=shared

**Frame.** compare at="apart from AI Dungeon" games=inzoi,ai-dungeon

**Voice.** And inZOI lets typed prompts steer its characters through an on-device model, but its needs-driven core is Sims-style, so it sits with The Sims and apart from AI Dungeon and Infinite Craft.{{assert:derived.inzoi.cluster == derived.the-sims-4.cluster}}{{assert:derived.inzoi.cluster != derived.ai-dungeon.cluster}}

## 7. Series and descendants (7:04 to 8:12)

**Picture.** Elite, 1984, a wireframe ship. Dissolve to Elite Dangerous, 2014, the same docking manoeuvre in full colour.

**Frame.** compare games=elite,elite-dangerous show=shared

**Voice.** Series stay together. SimCity with SimCity 4, The Sims with The Sims 4, and Elite with Elite Dangerous, thirty years apart, on generated star systems, trade, and a ship you fly yourself.{{assert:cocluster.simcity-1989.simcity-4 >= 0.9}}{{assert:cocluster.the-sims.the-sims-4 >= 0.9}}{{assert:cocluster.elite.elite-dangerous >= 0.9}}

**Picture.** M.U.L.E.'s auction screen. Dissolve to Offworld Trading Company's market panel, prices moving with each sale.

**Frame.** compare games=mule,offworld-trading-company show=shared

**Frame.** compare at="Factorio shares a cluster with Railroad Tycoon" games=factorio,railroad-tycoon

**Voice.** The method also finds descendants with different names. Offworld Trading Company, from 2015, shares a family with M.U.L.E., from 1983, in every resampling.{{assert:cocluster.mule.offworld-trading-company >= 0.9}} Its designer names M.U.L.E. and Railroad Tycoon as inspirations. Prices move with every purchase and sale, and you win by buying up your rivals' shares, a mechanic the catalog first records in Railroad Tycoon.{{assert:derived.equity-buyouts.earliest_game == railroad-tycoon}} Those old trading games keep a weaker tie to the factory games. Factorio shares a cluster with Railroad Tycoon in about half the resamplings, and with Satisfactory in all of them.{{assert:cocluster.factorio.railroad-tycoon > 0.3}}{{assert:cocluster.factorio.railroad-tycoon < 0.7}}{{assert:cocluster.factorio.railroad-tycoon < cocluster.factorio.satisfactory}}

## 8. The sequel that moved (8:12 to 9:19)

**Picture.** Frostpunk: a radial city around a glowing generator, temperature dropping on a gauge, the Book of Laws open on child labour.

**Frame.** compare games=frostpunk,against-the-storm show=shared

**Voice.** Frostpunk is the one series in the catalog that splits. Frostpunk is a survival city builder around a single coal generator. Temperature falls on a schedule, and the laws you sign trade your people's welfare for output. Its nearest neighbour is Against the Storm.{{assert:derived.against-the-storm.cluster == derived.frostpunk.cluster}}

**Picture.** Frostpunk 2: a council chamber, a hundred seats coloured by faction, a vote count climbing toward 51.

**Frame.** compare games=frostpunk,frostpunk-2 show=own

**Frame.** compare at="Its parts put it with Tropico 6" games=frostpunk-2,tropico-6 show=shared

**Voice.** Frostpunk 2 builds districts instead of buildings and passes laws through a council of a hundred delegates. Most laws need 51 votes. Broken promises anger factions, and faction tension can end in civil war. The developer describes social survival as a bigger threat than the cold. Its parts put it with Tropico 6 and Europa Universalis IV, and it shares a cluster with the first game in fewer than half of the resamplings.{{assert:derived.frostpunk-2.cluster == derived.tropico-6.cluster}}{{assert:cocluster.frostpunk.frostpunk-2 < 0.5}}

## 9. How much genre explains (9:19 to 10:14)

**Picture.** The design map with each game coloured by its store genre. Most islands are mostly one colour; many have a second and third.

**Voice.** Knowing a game's family tells you a good deal about its genre: normalized mutual information is {{stat:cluster_subgenre_nmi}}, against {{stat:cluster_subgenre_null_nmi}} when the labels are shuffled at random.{{assert:cluster_subgenre_nmi > cluster_subgenre_null_nmi}}{{assert:p_cluster_subgenre_nmi <= 0.01}} By a stricter score, the adjusted Rand index, where 1 would mean the families reproduce the genres exactly, agreement is only {{stat:cluster_subgenre_ari}}.{{assert:cluster_subgenre_ari < 0.6}} And {{stat:n_clusters_cross_subgenre}} of the {{stat:n_clusters}} clusters mix genres. Mechanics recover where games came from far better than chance, and they still cross genre lines often.{{assert:n_clusters_cross_subgenre >= 10}}

**Voice.** A game's family says what it is built from, and that is the part a designer can borrow.

## 10. Limits (10:14 to 11:15)

**Picture.** The Game of Life's glider crawling across a grid, next to Hamurabi's text report.

**Frame.** compare games=game-of-life,hamurabi show=shared

**Voice.** Games with very few mechanics look alike by what they lack: the Game of Life has only {{derived:game-of-life.mechanic_count}} mechanics, one of them the turn structure it shares with Hamurabi and The Oregon Trail, so it clusters with them.{{assert:cocluster.hamurabi.game-of-life >= 0.9}}{{assert:derived.game-of-life.mechanic_count <= 3}} Some clusters fall apart under resampling: the one that holds Frostpunk, Plague Inc., Timberborn, and FTL changes from subset to subset, and only Frostpunk and Against the Storm stay together.{{assert:cocluster.frostpunk.against-the-storm >= 0.9}} The clustering also sees which parts a game uses and ignores how they are tuned, and every decomposition so far was written by one model rater. A second rater is the next test of these families.

## 11. Close (11:15 to 12:09)

**Picture.** A blank card bundle for the viewer's game, with its rare parts circled.

**Frame.** anatomy blank

**Voice.** Take a game you know, circle its rare parts, and find the catalog games that share two or more. That is its family, whatever its genre. Then pick the member that looks least like your game on its store page, read how it handles the part you share, and write down one thing your game could take from it.

**Picture.** The colony-sim island zooms in: RimWorld and Dwarf Fortress side by side, a mood panel on one and a legends screen on the other.

**Frame.** compare games=rimworld,dwarf-fortress show=shared

**Voice.** RimWorld and Dwarf Fortress share a family in every resampling, and both carry the catalog's top emergence score.{{assert:cocluster.rimworld.dwarf-fortress >= 0.9}}{{assert:field.dwarf-fortress.emergence == 5}} Next episode: why the deepest systems are the hardest to read.

**On screen.** The dataset, the paper, and every source: simgrammar.com
