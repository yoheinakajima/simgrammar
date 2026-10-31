## 9. Opportunities

### 9.1 Ranking

Each opportunity names the mechanics it reworks, the techniques it depends on, games that partially demonstrate it, a validation experiment, and a falsifiable prediction. Priority is a weighted geometric mean of impact, feasibility, and novelty scored against rubric anchors; the weights favor impact and feasibility so that safe-but-trivial and brilliant-but-impossible ideas both rank below ideas that are useful and buildable.

{{viz:opportunity-priorities}}

{{table:opportunities-ranked}}

The highest-ranked opportunity is {{stat:top_opportunity}}. Most of the ideas near the top make existing simulations more legible, cheaper to extend, or more alive with techniques that already work, and none asks a learned model to become the simulation.

### 9.2 Five design principles

The opportunities share a small set of principles, each a response to the ceilings in §6 and the evidence in §8.

1. **Keep the simulation symbolic; let models read, explain, decorate, and propose.** Authoritative state stays typed and deterministic. Learned models sit around it as renderers, narrators, explainers, and proposal generators whose outputs pass through validators ([[symbolic-sim-neural-render]], [[content-elastic-events]], [[natural-language-legislation]]).
2. **Spend inference on salience.** Most ticks need no model. Calls at moments that matter, cached and logged, buy believability at bounded cost ([[salience-gated-llm-agents]], [[drama-aware-storyteller]], [[local-first-ai-sims]]).
3. **Explain before you generate.** Comprehension limits how much coupling players can use (§6.3), and technique research rarely targets it (§8.1). Explanation over logs and sensitivity analysis needs only techniques that already exist ([[causal-why-query]], [[bottleneck-explainer]], [[branch-preview-forecasts]], [[illustrated-chronicles]]).
4. **Generate offline, verify with agents.** Content, recipes, scenarios, mods, and balance can be generated at design time and checked by automated play before any player sees them ([[parallel-autobalance]], [[generated-recipe-graphs]], [[qd-scenario-libraries]], [[language-modding]]).
5. **Log every model call as an event.** Recording outputs restores replay, multiplayer sync, bug reproduction, and auditability, and the same log powers explanation, forecasting, and chronicles ([[event-sourced-sim-runtime]]).

### 9.3 By the ceiling they relax

**Legibility.** [[causal-why-query]] answers why-questions from the event log; [[bottleneck-explainer]] points at the binding constraint in production networks, a widely used mechanic that one technique reaches, and only as a playtester;{{assert:derived.production-chain.technique_count == 1}} [[branch-preview-forecasts]] shows distributions of futures before a decision; [[explained-delegation]] makes delegated subsystems accountable; [[sim-instructor-coach]] narrates mistakes in operation sims.

**Authoring cost.** [[content-elastic-events]] removes the ceiling on event decks; [[generated-inspection-shifts]] gives rule-checking games endless fair cases; [[generative-decoration-catalogs]] and [[learned-build-assist]] widen creative modes; [[generated-recipe-graphs]] and [[qd-scenario-libraries]] cut the cost of progression content; [[language-modding]] hands extension to players.

**Agent believability.** [[salience-gated-llm-agents]] gives colony and life sims specific minds at bounded cost; [[drama-aware-storyteller]] picks events for characters' arcs; [[negotiating-faction-ai]] lets rivals bargain and remember; [[human-calibrated-customers]] grounds crowds in models of real choice; [[trainable-creatures-revival]] returns to learned creatures with modern learning; [[neural-npc-motion]] shows internal state in movement.

**Compute.** [[learned-material-surrogates]] extends particle-level materials to whole worlds; [[mean-field-crowds]] lets cities hold equilibrium-consistent populations; [[learned-weather-layer]] brings realistic weather at low runtime cost.

**Determinism and infrastructure.** [[event-sourced-sim-runtime]] and [[local-first-ai-sims]] make AI components operable in long-lived, offline, moddable games; [[symbolic-sim-neural-render]] separates what must be exact from what may be generated.

**New forms.** [[llm-society-terrarium]] makes watching a language-agent society the game; [[open-ended-evolution-sandbox]] builds evolution games on continuous artificial life; [[specification-programming-games]] turns programming puzzles into specification and testing; [[intent-level-orders]] and [[teachable-sim-companion]] move control from clicks to intent and demonstration; [[agent-ambassadors-async]] links single-player worlds through negotiating envoys; [[dream-replay-layer]] gives world models a role where drift is a feature; [[living-workforce-factories]], [[placement-that-tells-stories]], and [[scientists-not-tech-trees]] fill white space between common mechanics.

**Beyond entertainment.** [[sims-as-agent-benchmarks]] offers simulation games as long-horizon evaluation environments for AI agents; [[participatory-planning-sandboxes]] and [[calibrated-serious-sims]] carry calibrated models into planning and education; [[mechanic-discovery-search]] uses this taxonomy as a search space for new mechanics.

### 9.4 Where to start, by kind of builder

- **A small studio** should look first at opportunities with feasibility 4 or 5 and horizon "now": legibility layers over an existing simulation, content-elastic events with validators, salience-gated agents on a local model, and offline balancing. Each can ship as a feature of a conventional design.
- **An engine, middleware, or tools company** has the infrastructure opportunities: event-sourced runtimes with model-call logging, constrained interfaces from language to game actions, headless simulation for agent testing, and calibrated surrogate libraries for weather and materials.
- **A research group** has the open problems: symbolic-to-neural rendering with semantic fidelity guarantees, learned material surrogates that conserve mass and energy, automated discovery of mechanics, and evaluation of explanation quality in games.
- **Organizations outside games** can use simulation games as instruments: agent benchmarks, planning sandboxes, and calibrated serious simulations, where the genre's legibility layer is as valuable as its models.
