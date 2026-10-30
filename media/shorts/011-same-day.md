# Short 11. Due on the same day

Vertical, about 55 seconds, about 100 words of narration. One finding, from the predictions table (chapter 12, episode 11). The animatic uses a synthetic scratch voice, disclosed on screen; the release uses the host's voice. Footage: screen recordings of the dataset's prediction records; no game footage.

## 0:00 to 0:06. The finding

**Picture.** A wall calendar flips to {{stat:first_prediction_resolves_long}}. Index cards pin themselves to the date.

**Frame.** timeline kind=due date=2027-12-31

**On screen.** {{stat:n_predictions_first_date}} predictions. One deadline.

**Voice.** {{stat:n_predictions_first_date}} predictions about AI in simulation games come due on the same day, {{stat:first_prediction_resolves_spoken}}.{{assert:n_predictions_first_date >= 5}}

## 0:06 to 0:36. One card

**Picture.** The first card fills the frame. Its criteria highlight clause by clause.

**Frame.** record bet=causal-why-query fields=falsifiable_signal

**Voice.** Every bet in our dataset carries one, written so a stranger could check it. Take the first: a widely played game lets you ask why something happened in your own save. It only counts if it shipped after October 24, 2026, in a game with ten thousand Steam reviews, answering from your save and not from a manual.{{assert:field.causal-why-query.falsifiable_signal.resolve_by == first_prediction_resolves}}

## 0:36 to 0:50. Who checks

**Picture.** Two run records side by side, operator and model highlighted, different in both.

**Frame.** compare a="Who made the bet" a_items="dataset-record:The agent and model that wrote it" b="Who checks it" b_items="person:A different person and model"

**Voice.** And the person who checks can't be the one who made the bet, or the same AI model that wrote it.

## 0:50 to 0:55. End card

**On screen.** Episode 11: Keeping score. simgrammar.com
