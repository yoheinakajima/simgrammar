## 8. Where the techniques land

### 8.1 How techniques change mechanics

Each `affects` edge records one of seven effects. Across {{stat:n_affects_edges}} edges the most common effect is *deepens* ({{stat:n_effect_deepens}} edges): the technique makes an existing mechanic richer, larger, or more varied without changing its role.{{assert:top_effect == Deepens}} Explanation is the rarest effect ({{stat:n_effect_explains}} edges).{{assert:rarest_effect == Explains}}

{{table:effect-distribution}}

The imbalance shows where research effort points. Generating content and replacing substrates (rule-based behavior with language models, numerical physics with learned dynamics) attract most work; explaining a simulation to the person playing it attracts little, although the techniques it needs (retrieval over structured logs, constrained generation, summarization) exist.

### 8.2 Exposure by family

Technique exposure weights each `affects` edge by the technique's maturity in games and by its effect type (weights in `vocab/rubrics.yaml`), then sums over a family's mechanics.

{{viz:technique-flows}}

{{table:family-summary}}

In total, exposure concentrates in four families: narrative and generation, agents and behavior, control and automation, and physics and materials:{{assert:top_exposed_family == Narrative & generation}}{{assert:rank.family-summary.agents-behavior <= 4}}{{assert:rank.family-summary.control-automation <= 4}}{{assert:rank.family-summary.physics-materials <= 4}} the layers where content is expensive to author or where behavior is expensive to compute. Per mechanic the order changes. {{stat:top_mean_exposed_family}} still leads and world generation is second,{{assert:top_mean_exposed_family == Narrative & generation}}{{assert:rank.family-mean-exposure.world-generation <= 2}} while agents and behavior and physics and materials fall out of the top three: their totals partly reflect how many mechanics they hold.{{assert:rank.family-mean-exposure.agents-behavior > 3}}{{assert:rank.family-mean-exposure.physics-materials > 3}} Per mechanic, exposure is low across the economic and logistic core of the genre: resources, logistics, economy, and population all sit in the lower half of families, resources and logistics near the bottom,{{assert:rank.family-mean-exposure.resources-production > 10}}{{assert:rank.family-mean-exposure.logistics-networks > 10}}{{assert:rank.family-mean-exposure.economy-finance > 10}}{{assert:rank.family-mean-exposure.population-lineage > 10}}{{assert:rank.family-mean-exposure.resources-production >= 16}}{{assert:rank.family-mean-exposure.logistics-networks >= 16}} and exposure is lowest of all in operation and procedure.{{assert:least_exposed_family == Operation & procedure}}{{assert:least_exposed_family == Operation & procedure}} {{stat:n_mechanics_zero_exposure}} mechanics are affected by no technique in the set, and they account for {{stat:pct_uses_on_zero_exposure}} percent of all game-to-mechanic uses in the catalog. Of the ten most widely used mechanics, {{stat:n_top10_prevalent_zero_exposure}} have no technique attached.

Exposure counts published results only: a mechanic is reached when a technique record has an `affects` edge to it, and the mechanics with no such edge carry {{stat:pct_uses_on_zero_exposure}} percent of all mechanic uses in the catalog. Many of them have a technique proposed for them by an opportunity (Section 9). In {{stat:n_opportunity_pairs_unlinked}} of the {{stat:n_opportunity_mechanic_pairs}} pairs of an opportunity and a mechanic it involves, none of the opportunity's own techniques has an edge to that mechanic yet; counting a mechanic as reached once an opportunity proposes a technique for it would leave {{stat:pct_uses_on_zero_exposure_unproposed}} percent of uses unreached.{{assert:pct_uses_on_zero_exposure_unproposed < pct_uses_on_zero_exposure}}{{assert:n_opportunity_pairs_unlinked > 0}} The larger figure measures where published results have not gone; the smaller one, where nothing has yet been proposed.

Current AI research mostly targets what a simulation game shows and says, not the rule-systems most simulation games are built from. That is partly sensible (production chains and budgets are cheap and legible already) and partly a gap: the economic core is where balance work, legibility problems, and authoring of recipes and scenarios consume design time.

### 8.3 Most exposed mechanics

{{table:most-exposed-mechanics}}

[[generative-content]] and [[procedural-terrain]] lead because many techniques generate content or worlds.{{assert:rank.most-exposed-mechanics.generative-content <= 2}}{{assert:rank.most-exposed-mechanics.procedural-terrain <= 2}} [[utility-action-selection]] is next:{{assert:rank.most-exposed-mechanics.utility-action-selection == 3}} language models, planners, and learned policies all offer to replace the hand-written scoring at the center of agent behavior. [[rigid-body-physics]] and [[direct-avatar]] follow, exposed mainly to frame-generating world models,{{assert:rank.most-exposed-mechanics.rigid-body-physics <= 6}}{{assert:rank.most-exposed-mechanics.direct-avatar <= 6}} which replace both with learned prediction and therefore inherit those models' consistency limits.

### 8.4 Judgment versus evidence

Each mechanic carries a judged `ai_leverage` score. It correlates with technique exposure at ρ = {{stat:rho_ai_leverage_exposure}}.{{assert:rho_ai_leverage_exposure >= 0.3}} This is a consistency check, not independent agreement: the original model rater scored leverage, wrote the technique `affects` edges, and judged technique maturity (§2.6). Independent second ratings cover part of the mechanic scores; the technique links and maturity judgments retain their original authorship. The leverage-gap table lists where they disagree: mechanics judged highly open to AI that no technique in the set yet addresses.

{{table:leverage-gap}}

Modding interfaces, blueprints, romance and family systems, creature care, diagnosis, product design, history generation, and rule-checking inspection are each judged ready for substantial change, and none has a technique pointed at it in this dataset.{{assert:derived.modding-api.technique_exposure == 0}}{{assert:derived.blueprints.technique_exposure == 0}}{{assert:derived.history-generation.technique_exposure == 0}}{{assert:derived.rule-checking-inspection.technique_exposure == 0}} Some are covered implicitly by general techniques (code generation for modding, language models for romance dialogue), but none has a cited, game-specific result.

### 8.5 Authoritative state versus presentation

The techniques divide by whether they touch authoritative simulation state. Those that change only presentation have shipped (neural upscaling and frame generation, asset generation, motion synthesis) or reached prototypes (restyling); they preserve determinism or can be made reproducible by storing what they generate.{{assert:field.real-time-video-restyling.maturity == prototype}} Those that would replace physics, fields, or the world with learned prediction remain prototypes or research in games. The shipped exceptions that reach state are narrow and controlled: cached model outputs as rules ([[llm-rule-adjudication]]), language-model characters that choose actions in [[inzoi]] ([[generative-agents]], [[on-device-language-models]]), and opponents ([[deep-rl-npc-policies]], [[monte-carlo-tree-search]]). Of these, only the language characters break reproducibility outright.{{assert:field.generative-agents.determinism_impact == breaks}}{{assert:field.deep-rl-npc-policies.determinism_impact == mitigable}}{{assert:field.monte-carlo-tree-search.determinism_impact == mitigable}}{{assert:field.llm-rule-adjudication.determinism_impact == mitigable}} The pattern suggests a design principle that recurs through §9: keep the simulation symbolic, typed, and logged, and let learned models read it, explain it, decorate it, and propose changes to it through validated interfaces.
