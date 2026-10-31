# Short 7. Most used, barely touched

Vertical, about 55 seconds, about 100 words of narration. One finding, from technique exposure by family (chapter 8, episode 7). Any scratch voice is synthetic and disclosed on screen; the release uses the host's voice. Footage: Factorio (`media/rights.yaml`).

## 0:00 to 0:05. The finding

**Picture.** Factorio. A long production line running at full speed, then stopping stage by stage from the end backwards.

**Frame.** chain nodes=furnace,conveyor-transport:Belt,assembler,science-flask:Research verbs="feeds,carries,makes" from=factorio

**On screen.** Resources and production: {{stat:n_family_zero_exposure_resources_production}} of {{stat:n_family_mechanics_resources_production}} mechanics with no AI technique.

**Voice.** The kind of mechanic simulation games use most is among the kinds AI research has touched least.{{assert:most_used_family == Resources & production}}{{assert:rank.family-mean-exposure.resources-production >= 16}}

## 0:05 to 0:22. The number

**Picture.** Fourteen labelled tiles for the family's mechanics. All but three go grey.

**Frame.** count kind=tiles family=resources-production lit=affected

**Voice.** Resources and production is the most used family in our catalog. Of its {{stat:n_family_mechanics_resources_production}} mechanics, {{stat:n_family_zero_exposure_resources_production}} have no AI technique pointed at them. Production chains get one, and only to test them.{{assert:n_family_zero_exposure_resources_production >= 10}}{{assert:derived.production-chain.technique_count == 1}}

## 0:22 to 0:40. The moment

**Picture.** The player clicks the assembler at the end of the stalled line. Far upstream, off screen, one furnace sits idle. A slow pan finds it.

**Frame.** moment panels="cursor+assembler:The player clicks the stalled assembler|conveyor-transport:The belt feeding it is empty|furnace:Far upstream, one furnace sits idle"

**Frame.** record at="The record for production chains" mechanic=production-chain fields=failure_modes

**Voice.** A furnace starves far upstream, and the player blames the building in front of them. The record for production chains lists that as a known failure in games without flow statistics.

## 0:40 to 0:52. Where the research went

**Picture.** The family bars, narrative and generation at the top.

**Voice.** Instead the techniques pile up on stories and characters. Narrative and generation is the most exposed family in the set.{{assert:top_exposed_family == Narrative & generation}}

## 0:52 to 0:57. End card

**On screen.** Episode 7: Where AI lands. simgrammar.com
