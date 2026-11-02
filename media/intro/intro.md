# Intro. SimGrammar in about a minute

**Summary.** What the project is, in the order a newcomer meets it: the catalog in four numbers, the games by year, the parts they share, the icons, the bets, and the site.

Rendered twice from this one script: 16:9 for the home page and 9:16 for social posts, about 70 seconds, one take per scene with short gaps (`python scripts/video/assemble.py intro`). Every number is read from the dataset when the video is built. No game footage: the frames are the project's own graphics and screenshots of simgrammar.com as the same build renders it.

## 1. The atlas

**Picture.** Four numbers count up, each lighting as its clause is spoken: the games, the mechanics, the AI techniques, and the predictions with the years they come due.

**Frame.** count kind=totals cues="game:analyzed,mechanic:named,technique:tied,prediction:predict"

**Voice.** We analyzed {{stat:n_game}} simulation games, named {{stat:n_mechanic}} mechanics, tied them to {{stat:n_technique}} AI and machine-learning techniques, and used this data to predict the mechanics and AI techniques we expect to see in the next {{stat:years_to_first_prediction}} to {{stat:years_to_last_prediction}} years.

## 2. Every game, by year

**Picture.** Every catalog game drops onto its release year as one square, oldest first. The games the narration names are pinned, and each lights as it is said.

**Frame.** timeline kind=games ids=hamurabi,simcity-1989,civilization,the-sims,minecraft,factorio,stardew-valley,paralives

**Voice.** The catalog runs from Hamurabi in {{stat:year_min}} through SimCity, Civilization, The Sims, Minecraft, Factorio and Stardew Valley, to Paralives in {{stat:year_max}}.{{assert:field.hamurabi.year == year_min}}{{assert:field.paralives.year == year_max}}

## 3. The parts

**Picture.** Three mechanics, each with the number of catalog games that use it and two of those games, lighting as they are named. Then the most common mechanic of all.

**Frame.** count kind=bars ids=production-chain,needs-decay,tech-tree with="factorio,anno-1800|the-sims,rimworld|civilization,stellaris"

**Frame.** count kind=bars rank ids=variable-speed at="The most common"

**Voice.** Mechanics are the parts designers reuse: production chains in Factorio and Anno 1800, needs decay in The Sims and RimWorld, a tech tree in Civilization. The most common is the pause button, in {{stat:most_prevalent_mechanic_share_pct}} percent of games.{{assert:derived.variable-speed.prevalence_rank == 1}}

## 4. The icons

**Picture.** Every icon the project has drawn, in one grid. The mechanics light up, then the genres, then the techniques.

**Frame.** count kind=icons cues="mechanic:mechanic,subgenre:genre,technique:technique"

**Voice.** Each mechanic, genre and technique has an icon of its own, drawn from a few simple shapes.

## 5. The bets

**Picture.** Three bets as cards, each with its prediction and the date it resolves. The one the narration reaches is outlined.

**Frame.** record bets=causal-why-query,branch-preview-forecasts,mechanic-discovery-search current=causal-why-query

**Frame.** record bets=causal-why-query,branch-preview-forecasts,mechanic-discovery-search current=mechanic-discovery-search at="a game will credit"

**Voice.** Then we made {{stat:n_predictions}} bets, each with a prediction a stranger can check. By {{stat:first_prediction_resolves_spoken}}, a widely played game will let you ask why something happened in your own game. By {{stat:last_prediction_resolves_spoken}}, a game will credit one of its mechanics to an automated discovery system.{{assert:field.causal-why-query.falsifiable_signal.resolve_by == first_prediction_resolves}}{{assert:field.mechanic-discovery-search.falsifiable_signal.resolve_by == last_prediction_resolves}}

## 6. The site

**Picture.** simgrammar.com as this build renders it: the home page, a game's page, a mechanic's page, a bet's page, the paper, and the watch page.

**Frame.** site page=/

**Frame.** site page=/game/rimworld/ at="every game"

**Frame.** site page=/mechanic/needs-decay/ at="mechanic and bet"

**Frame.** site page=/opportunity/causal-why-query/ at="bet, with"

**Frame.** site page=/paper/ at="the paper"

**Frame.** site page=/watch/ at="these videos"

**Voice.** It's all open at simgrammar.com: a page for every game, mechanic and bet, with its sources, plus the paper and these videos.
