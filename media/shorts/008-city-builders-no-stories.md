# Short 8. City builders don't tell stories

Vertical, about 55 seconds, about 100 words of narration. One finding, from the white-space analysis (chapter 9, episode 8). Any scratch voice is synthetic and disclosed on screen; the release uses the host's voice. Footage: Cities: Skylines, Surviving Mars (`media/rights.yaml`).

## 0:00 to 0:06. The finding

**Picture.** Two piles of game covers: a tall one labelled "place buildings," a short one labelled "story events." A single cover slides into the gap between them.

**Frame.** count kind=venn a=free-placement b=triggered-event-chains

**On screen.** Place buildings: {{derived:free-placement.prevalence}} games. Story events: {{derived:triggered-event-chains.prevalence}}. Both: one.

**Voice.** Only one game in our catalog lets you place buildings and also runs chains of story events: {{derived:free-placement.prevalence}} games do the first, {{derived:triggered-event-chains.prevalence}} the second.{{assert:cooccur.free-placement.triggered-event-chains == 1}}

## 0:06 to 0:28. The moment

**Picture.** Cities: Skylines. A district built in one go, decades later: hearses queued down the street, house after house.

**Frame.** moment panels="house:A district built all at once|clock:Grows old all at once|grave+car:The hearses back up"

**Voice.** In Cities: Skylines, a district built all at once grows old all at once. Decades later its residents die in a wave, and the hearses back up. The game treats it as a services problem. Nothing tells you a story about any of them.

## 0:28 to 0:46. The exception

**Picture.** Surviving Mars: a colony of domes, then a Mystery's first event window.

**Frame.** anatomy game=surviving-mars parts=free-placement,triggered-event-chains,power-grid,tech-tree current=triggered-event-chains

**Voice.** The exception is Surviving Mars, which lays authored mysteries like plagues and AI revolts over a colony you lay out yourself. Even there, the mysteries are layered on top of the colony.{{assert:rank.whitespace.free-placement.triggered-event-chains == 1}}

## 0:46 to 0:51. End card

**On screen.** Episode 8: Vacant lots. simgrammar.com
