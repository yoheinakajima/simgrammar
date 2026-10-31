# Short 1. The five most common parts

Vertical, about 50 seconds, about 100 words of narration. Scene lengths follow the ElevenLabs scratch takes, less one line cut from scene four after they were recorded. One finding, from the prevalence ranking (chapter 1, episode 1). The animatic uses a synthetic scratch voice, disclosed on screen; the release uses the host's voice. Footage: RimWorld, Cities: Skylines, Factorio, RollerCoaster Tycoon (`media/rights.yaml`).

## 0:00 to 0:06. The finding

**Picture.** The catalog grid, every game a row and every mechanic a column, columns sorted by how many games use them. The five fullest columns light up left to right.

**On screen.** The five most common parts of a simulation game.

**Voice.** Four of the five parts that turn up most often in simulation games don't simulate anything.

## 0:06 to 0:21. The five

**Picture.** Two seconds per part, each labelled with its rank: RimWorld paused mid-raid; a building dropped onto an empty lot in Cities: Skylines; a mod list; a RollerCoaster Tycoon park's finances; Factorio's research screen.

**Frame.** count kind=bars rank ids=variable-speed,free-placement,modding-api,budget-treasury,tech-tree

**Voice.** We broke {{stat:n_game}} of them into their parts. First is the pause button, in {{stat:most_prevalent_mechanic_share_pct}} percent of them. Then placing buildings where you like, support for mods, a treasury, and a tech tree.{{assert:derived.variable-speed.prevalence_rank == 1}}{{assert:derived.free-placement.prevalence_rank == 2}}{{assert:derived.modding-api.prevalence_rank == 3}}{{assert:derived.budget-treasury.prevalence_rank == 4}}{{assert:derived.tech-tree.prevalence_rank == 5}}

## 0:21 to 0:31. Seventh place

**Picture.** The seventh column lights up. Factorio: ore rides a belt into a furnace and comes out as plates.

**Frame.** chain nodes=ore,plate,gear verbs="in a furnace,in an assembler"

**Voice.** The exception is the treasury, money in and money out. Production chains come seventh, and they're the first part on the list that models a physical process: ore into plates, plates into gears.{{assert:derived.production-chain.prevalence_rank == 7}}

## 0:31 to 0:43. Where the identity is

**Picture.** The camera slides right along the grid to RimWorld's row. Its core columns light up, each one nearly empty.

**Frame.** anatomy game=rimworld parts=storyteller-director,mood-breakdown,injury-body-model

**On screen.** Storyteller: {{derived:storyteller-director.prevalence}} games. Mood breaks: {{derived:mood-breakdown.prevalence}}. Injuries by body part: {{derived:injury-body-model.prevalence}}.

**Voice.** The parts a game is known for are rare. RimWorld's storyteller, its mood breaks and its body-part injuries each show up in fewer than ten catalog games.{{assert:derived.storyteller-director.prevalence < 10}}{{assert:derived.mood-breakdown.prevalence < 10}}{{assert:derived.injury-body-model.prevalence < 10}}

## 0:43 to 0:48. End card

**On screen.** Episode 1: Every simulation game is made of the same parts. simgrammar.com
