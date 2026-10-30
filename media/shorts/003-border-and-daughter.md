# Short 3. A border post and a daughter

Vertical, about 50 seconds, about 100 words of narration. One finding, from the families of games (chapter 4, episode 3). The animatic uses a synthetic scratch voice, disclosed on screen; the release uses the host's voice. Footage: Papers, Please, Princess Maker 2, The Sims (`media/rights.yaml`).

## 0:00 to 0:06. The finding

**Picture.** Split screen. Left: a passport under a desk lamp in Papers, Please. Right: Princess Maker 2's daughter at her desk with a schedule.

**Frame.** compare games=papers-please,princess-maker-2

**On screen.** Same family.

**Voice.** A border-checkpoint game from 2013 and a daughter-raising game from 1993 belong to the same family.{{assert:derived.princess-maker-2.cluster == derived.papers-please.cluster}}

## 0:06 to 0:20. How we know

**Picture.** The design map of the catalog; games drift into islands, the map reshuffles over and over, and the two games keep landing on the same island.

**Voice.** We grouped {{stat:n_game}} simulation games by the parts they're built from, then redid the grouping on {{stat:cluster_subsamples}} random subsets of the catalog. These two land together almost every time.{{assert:cocluster.papers-please.princess-maker-2 >= 0.9}}

## 0:20 to 0:38. Why

**Picture.** Side by side: the border shift clock and the month's three slots; the family ledger and the annual income; a scripted visitor and a festival announcement.

**Frame.** compare games=papers-please,princess-maker-2 show=shared

**Voice.** Both give you time in fixed slots: a shift at the border, three slots a month for your daughter. Both keep money tight. Both keep sending authored events at you.

## 0:38 to 0:48. Not where you'd file it

**Picture.** The Sims' family in a kitchen slides in, then slides off the island.

**Frame.** compare games=princess-maker-2,the-sims

**Voice.** Princess Maker 2 is filed as a life sim, and it lands far from The Sims.{{assert:derived.princess-maker-2.cluster != derived.the-sims.cluster}}

## 0:48 to 0:52. End card

**On screen.** Episode 3: Families across genres. simgrammar.com
