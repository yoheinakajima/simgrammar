## 6. Five ceilings

This section proposes that five constraints account for many of simulation design's conventions. Each is offered as an explanation drawn from design practice and the catalog's examples, which the dataset does not test, and each is the target of a different group of techniques in §7. The table in §4.1 lists the families each ceiling bears on most.

{{viz:constraint-profile}}

The figure's family means use stored scores, which for the doubly rated mechanics are the lower of two ratings (§2.3). Taking the upper rating instead would move no family's mean on any scale by more than {{stat:max_family_mean_shift_upper}} and would change none of the figure's marks.{{assert:n_family_marks_changed_upper == 0}}{{assert:n_family_marks_changed_mean == 0}}

### 6.1 Compute per tick

A consumer machine must advance the whole simulation many times per second while rendering it. The constraint is the likely reason city builders simulate aggregate populations with a sample of visible agents, per-particle material simulation ([[falling-sand-materials]], [[fluid-gas-simulation]]) appears in 2D or small arenas, late-game slowdown is a genre-wide complaint, and [[agent-pathfinding]] and [[traffic-congestion]] are the usual bottlenecks. Mechanics scored 4 or 5 on compute cost are the ones the rater judged capped by hardware rather than design, which is what those anchors say.

**Relaxed by:** GPU-parallel and accelerated simulation, learned surrogates for physics and weather, mean-field approximations for large populations, and inference-efficient models for agent decisions.

### 6.2 Authoring cost

Every unit of variety in some mechanics must be made by hand: an animation for each interaction, a line of dialogue for each social exchange, an event for each situation, an asset for each catalog entry. Mechanics with high authoring cost are capped by budgets, and players exhaust them; event decks that repeat, villagers who recycle requests, and social systems in rule-based games that read as formulaic are consistent with that. Across mechanics, authoring cost and judged AI leverage have a Spearman correlation of {{stat:rho_authoring_cost_ai_leverage}} ({{stat:rho_authoring_cost_ai_leverage_family_low}} to {{stat:rho_authoring_cost_ai_leverage_family_high}} when families are resampled, §5.6).{{assert:rho_authoring_cost_ai_leverage > 0.2}}{{assert:rho_authoring_cost_ai_leverage_family_low > 0}} Both scores are the same rater's judgments, so what the correlation supports is a statement about that rater: the mechanics it judged most limited by content budgets are the ones it judged most open to generative techniques. Part of the agreement may be in the anchors, since the AI-leverage scale names cost, variety, and assets (§5.6), and independent second ratings cover only part of the vocabulary (§2.6). The correlation is a consistency check on those judgments, like the leverage-exposure check of §8.4, and does not show that generative techniques reach those mechanics.

**Relaxed by:** constrained language generation for events and dialogue, text-to-3D and neural rendering for assets, learned motion for animation, and procedural generation with learned priors.

### 6.3 Legibility

Players must form a working model of why the simulation did what it did, or they experience the depth as randomness. The rubric scores are consistent with the tension: in them, mechanics rated as generating more unscripted variety are rated harder to understand, a pattern §5.6 treats as a hypothesis about the scores rather than a measured trade-off.{{assert:rho_legibility_emergence_potential < -0.2}}

{{figure:legibility-vs-emergence}}

Designers have answered with a whole family of mechanics that own no simulation state ([[data-overlays]], [[causal-tooltips]], [[agent-inspection]], [[history-chronicle]]). Each costs design effort and screen space, and on this reading each coupled system a game adds needs one.

**Relaxed by:** language models that read state and event logs and explain causes, forecasting by simulating futures, and learned surrogates that make expensive hidden fields cheap to visualize.

### 6.4 Determinism

Replays, lockstep multiplayer, bug reproduction, competitive leaderboards, and save integrity require that the same inputs produce the same state. [[factorio]]'s multiplayer depends on it. Determinism is the usual reason given for keeping stochastic or learned components out of authoritative game state. Of the {{stat:n_technique_runtime}} techniques here that can run during play, {{stat:n_technique_runtime_breaks}} break reproducibility outright, {{stat:n_technique_runtime_mitigable}} can be made reproducible by seeding, caching, or logging their outputs, and {{stat:n_technique_runtime_preserves}} leave it intact (see `determinism_impact`).{{assert:n_technique_runtime_breaks < n_technique_runtime_mitigable}}

{{viz:determinism-runtime}}

**Relaxed by:** recording model outputs as events so replays read the log rather than re-call the model, splitting authoritative symbolic state from non-authoritative generated presentation, and constrained decoding that maps open-ended outputs into typed, validated state changes.

### 6.5 Believability of agents

Rule-driven agents are legible and cheap but shallow: their utilities are visible formulas and their speech is canned. The genre's preference for many shallow agents ([[crowd-preferences]]) or few agents with thick systemic state ([[memories-thoughts]], [[injury-body-model]]) over agents with rich minds is consistent with this constraint.

**Relaxed by:** language-model agents with memory and reflection, models trained to predict human choices, and small local models that make per-agent language affordable.

### 6.6 What the ceilings imply

The five constraints do not move together. Authoring cost is being relaxed fastest, with asset, motion, and language techniques already shipped; compute is being relaxed mostly in rendering, not in simulation.{{assert:field.neural-rendering-shaders.maturity == shipped-mainstream}} Agent believability is being relaxed at a new cost in determinism and legibility. Legibility shows the widest gap between available technique and use (§8.1): explanation over structured state needs retrieval, constrained generation, and summarization, all of which exist.
