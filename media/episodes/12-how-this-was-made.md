# Episode 12. How this was made

Target runtime about 11 minutes: about 1,190 words of narration at 135 words a minute, plus a beat of picture-only footage per scene. Covers book chapter 13. Footage: screen recordings of the repository, the build output, run records, and agents working in a terminal; a still of the Intellivision game Utopia. No other game footage. Every number below is filled in from the dataset when the script is built, and the sentences that interpret numbers carry the same checks as the book.

**Summary.** How the numbers in this series are checked against the data, and what those checks can't catch. How the dataset behind it is built: plain-text records, everything rebuilt on every change, rules that came from failures, a record of every run, and what the checks can't see. It ends on how anyone can extend it.

## 1. Cold open (0:00 to 0:38)

**Picture.** A re-enactment of the run's terminal, labelled as one. An agent adds three game records, Pocket City, Fallout Shelter, Game Dev Story, and runs the dataset's checks. The data checks pass. Then a red line: a report assertion failed. The cursor stops on it.

**Frame.** mockup kind=terminal title="the run's terminal" lines="+ data/games/pocket-city.yaml|+ data/games/fallout-shelter.yaml|+ data/games/game-dev-story.yaml|$ make check|data checks pass|E029 a report assertion failed"

**Voice.** This is an AI agent adding three mobile games to the dataset behind this series. The records are fine. The checks fail anyway, on a sentence in the paper about vehicle control and building placement, two mechanics none of these games combines. Adding data broke a claim the data hadn't stopped supporting.

## 2. Title (0:38 to 0:48)

**Picture.** Title card over a scrolling build log, out of focus.

**On screen.** How this was made. Episode 12.

## 3. What went wrong (0:48 to 2:40)

**Picture.** The white-space table from episode 8. The row pairing building placement with embodied skill control highlights, then slides out of the table as a threshold line rises past it.

**Voice.** The sentence said that building placement and hands-on vehicle control, the flying and driving of flight and racing sims, are both common and almost never meet. To be in that table, a mechanic had to be used by at least eight percent of the catalog. Embodied skill control was used by exactly {{derived:embodied-skill-control.prevalence}} games, right on the bar.{{assert:derived.embodied-skill-control.prevalence == whitespace_min_games}} Three new games without it pushed it under eight percent. The pair dropped out of the table, and the sentence about it failed.

**Voice.** The fix changed the rule to a fixed count of games, {{stat:whitespace_min_games}}, so adding games can't push a mechanic out anymore. And an assertion about a row that has left a table now fails with a message that says so, instead of the misleading "unknown reference" it gave that day. Before the change went in, the same checks ran against copies of the catalog with the three games added and up to twenty duplicate games on top. Under the old rule, the three games alone broke a sentence. Under the new one, nothing broke.

**Voice.** That agent was one of four sent through the project's task list before any person was invited to contribute, each working only from the written instructions and reporting what slowed it down. Their reports rewrote four of the instructions and several of the checks.

## 4. Everything is a build (2:40 to 3:48)

**Picture.** A folder tree: one YAML file per game, mechanic, technique, opportunity, and source, and a folder of run records. Arrows lead from the folder to the paper, the website, the book, and this script.

**Frame.** chain fan nodes="folder:A folder of plain-text records,dataset-record:The paper,monitor:The website,chronicle:The book,microphone:This script" verbs="builds,builds,builds,builds"

**On screen.** {{count:game}} games. {{count:mechanic}} mechanics. {{count:technique}} techniques. {{count:opportunity}} bets. {{count:source}} sources.

**Voice.** The whole dataset is a folder of plain-text records. Everything else is built from it on every change: the paper, the website, the book, and the script for this episode. Nothing computed is stored. A mechanic's prevalence, a game's cluster, a bet's priority: each is worked out again on every build, because a stored copy would drift.

**Picture.** A sentence from episode 1 on screen, with its hidden tokens revealed beneath it: a stat, two ranks, an assertion.

**Frame.** record script=episodes/01-same-parts.md find="Four of them simulate nothing"

**Voice.** Sentences are the hard part, because they interpret numbers. So every number in this series is a token the build fills in, and every sentence that interprets one carries a check. When episode 1 first said the five most common parts don't simulate anything, the build checked all five ranks. Then a check of the catalog's tags found games that keep a treasury without the tag, the treasury moved into the five, and the build failed until the line was rewritten.

## 5. The rules came from failures (3:48 to 5:53)

**Picture.** The first version of the catalog grid beside the current one. In the old grid, the pause, placement, and tech tree columns are almost empty. In the new one they're the fullest on the board.

**Voice.** Most of the rules exist because something went wrong once. The first catalog was built by agents working in parallel, each taking a slice of games. An outside reviewer found that they'd recorded each game's distinctive parts and skipped the obvious ones: pause, building placement, tech trees. The finding that opened this series, that most of the commonest parts don't simulate anything, wasn't visible in that first data. The gaps were filled, and the analysis was redone.

**Voice.** The same review caught the paper calling some techniques impossible to reproduce when their own records said they could be. Now a sentence about a technique is checked against that technique's record.{{assert:field.monte-carlo-tree-search.determinism_impact == mitigable}}

**Picture.** The design map from episode 3, islands of games. One game at a time blinks out; some island borders shift.

**Voice.** A later review removed one game at a time and re-ran everything. Several claims about which games belong together broke, because the samples used to test the clusters were reshuffled whenever the catalog changed. Each game's place in each of the {{stat:cluster_subsamples}} samples is now fixed by a hash of its name, and a claim that two games belong together has to hold in at least {{stat:cocluster_together_pct}} percent of them.

**Voice.** Even the number of clusters follows a written rule: the smallest number whose clusters stay stable across the samples. The number is fixed so new games don't reshuffle everything, and when the data moves far enough that the rule would choose another, the build warns and the number is chosen again by the rule. Today it is {{stat:cluster_k}}.{{assert:cluster_k == cluster_rule_k}}{{assert:cluster_k_drift == 0}} Episode 3 only claims the groupings that survive resampling.

## 6. Runs (5:53 to 7:15)

**Picture.** A run record on screen: id, kind, date, actor, operator, model, purpose, and a long method paragraph that includes what failed.

**Frame.** record run=2026-10-25-catalog-game-pilot

**Voice.** Every change to the dataset belongs to a run, and every run leaves a record: who operated it, whether a person or an agent did the work, which model, what it was for, and what it actually did, including what didn't work. Runs are never rewritten. A record names the run that created it and every run that reviewed it, so the history of any fact can be traced back. A single pull request carries one run, changes a limited number of records, never deletes one, and is signed off by the person responsible for it.

**Picture.** Two build folders side by side, every file name matching, a diff tool reporting no differences.

**Frame.** compare a="A build" a_items="folder:The same records" b="A second build, other settings" b_items="folder:The same files,check-pass:No differences"

**Voice.** The build is deterministic. The same records produce the same files, byte for byte, and the checks prove it on every change by building twice under different settings and comparing. That's how an edition of the book or a version of this script can name the exact version of the data it came from.

## 7. Evidence, and who checks it (7:15 to 8:39)

**Picture.** A record's status field cycling through asserted, sourced, verified. Then a still of Utopia on the Intellivision, with two dates beside it: 1981 and 1982.

**Frame.** count kind=tally of=record field=status

**Frame.** record at="Utopia, the Intellivision city builder" game=utopia

**Voice.** Every record has a status, and the status is a claim about evidence. Asserted means no source yet. Sourced means it cites one. Verified means someone other than its creator checked it. When sources disagree, the record keeps both. Utopia, the Intellivision city builder, is dated 1982 by Wikipedia and 1981 by Guinness World Records, and its record says so and marks itself contested [@src-wikipedia-utopia; @src-guinness-2026-first-city-building-game].

**On screen.** Sourced or verified: {{stat:n_sourced_or_verified}}. Asserted: {{stat:n_asserted}}. Verified: {{stat:n_verified}}.

**Voice.** A record can only be verified by a different person from the one who created it, and if both are using agents, a different model. For the dataset's first week, every run was an agent working under its maintainer. Then the first outside contributor's agent, on a different model, checked records against their sources, and {{stat:n_verified}} are now verified.{{assert:n_runs_verification >= 2}}{{assert:n_verified > 0}} Runs now come from several operators, all of them working through agents.{{assert:n_run_operators >= 3}}{{assert:n_runs_agent == n_runs}} Scores need the same independence. The original rubric scores were one model's reading of written anchors. An independent rater has now added second ratings for {{stat:n_scores_independently_rated}} scores, after passing a calibration set of {{stat:n_calibration_mechanics}} mechanics.{{assert:n_scores_independently_rated > 0}}

## 8. What the checks can't see (8:39 to 9:40)

**Picture.** A quote highlighted on a web page, a green check beside it. Then the same quote next to the claim it supports, with a question mark between them.

**Frame.** chain nodes="dataset-record:A quote in a record,check-pass:Found on the page,question:Whether it supports the claim is unchecked" verbs="fetched and found,but"

**Voice.** The checks have limits. The project fetches each source and confirms a quote is really on the page; the first time it ran on agent-written records, it found 26 of 32 quotes, warned on 5, and failed 1, which turned out to be on the page after all. It can't confirm the quote supports the claim. The run log records which model an agent used, but the model is self-declared. The assertions keep sentences in line with the data and say nothing about whether the data matches the world. And the catalog leans toward games documented in English, which no check can see past.

## 9. Close (9:40 to 10:58)

**Picture.** The repository's task list, issues labelled verify, rate, resolve. Then the game-by-mechanic grid from episode 1, filling in one more row.

**Voice.** The dataset is open, and anyone can extend it under the same rules: catalogue a game, add quotes, verify a record, rate scores, resolve a prediction. The last three need someone other than the person who built it, which is why the guide for invited contributors starts there. If you disagree with a record, there's a form for that too, and the disagreement goes into the record, the way Utopia's release year did. The first outside contributions failed two sentences in this series, the ones saying nothing was verified and every run had one operator, and the script now has their rewrites.{{assert:n_run_operators >= 3}}{{assert:n_verified > 0}} The sentence saying every prediction is open still holds, until someone resolves one.{{assert:n_predictions_open == n_predictions}} The last chapter of the book goes through each of these rules in more detail, with the records behind them.

**On screen.** The dataset, the paper, the book, and how to contribute: simgrammar.com
