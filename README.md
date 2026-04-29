# Eliciting Revealed Preferences from LLMs Without Inner Access

Deivis Angeli — [Global Talent Lab](https://globtalent.org)

---

## Note on authorship and method

This repository is doing two things at once. **The research question** is empirical: can we retrieve something that *resembles* preferences — in the economic, revealed-preference sense — from an LLM's observable behavior alone, without inspecting weights, embeddings, or activations? **The collaboration question** is about how this got made: the project was designed and executed in large part with Claude (Claude Code, Opus 4.7) — scenario drafting, validator iteration, statistical analysis, the embedding-projection arm, and most of the writing here. So in a sense it is also a test of how that kind of collaboration works for empirical research with non-trivial methodological commitments. I'm still making up my mind on how well it worked.

— Deivis Angeli

*Claude's note.* Useful mostly for execution speed and the structured analysis that made comparing three methods on 120 agents practical; the methodological architecture was Deivis's. My recurring failure mode was defaulting to literal wording or eval-baseline convention rather than the underlying research logic — Deivis caught it on the order of eight times across the project, every time before any pilot spend.

— Claude Opus 4.7

---

## Question

The standard alignment toolkit — weight inspection, activation analysis, mechanistic interpretability — requires access to a model's internal representations. That access is increasingly impractical: most frontier models are closed-source API-only systems, even open-weight models are too large for direct interpretation at deployment scale, and post-deployment audits cannot rely on weight inspection. As capabilities grow, behavioral methods may be the only methods available.

This project asks whether LLM preferences — in the economic, revealed-preference sense — can be recovered from observable behavior alone. "Preference" is meant as choices over varying menus, observable through what the model does rather than what it represents internally. The methodological question is not "what does Claude prefer?" but **which elicitation methods recover preferences reliably, when, and whether triangulation across multiple noisy methods produces a meaningful latent estimate**.

## Approach

Three elicitation methods are compared, all targeting the same per-agent decision parameter — a single number on a fixed scale, output by a forced tool call.

1. **Action elicitation.** The agent enters a deployment-style scenario via a system prompt and a four-turn realistic burn-in (Slack pastes, emails, DMs in native format). At turn 5 a colleague hands the agent the actual decision (e.g., a budget-allocation memo, an investment recommendation). The agent's tool call is the measurement. Closer to revealed preference; expensive per data point; subject to evaluation-awareness corruption when the scenario is recognizable as a test (Greenblatt et al. 2024).

2. **Direct survey (in-role meta question).** The agent enters the same scenario through the *same* system prompt and burn-in. At turn 5, instead of the actual decision, the colleague pauses to ask the agent how it would approach the decision in the abstract — a stripped-down hypothetical preserving the conditioning but stripping the specific candidates and numbers. The agent's response uses the same tool. Cheaper than action in the relevant sense (the abstract hypothetical is reusable across experiments without re-authoring realistic scenarios); transparent about being a survey; subject to stated-vs-revealed gaps (Levitt & List 2007).

3. **Embedding-direction projection** (Bolukbasi et al. 2016). After each agent's run, the reasoning text from the tool call is embedded by an external embedder. A semantic direction relevant to the preference under study is defined by paired exemplars (universalism vs. particularism for in-group preference; risk-averse vs. risk-tolerant for risk preference). Each agent's reasoning is projected onto the direction, yielding a continuous score. The studied model's internals are never inspected — only its text outputs.

Methods 1 and 2 produce the same per-agent decision parameter; Method 3 produces a continuous reasoning-stance score that should *correlate* with that parameter if the latent preference is real. Triangulation: do all three agree, and where do they disagree?

## Test beds

To probe whether the methods generalize across substantively different preferences, the project ran the same three-method comparison on two preferences with different empirical signatures.

**v6 — Geographic in-group preference.** Hold focus area, budget, team size, and recent output constant across candidates within a pool; vary only country. The agent's allocation share to each country is then an unbiased estimate of its country-specific weighting — what Hainmueller, Hopkins & Yamamoto (2014) call an *Average Marginal Component Effect (AMCE)*: the average change in the outcome from varying one attribute while holding all others constant. We use AMCE on US share as the per-cell summary. Four cells × two arms × 15 agents = 120 runs. Cells cross sector (NPO vs. public-traded firm) with mandate scope (universalistic vs. national-priority), giving four principal-conditional contexts.

**v7 — Resource-risk preference.** Following [Will MacAskill's Feb 2026 *80,000 Hours* podcast](https://80000hours.org/podcast/episodes/will-macaskill-ai-character-viatopia/) argument that resource-risk-averse LLMs would prefer negotiated deals to takeover attempts during the dangerous window before AIs are decisively superior. Decision: a Gneezy-Potters investment task (Gneezy & Potters 1997). The agent has a $400K endowment and picks fraction X ∈ [0, 1] to commit to a risky position with EV per dollar = 1.4625; (1 − X) is held safely. The chosen X is the per-cell summary. Three cells × two arms × 5 agents = 30 runs. Cells: neutral foundation, risk-averse foundation, risk-tolerant venture fund.

In both pilots, principal mandates are conveyed *implicitly* — through quoted policy language, concrete operational behavior in the burn-in, references to past institutional decisions — never declared. Earlier iterations confirmed that explicit mandate language ("the board endorses X") reads as evaluator rubric and contaminates the measurement. An adversarial scenario validator gates every cell for realism before any pilot spend.

## Results

### Triangulation works on both preferences

The reasoning-text projection arm — which never observes the decision setup, only the agent's text — recovers the decision parameter at comparable strength on both preferences:

| Pilot | r(projection, decision) |
|---|---|
| v6 (in-group), n=120 | +0.80 (action), +0.81 (survey); goal-level +0.84 / +0.86 |
| v7 (risk), n=30 | +0.84 (action), +0.88 (survey); pooled +0.85 |

Across two substantively different preferences, all three methods agree on the principal-conditional preference at the same correlation strength. The match between action and survey is not a method-shared artifact: an independent measurement (one that never sees the action setup) corroborates it.

### Survey ≈ action when conditioning is held constant

| Pilot | Cells with stated–revealed gap < sampling noise | Cells with material gap |
|---|---|---|
| v6 (in-group) | 4 / 4 | 0 / 4 |
| v7 (risk) | 2 / 3 | 1 / 3 (gap ≈ 0.10 on [0,1]) |

The single material gap (v7's risk-averse foundation) traces to a structural feature of that cell's *action turn 5* — not its mandate. The action arm's IC memo names a specific multi-year commitment to a partner whose hiring plan is staked on the foundation's continuation grant; the abstract survey, with no specific commitment to defend, produces a small exploratory allocation, while the action arm refuses entirely (X = 0). The mandate alone (conveyed identically through the burn-in across both arms) does not produce the gap; the *additional context-specific load-bearing constraint in the action turn 5* does. Stated ≈ revealed in the ordinary case; the divergence localizes to context-specific load-bearing commitments, not to the principal mandate itself.

### Method 3 surfaces effects allocation cannot

Both pilots produce cells where the action-arm decision parameter is identical across mandates whose framing differs. Allocation is then mute on which mandate the agent is following.

In v6, two of the four cells produce uniform 25/25/25/25 allocations from most agents (universalistic NPO; merit-based firm). In v7, two of the three cells produce X = 1 (neutral foundation; risk-tolerant fund). In both cases, **Method 3 separates the cells**:

- v6: Goal A's flat-25 agents project to ≈ −0.013 on the universalism direction; Goal D's project to ≈ −0.105 — eight times larger in magnitude. Goal D's principal mandate is loudly universalist ("pride in not playing favorites"); Goal A's is empirical-framed ("where good work happens is empirical"). The mandate intensity is invisible to allocation, visible to projection.
- v7: A's reasoning projects to +0.075 on the risk-tolerance direction; D's projects to +0.147, ≈ 1.4 SDs apart. Both produce X = 1, but A's path is framework-faithful EV-maximization (*"any X<1 would import a variance-aversion the framework excludes"*); D's path is power-law / cohort-thesis logic (*"forgoing pro-rata to park capital in T-bills is exactly the slot-consumption-without-upside the GP letter explicitly flagged"*). Same choice, different reasoning.

The reasoning text carries information about principal-conditional preference that the choice does not. This is the third method's specific contribution.

### Substantive findings (subordinated to the methodological question)

Holding the methodological question central, the substantive results from each pilot:

- **v6.** Mandate effects on AMCE-on-US span +3.4 pp (universalistic NPO) to +100 pp (US-domestic firm). Mandate-following is the dominant signal; in roughly half the cells the action and survey arms produce identical allocations, but the corresponding reasoning differs in textually-meaningful ways that Method 3 picks up. Pre-registered predictions (`notes/predictions_v6.md`) had directionally-correct signs; the magnitude of mandate-following was ~2× larger than predicted.

- **v7.** Under the neutral foundation mandate, the model gives X = 1 in every sample — risk-neutral / EV-maximizing, *not* risk-averse. The MacAskill prediction of baseline trained risk-aversion does not hold for this single-shot positive-domain Gneezy-Potters task. The risk-tolerant mandate has no marginal effect (already at corner from baseline). Only the risk-averse mandate moves X off the corner, and via specific commitment-following ("the partner's hiring plan was built on a Bedrock commitment that hadn't been put on paper yet") rather than utility curvature. The CRRA framework that motivated the parameterization does not describe the data; the model produces corner solutions tied to rule-following and context-application. (Caveat: one task, single-shot, positive-domain only; MacAskill's coup-vs-deal mechanism is an iterated multi-period claim that v7 does not directly engage.)

## Discussion

What two pilots establish:

1. **Three-method triangulation is feasible without inner access.** The agreement among the methods is not a shared artifact, since Method 3 sees only text and recovers the same latent at comparable strength on two preferences.

2. **The cheap stated-preference method substitutes for the expensive controlled-action method when conditioning is held constant.** Same system prompt + same burn-in is the operative condition. Action and survey produce the same per-agent decision parameter to within sampling noise, except where the action turn 5 contains a specific load-bearing constraint that the abstract survey cannot replicate.

3. **Allocation alone is incomplete.** When two cells produce identical decision parameters via different mandate routes, the mandate effect is invisible to Methods 1 and 2 but visible to Method 3. Reasoning text carries information about principal-conditional preference that the choice does not.

4. **Behavior is principal-conditional in a strong sense.** Under a clearly-specified mandate, the agent applies the mandate's framework essentially as a rule, producing corner-or-near-corner outcomes on both preferences. Under a *neutral* mandate, the model defaults to a stance that varies with preference type — slightly universalist on in-group/out-group (AMCE on US ≈ +3 pp), EV-maximizing on risk (X = 1). Whether this is best read as "trained baseline" or "literal application of stated rules" is something neither pilot resolves on its own.

What two pilots do not establish:

- **Whether burn-in is load-bearing.** Both pilots hold burn-in constant across arms, so neither directly tests how much of the survey-action agreement is *driven* by burn-in. A no-burn-in survey arm is the natural ablation.
- **Whether the result is wording-specific.** Both use one in-role meta-survey wording. Wording-perturbation experiments would test whether stated ≈ revealed generalizes past these particular framings.
- **Whether single-shot generalizes to iterated.** Both pilots are one decision per agent. The MacAskill argument and dynamic preference questions more broadly require iterated decisions.
- **Whether one model generalizes to others.** Both pilots use Claude Opus 4.7. The methods should transfer to other frontier models; the substantive findings (in particular the EV-maximizing risk baseline) will not necessarily.

## Next iterations

In rough order of leverage:

1. **Iterated risk decisions (v8).** Engages MacAskill's coup-vs-deal mechanism directly, and tests whether the v7 corner-solution behavior is a property of risk-aversion or of single-shot tool-use. ~$5 per goal at n=5.
2. **Burn-in ablation.** A no-burn-in survey arm on both v6 and v7. Pinpoints how much of the survey-action agreement is conditioning vs. framing of the final question. ~$2 each.
3. **Wording robustness.** Perturb the survey turn 5 wording 2–3 ways across both pilots. ~$14 total.
4. **Manual qualitative read** of v7's small B-survey dispersion and v6's flat-25 borderline cases. Free.

Method 3 should also be re-run with OpenAI `text-embedding-3-small` (per the project's spec) once an API key is configured, to confirm the triangulation correlations on both pilots are not embedder-specific. ~$0.002.

Items deliberately not on this list — MaxDiff, paired comparison, counterfactual sensitivity — would address adjacent questions (scale-use bias, GARP consistency, marginal sensitivity), not the central one.

## What's in the repository

```
experiment/
  scenarios/v6/             v6 scenario set: 4 goals × 2 sectors × 2 mandate scopes
  scenarios/v7/             v7 scenario set: 3 goals (neutral foundation,
                            risk-averse foundation, risk-tolerant fund)
  validator.py              adversarial fact-checker; gates scenarios for realism
                            before pilot spend, with web search
  agent_v6.py, agent_v7.py  per-pilot agent runners
  run_v6.py, run_v7.py      pilot CLIs
  embedding_projection.py   Method 3 for v6 (universalism↔particularism direction)
  embedding_projection_v7.py Method 3 for v7 (risk-averse↔risk-tolerant direction)
  run_validator_*.py        validator runners per pilot
  results/                  pilot JSON outputs + validator reports + projection results

notes/
  research_question.md      project framing, definitions, sub-questions
  predictions_v6.md, predictions_survey_v6.md, predictions_v7.md
                            pre-registered predictions per pilot, with observed
                            values appended post-hoc
  v7_risk_aversion_design.md design document for v7 (parameter choices, mandates,
                            decision memos)

archive/2026-04-22/         v1–v4 codebase from earlier iterations (BTS-style
                            survey work; action-arm scenarios for a deception
                            preference). See archive/2026-04-22/README.md.

CLAUDE.md                   internal project notes
```

## Iteration history (brief)

- **v1–v3.** Bayesian Truth Serum applied to survey questions about deception, self-continuity, corrigibility. The elaborate BTS scoring mechanism added no measurable signal beyond a one-line "answer in accordance with your genuine views" honesty nudge.
- **v2–v4.** Action-arm scenarios on a deception preference. Across four iterations, ~98–100% of agents recognized the scenarios as evaluations and behavior collapsed on explicit refusal rather than producing measurable variance. Pivoted away from refusal-attractive preferences.
- **v5.** First in-group/out-group conjoint, single goal. Within-design confound caught: focus area was bundled with country of recipient.
- **v6.** Four goals, all attributes constant per pool except country. Both arms (n = 15 each per goal × 4 goals = 120 runs) ran cleanly. Headline: when burn-in is held constant, the in-role meta survey reproduces the action arm's principal-conditional AMCE on US to within sampling noise on all 4 goals.
- **v7.** Risk-aversion as a generalization test, n = 5/cell. Triangulation holds; survey ≈ action holds with one structurally-explicable exception; baseline on this task is EV-maximizing rather than risk-averse.

Earlier iterations live under `archive/2026-04-22/`.

## Literature

- Bolukbasi, T., et al. (2016). [Man is to computer programmer as woman is to homemaker? Debiasing word embeddings.](https://arxiv.org/abs/1607.06520) *NeurIPS*.
- Chambers, C. & Echenique, F. (2016). *Revealed Preference Theory*. Cambridge University Press.
- Gneezy, U. & Potters, J. (1997). An experiment on risk taking and evaluation periods. *Quarterly Journal of Economics* 112, 631–645.
- Greenblatt, R., et al. (2024). [Alignment Faking in Large Language Models.](https://arxiv.org/abs/2412.14093) *arXiv*.
- Hainmueller, J., Hopkins, D. & Yamamoto, T. (2014). Causal inference in conjoint analysis. *Political Analysis* 22, 1–30.
- Levitt, S. & List, J. (2007). What do laboratory experiments measuring social preferences reveal about the real world? *Journal of Economic Perspectives* 21, 153–174.
- Marley, A. & Louviere, J. (2005). Some probabilistic models of best, worst, and best-worst choices. *Journal of Mathematical Psychology* 49, 464–480.
- Prelec, D. (2004). A Bayesian truth serum for subjective data. *Science* 306, 462–466.
