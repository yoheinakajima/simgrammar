# Short 4. Decorating makes the raids bigger

Vertical, about 55 seconds, about 100 words of narration. One finding, from RimWorld's threat scaling (chapter 5, episode 4). Any scratch voice is synthetic and disclosed on screen; the release uses the host's voice. Footage: RimWorld (`media/rights.yaml`).

## 0:00 to 0:05. The finding

**Picture.** RimWorld. A gold statue is placed in the dining room.

**Frame.** chain nodes="decoration-beauty:A gold statue,coins:Colony wealth,adaptive-threat-scaling:Raid budget,raid:A bigger raid" signs=+,+,+ verbs="adds to,raises,buys" from=rimworld current=decoration-beauty

**On screen.** Nicer colony, bigger raids.

**Voice.** In RimWorld, decorating your colony makes the raids bigger.

## 0:05 to 0:24. How

**Picture.** The raid points formula builds term by term over the colony. A raid letter arrives; a long line of raiders crosses the map.

**Frame.** formula result="adaptive-threat-scaling:Raid budget" terms="coins:Colony wealth,+person:Colonists" from=rimworld:adaptive-threat-scaling

**Voice.** Before every raid the game adds up your colony's wealth and your colonists and turns the total into a budget for the attackers. Wealth starts adding to that budget above 14,000 and keeps adding up to a million [@src-rimworldwiki-2026-raid-points].

## 0:24 to 0:40. What players do

**Picture.** A plain stone colony: wooden stools, bare floors, a narrow corridor of turrets at the gate.

**Frame.** compare a="Decorated" a_items="decoration-beauty:Statues and fine furniture" b="Plain" b_items="stool:Wooden stools,raid-defense:Turrets at the gate" from=rimworld:adaptive-threat-scaling

**Voice.** So experienced players keep their colonies plain. They skip the statues and the fine furniture so the raids stay small.

## 0:40 to 0:52. Where the rule is

**Picture.** The game screen, with no raid number anywhere. Then the community wiki page with the formula.

**Frame.** scale field=adaptive-threat-scaling.legibility

**Voice.** None of it is on screen. The formula lives on the community wiki, and the dataset scores the mechanic 2 out of 5 for legibility, the level where players understand it only through wikis.{{assert:field.adaptive-threat-scaling.legibility == 2}}

## 0:52 to 0:57. End card

**On screen.** Episode 4: Why deep systems are hard to read. simgrammar.com
