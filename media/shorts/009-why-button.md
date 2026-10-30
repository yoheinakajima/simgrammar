# Short 9. The why button

Vertical, about 55 seconds, about 100 words of narration. One finding, from the ranked opportunities (chapter 10, episode 9). The animatic uses a synthetic scratch voice, disclosed on screen; the release uses the host's voice. Footage: a colony or city sim with the why-query as a labelled mock-up; no specific title is implied to have the feature.

## 0:00 to 0:06. The finding

**Picture.** The ranked table of bets, sorted by priority. The top row lifts out of the table and grows to fill the frame.

**Frame.** count kind=ranked of=opportunity n=5 current=causal-why-query

**On screen.** The top-ranked AI bet for simulation games.

**Voice.** The AI feature our dataset ranks highest for simulation games is a button that asks why.

## 0:06 to 0:30. The button

**Picture.** Mock-up, labelled: a city view. The player right-clicks a closed hospital and picks "why?". Five short sentences appear, each with a link; clicking one scrubs a timeline back to the event it names.

**Frame.** mockup kind=ui bet=causal-why-query title="Why did the hospital close?" items="question:Why?" lines="A few sentences, each linked to an event in the game's own log|The model can only say what it can point to|An answer it cannot ground says so"

**Voice.** We scored {{count:opportunity}} bets on impact, feasibility, and novelty, and this one came first.{{assert:rank.opportunities-ranked.causal-why-query == 1}} Right-click the hospital that closed three months ago, ask why, and get a few sentences, each linked to an event in the game's own log. The model can only say what it can point to. If it can't ground an answer, it says so.

## 0:30 to 0:50. The deadline

**Picture.** A calendar flips to the bet's resolve-by date.

**Frame.** timeline kind=due bet=causal-why-query current=causal-why-query

**On screen.** Due {{stat:first_prediction_resolves_long}}.

**Voice.** The bet has a deadline. If no game with at least ten thousand Steam reviews ships it by {{stat:first_prediction_resolves_spoken}}, answering free-text questions from the player's own save, it loses.{{assert:field.causal-why-query.falsifiable_signal.resolve_by == first_prediction_resolves}}

## 0:50 to 0:55. End card

**On screen.** Episode 9: Bets worth making. simgrammar.com
