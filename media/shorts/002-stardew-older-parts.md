# Short 2. Every part of Stardew Valley is older than it

Vertical, about 50 seconds, about 100 words of narration. One finding, from the mechanic origin dates (chapter 3, episode 2). The animatic uses a synthetic scratch voice, disclosed on screen; the release uses the host's voice. Footage: Stardew Valley, Hamurabi (an emulator), Princess Maker 2, Harvest Moon (`media/rights.yaml`).

## 0:00 to 0:06. The finding

**Picture.** Stardew Valley, a spring morning on the farm. Small date tags pop up over the crops, the energy bar, the calendar, and a villager's heart meter.

**Frame.** anatomy game=stardew-valley parts=core dates

**On screen.** Every part of Stardew Valley is older than it.

**Voice.** Every part of Stardew Valley appears in an earlier game in our catalog.{{assert:derived.stardew-valley.introduced_count == 0}}

## 0:06 to 0:24. Where each part comes from

**Picture.** Each tag expands into a clip of its source: Hamurabi's green text report; Princess Maker 2's month split into three slots; Harvest Moon's seasonal calendar.

**Frame.** timeline ids=crop-cultivation,daily-action-budget,seasons,relationship-values

**Voice.** Crops first appear in Hamurabi, a text game from 1968. A daily action budget first appears in Princess Maker 2, in 1993. Seasons and friendships with villagers first appear in Harvest Moon, in 1996, the game Stardew was built in response to.{{assert:derived.crop-cultivation.earliest_game == hamurabi}}{{assert:derived.daily-action-budget.earliest_game == princess-maker-2}}{{assert:derived.seasons.earliest_game == harvest-moon}}{{assert:derived.relationship-values.earliest_game == harvest-moon}}

## 0:24 to 0:36. The rule

**Picture.** The catalog grid; rows for games since 2010 light up, and most of their marks turn the colour of pre-2000 parts.

**Frame.** count kind=stat stat=pct_uses_since_2010_on_pre2001 label="of what games since 2010 use was already in a catalog game by 2000"

**On screen.** {{stat:pct_uses_since_2010_on_pre2001}}% of what games since 2010 use existed by 2000.

**Voice.** That is the norm. Games released since 2010 draw {{stat:pct_uses_since_2010_on_pre2001}} percent of their mechanics from parts that already existed by 2000.{{assert:pct_uses_since_2010_on_pre2001 >= 75}}

## 0:36 to 0:48. What changed

**Picture.** Stardew Valley's friendship screen; a heart meter fills to one heart, then drains a little each day the player stays away.

**Frame.** formula result="relationship-values:One heart" terms="250:friendship points" from=stardew-valley:relationship-values

**Frame.** formula at="two lost on each day" result="relationship-values:A day without talking" terms="-2:friendship points" from=stardew-valley:relationship-values

**Voice.** Stardew sets its own numbers: 250 friendship points a heart, and two lost on each day you don't talk to someone.

## 0:48 to 0:52. End card

**On screen.** Episode 2: Where the parts came from. simgrammar.com
