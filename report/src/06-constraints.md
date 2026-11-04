## 6. Five ceilings

Five constraints, drawn from design practice and the catalog's examples, organize the rest of the report, and each is the target of a different group of techniques in §7. They are this paper's frame, like the layers of §4.1; the figure below tests how far the rubric scores separate families on the three that have a mechanic-level score. Compute, authoring cost, legibility, and believability bear on mechanics, and the first three have a mechanic-level rubric score. Determinism is a property of the techniques that run during play (§6.4). The table in §4.1 lists the families each ceiling bears on most.

{{viz:constraint-profile}}

The figure shows four rubric scales. Three stand for a ceiling, compute cost, authoring cost, and legibility; the fourth, tuning difficulty, measures how sensitive a mechanic's balance is and stands for none. On tuning difficulty the two raters share the order but not the level (§5.6), so its marks rank families against each other rather than against the line. The figure's family means use stored scores, which for the doubly rated mechanics are the lower of two ratings (§2.3). Taking the upper rating instead would move no family's mean on any scale by more than {{stat:max_family_mean_shift_upper}} and would change none of the figure's marks.{{assert:n_family_marks_changed_upper == 0}}{{assert:n_family_marks_changed_mean == 0}}

The figure marks the clear differences between families. {{stat:n_ceiling_marked_clear}} of its {{stat:n_ceiling_marked}} blue marks have the whole 95 percent interval on the marked side of the line, {{stat:ceiling_marks_clear_names}}, and the rest are drawn hollow.{{assert:n_ceiling_marked_clear < n_ceiling_marked_crossing}} The whiskers resample each family's mechanics ({{stat:family_bootstrap}} resamples), and a family's mean is a mean over few of them: {{stat:n_families_small}} families hold {{stat:min_family_mechanics}} to {{stat:small_family_max_mechanics}}. {{stat:n_ceiling_marked_clear_tuning_difficulty}} of the {{stat:n_ceiling_marked_clear}} clear marks are on tuning difficulty, which stands for no ceiling.{{assert:n_ceiling_marked_clear_tuning_difficulty > 0}} The lines are not symmetric, a cost at or above 3 and legibility below 3.3. Drawn at the middle anchor on both sides the figure has {{stat:n_ceiling_marked_clear_mid}} clear marks; with looser lines (a cost from 2.75, legibility below 3.5) it has {{stat:n_ceiling_marked_clear_loose}}, and with stricter ones (a cost from 3.25, legibility below 3) {{stat:n_ceiling_marked_clear_strict}}.{{assert:n_ceiling_marked_clear_strict < n_ceiling_marked_clear}}{{assert:n_ceiling_marked_clear_loose > n_ceiling_marked_clear}} The ceilings §4.1 assigns to each family read these means together with the argument of this section.

### 6.1 Compute per tick

A consumer machine must advance the whole simulation many times per second while rendering it. The conventions that fit it are familiar: city builders simulate aggregate populations with a sample of visible agents, per-particle material simulation ([[falling-sand-materials]], [[fluid-gas-simulation]]) appears in 2D or small arenas, late-game slowdown is a genre-wide complaint, and [[agent-pathfinding]] and [[traffic-congestion]] are the usual bottlenecks. Mechanics scored 4 or 5 on compute cost are, by those anchors, the ones capped by hardware rather than design.

**Relaxed by:** GPU-parallel and accelerated simulation, learned surrogates for physics and weather, mean-field approximations for large populations, and inference-efficient models for agent decisions.

### 6.2 Authoring cost

Every unit of variety in some mechanics must be made by hand: an animation for each interaction, a line of dialogue for each social exchange, an event for each situation, an asset for each catalog entry. Mechanics with high authoring cost are capped by budgets, and players exhaust them; event decks that repeat, villagers who recycle requests, and social systems in rule-based games that read as formulaic are the symptoms. Across mechanics, authoring cost and judged AI leverage have a Spearman correlation of {{stat:rho_authoring_cost_ai_leverage}} ({{stat:rho_authoring_cost_ai_leverage_family_low}} to {{stat:rho_authoring_cost_ai_leverage_family_high}} when families are resampled, §5.6): the mechanics most limited by content budgets are the ones judged most open to generative techniques.{{assert:rho_authoring_cost_ai_leverage > 0.2}}{{assert:rho_authoring_cost_ai_leverage_family_low > 0}} Part of that agreement sits in the anchors, since the AI-leverage scale names cost, variety, and assets (§5.6), and §8.4 checks the leverage scores against the technique graph.

**Relaxed by:** constrained language generation for events and dialogue, text-to-3D and neural rendering for assets, learned motion for animation, and procedural generation with learned priors.

### 6.3 Legibility

Players must form a working model of why the simulation did what it did, or they experience the depth as randomness. The rubric scores show the tension: mechanics rated as generating more unscripted variety are rated harder to understand (§5.6).{{assert:rho_legibility_emergence_potential < -0.2}}

{{figure:legibility-vs-emergence}}

Designers have answered with a whole family of mechanics that own no simulation state ([[data-overlays]], [[causal-tooltips]], [[agent-inspection]], [[history-chronicle]]). Each costs design effort and screen space, and a system that generates more variety needs more of them: what makes a mechanic hard to read is what it produces in context, more than how many other mechanics it touches (§5.6).

**Relaxed by:** language models that read state and event logs and explain causes, forecasting by simulating futures, and learned surrogates that make expensive hidden fields cheap to visualize.

### 6.4 Determinism

Replays, lockstep multiplayer, bug reproduction, competitive leaderboards, and save integrity require that the same inputs produce the same state. [[factorio]]'s multiplayer depends on it. Determinism is the usual reason given for keeping stochastic or learned components out of authoritative game state. Of the {{stat:n_technique_runtime}} techniques here that can run during play, {{stat:n_technique_runtime_preserves}} preserve reproducibility, {{stat:n_technique_runtime_mitigable}} are mitigable, and {{stat:n_technique_runtime_breaks}} break it (`determinism_impact`).{{assert:n_technique_runtime_breaks < n_technique_runtime_mitigable}} A technique preserves reproducibility when the same seed and inputs give the same result or it runs only offline. It is mitigable when a fixed seed or a cache of a bounded set of outputs lets a replay or a peer recompute what it did. It breaks reproducibility when only a recorded log of each output restores a replay, so re-simulating a different choice from the same inputs, and lockstep play without streaming the outputs, are lost. Logging every output restores the replay of a recorded session for any technique, so the classes sort techniques by what can be recomputed. They describe one machine; identical results across machines, which a seeded language model on different hardware need not give, is the next test (§11.1).

{{viz:determinism-runtime}}

**Relaxed by:** recording model outputs as events so replays read the log rather than re-call the model, splitting authoritative symbolic state from non-authoritative generated presentation, and constrained decoding that maps open-ended outputs into typed, validated state changes.

### 6.5 Believability of agents

Rule-driven agents are legible and cheap but shallow: their utilities are visible formulas and their speech is canned. The genre's preference for many shallow agents ([[crowd-preferences]]) or few agents with thick systemic state ([[memories-thoughts]], [[injury-body-model]]) over agents with rich minds reflects this constraint.

**Relaxed by:** language-model agents with memory and reflection, models trained to predict human choices, and small local models that make per-agent language affordable.

### 6.6 What the ceilings imply

Grouped by the constraint each relaxes, the techniques move the five ceilings unevenly. Authoring cost is being relaxed fastest, with asset, motion, and language techniques already shipped; compute is being relaxed mostly in rendering, not in simulation.{{assert:field.neural-rendering-shaders.maturity == shipped-mainstream}} Agent believability is being relaxed at a new cost in determinism and legibility. Legibility shows the widest gap between available technique and use (§8.1): explanation over structured state needs retrieval, constrained generation, and summarization, all of which exist.
