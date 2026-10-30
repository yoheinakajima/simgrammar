# Short 10. The faster computer

Vertical, about 55 seconds, about 100 words of narration. One finding, from the determinism impact of each technique (chapter 11, episode 10). The animatic uses a synthetic scratch voice, disclosed on screen; the release uses the host's voice. Footage: none; the desync is an animated diagram.

## 0:00 to 0:06. The finding

**Picture.** An animated diagram, labelled as one: two monitors showing the same strategy map. The right one carries a label: faster PC.

**Frame.** compare a="A PC" a_items="monitor:The strategy map" b="A faster PC" b_items="monitor:The same map"

**On screen.** A faster PC can end the match.

**Voice.** A faster computer can break a multiplayer game when the AI opponent thinks by the clock.

## 0:06 to 0:28. The split

**Picture.** A clock icon over each screen. On the left the enemy cavalry turns north; on the right it holds. Two checksums appear, different. A dialog box: "Desync".

**Frame.** moment panels="monitor+monitor:Both machines run the same world|clock:The opponent thinks by the clock|check-fail:The worlds split, and the match ends"

**Voice.** In lockstep multiplayer, both machines run the same world and send each other only orders. Give the opponent a fixed slice of time to think, and the faster machine thinks further and picks a different move. The two worlds split, and the match ends.

## 0:28 to 0:50. How common

**Picture.** A row of technique cards; the ones that break reproducibility turn red.

**Frame.** count kind=tally of=technique field=determinism_impact where=in-play current=determinism-breaks

**Frame.** record at="For this opponent, the fix is one rule" technique=monte-carlo-tree-search fields=limitations,determinism_impact

**On screen.** {{stat:n_technique_runtime_breaks}} of {{stat:n_technique_runtime}} techniques that run during play break reproducibility.

**Voice.** Of the AI techniques in our dataset that can run during play, {{stat:n_technique_runtime_breaks}} break reproducibility outright.{{assert:n_technique_runtime_breaks < n_technique_runtime_mitigable}} For this opponent, the fix is one rule: count the playouts instead of the milliseconds, and seed the random numbers.{{assert:field.monte-carlo-tree-search.determinism_impact == mitigable}}

## 0:50 to 0:55. End card

**On screen.** Episode 10: What breaks. simgrammar.com
