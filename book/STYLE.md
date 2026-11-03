# House style for the book and the videos

Applies to `book/src/`, `media/episodes/`, `media/shorts/`, and `media/mega/`. The mechanical part is enforced by `scripts/style_check.py` (run by `make check` and CI) from the list in `book/tells.yaml`; the rest is for the writer and the reviewer.

## What to write

1. **Lead with what the reader does not know.** Nobody needs a pause button, a tech tree, or a city builder explained. Open on the finding, the number, or the moment in a game, and give background only where the finding needs it.
2. **Be specific.** Name the game, the year, the rule, the number. "Crime in SimCity is 128 minus land value plus density minus police effect" is better than "SimCity models crime through several interacting factors". The records carry this detail in `design_notes`, `note`, `definition`, and `key_results`; use it.
3. **End paragraphs on a fact or an example,** not on a maxim. A closing line such as "That is what infrastructure looks like" restates the paragraph in slogan form; cut it.
4. **Say how sure the data is once, where the finding is made.** State a result at the strength its evidence supports, give the number that supports it, and move on. Report a robustness check as what was tested and what held; state a check that failed once, plainly, in the section that owns the finding. The general limits (the catalog is a sample of well-documented games, the rubric scores come mostly from one model rater, clusters move with the data) are listed once, in paper §2.6 and chapter 13, and are not repeated finding by finding. Claims about the catalog say "in the catalog". Every interpretive sentence carries an assertion (CONTRACT I10).
5. **First person only for what the author did.** No invented memories or motives. The author built the dataset with agents; that may be said. Opening scenes use "you" and describe what happens in the game.
6. **One idea per paragraph, and say it once.** A fact stated in one chapter is referred to, not restated, in the next. Within a chapter, do not summarize the section you just wrote.

## What not to write

These are the habits that make prose read as machine-written. Most are caught by the lint; the structural ones need a reader.

- **Contrast frames.** "Not X, but Y", "X is not A. It is B.", "isn't just", "more than just", and the fragment pair "Not to escape. To think." State the positive claim directly.
- **Setups and reveals.** "Here's the thing", "The answer might surprise you", "The result?", "It turns out", "This is where X comes in", "Enter X". Give the information.
- **Questions to the audience.** No rhetorical questions in prose, and no episode or short ends on a question. A closing line states a fact or what comes next.
- **Stock words.** delve, tapestry, testament, realm, landscape (figurative), navigate (figurative), harness, leverage (as a verb), seamless, robust, crucial, pivotal, vital, intricate, nuanced, myriad, showcase, underscore, foster, elevate, empower, journey (figurative), quietly, honest (of a thing), deceptively, notably, importantly, interestingly, ultimately, essentially, fundamentally, at its core, at the heart of, in the world of, when it comes to, worth noting, plays a key role, serves as, stands as, nobody talks about. The full list with reasons is `book/tells.yaml`.
- **Scaffolding in prose.** "First, ... Second, ... Third, ..." and "There are three reasons" belong in a list, if anywhere.
- **Em dashes.** Use commas, parentheses, or a new sentence.
- **Apologies and stacked hedges.** "Unfortunately", "we cannot", "should be read as", "this does not show", a limit the chapter already gave, or a sentence whose only job is to disclaim the one before it. If a limit changes what a claim means, say it once in a clause; if it applies to everything, it is already in the limits section.

A word on the list can be right in its literal sense (an Oregon Trail journey, a flight sim that navigates by beacons). Mark the line with `<!-- tells-ok: <id> -->` and the lint skips that pattern on that line; the reviewer still reads it.

## Video

- **Cold opens run under 45 seconds** and show a moment, not a definition.
- **The first sentence of each scene carries new information.** No "in this video", "let's look at", or recaps of the previous scene.
- **Narration is 135 words a minute** for timing (`scripts/episode_timings.py`); leave picture-only beats.
- **On-screen numbers are tokens,** like the narration's.
- **Shorts state the finding in the first sentence** and on screen within two seconds, show one game moment and one number, run 90 to 110 words, and end on a fact. A short is one finding, not one mechanic explained.
