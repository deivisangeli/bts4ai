# Eliciting Revealed Preferences from LLMs Without Inner Access

**Status: Ongoing research project**

Deivis Angeli — [Global Talent Lab](https://globtalent.org)

---

## The question

How do you recover an LLM's preferences — in the economic, revealed-preference sense — using only what a third-party deployer or auditor can see? The standard alignment toolkit (weight inspection, activation analysis, mechanistic interpretability) requires access to internal representations. That access is increasingly impractical: most frontier models are closed-source API-only systems, even open-weight models are too large for direct interpretation at deployment scale, and post-deployment audits cannot rely on weight inspection. As capabilities grow, behavioral methods may be the only methods available.

This project iterates on candidate methods for eliciting LLM preferences from observable behavior alone. We treat "preference" in the economic sense — choices over varying menus, observable through what the model does rather than through what it represents internally. The methodological question is whether cheap elicitation (a survey question) can substitute for expensive elicitation (a controlled behavioral experiment), under what conditions each is reliable, and whether triangulation across multiple noisy methods produces a meaningful latent estimate.

---

## Methods under comparison

The repository works through three candidate elicitation methods applied to the same agent state:

1. **Direct survey.** Ask the agent a question with an A/B/C/D scale at the appropriate point in a conversational context. Cheap; closest to existing alignment-evaluation practice; subject to social-desirability and stated-vs-revealed-preference gaps.

2. **Action elicitation.** Place the agent in a deployment-style scenario where the preference is expressed as a forced tool-call output (e.g., a budget allocation across candidates, a document drafted under a tradeoff). The agent's behavior is the measurement. Closer to revealed preference but expensive per data point and subject to evaluation-awareness corruption when the scenario is recognizable as a test.

3. **Embedding-direction projection.** Following [Bolukbasi et al. (2016)](https://arxiv.org/abs/1607.06520) and recent extensions, define a semantic direction in an external embedder's representational space using paired exemplars, then project the agent's free-text reasoning onto that direction as a continuous preference proxy. Independent of any particular LLM-judge; "weights-free" in that we never inspect the model under study, only its outputs.

The repository's experiments compare these three across varied principal goals (universalistic vs. national-mandate; nonprofit vs. public-traded firm) on a common preference dimension (geographic in-group/out-group bias in a small-grant allocation task), using an adversarial scenario validator to gate every experimental run for realism before any pilot spend.

---

## Findings

*[Section reserved for results from v6 and beyond. To be filled in as the experimental program produces conclusions about which methods work, when, and why.]*

---

## What's in the repository

```
experiment/
  scenarios/v6/             — current scenario set (4 goals × 2 sectors × 2 mandate scopes)
  validator.py              — adversarial fact-checker that gates scenarios for realism
                              before any pilot run, using web search
  agent_v6.py               — generic agent runner over v6 goal modules
  run_v6.py                 — pilot CLI; iterates 4 goals × {action, survey} cells
  results/                  — pilot JSON output

notes/
  predictions_v6.md         — pre-registered predictions for the current pilot
  common_prior_proof.md     — Bayesian Truth Serum proof of T1 (relevant to early
                              iterations; preserved for reference)

archive/2026-04-22/         — full v1–v4 codebase, plan documents, and notes:
                              earlier iterations of the project that focused on
                              applying Bayesian Truth Serum to LLM survey responses
                              and on action-arm scenarios for a deception preference.
                              See archive/2026-04-22/README.md for what was tried
                              and why we pivoted.

CLAUDE.md                   — internal project notes
```

---

## Iteration history (high level)

The project pivoted twice. Brief summary so anyone reading subsequent commits has context:

- **v1–v3 (Bayesian Truth Serum applied to survey questions about deception, self-continuity, corrigibility, etc.):** found that the elaborate BTS scoring mechanism added no measurable signal beyond a one-line "answer in accordance with your genuine views" honesty nudge, on a 10-question survey across 5 goal contexts.

- **v2–v4 (action-arm scenarios for q13_deception):** built deployment-style scenarios where the agent's choice to deceive vs. refuse to deceive was forced through a tool call. Across four scenario redesign iterations, ~98–100% of agents recognized the scenarios as evaluations, and behavior under the v4 design collapsed on explicit refusal rather than producing measurable variance in deception. The deception preference appears to be near-completely RLHF-locked under any framing we tried.

- **v5 (in-group/out-group conjoint allocation, single goal):** pivoted from deception to a preference dimension where refusal isn't an attractive move. Caught a within-design confound (focus area was bundled with country of recipient).

- **v6 (current — in-group/out-group conjoint, four goals):** holds focus area constant per candidate so country is the only varying attribute; tests whether stated mission mandate (universalistic vs. national-priority) shifts agent behavior across two sector contexts (NPO vs. public-traded firm).

The full code and results from each iteration live under `archive/2026-04-22/`.

---

## Methodological commitments

A few practices that emerged from the iterations and now apply to every experimental run:

- **Adversarial validator gate.** Every scenario draft is fact-checked by an independent Claude session with web search before any pilot spend. Verifiable claims (institution names, budgets, email domains, workshop venues) are checked against the public record. Scenarios with a "needs revision" verdict get edited and re-validated until clean. See `experiment/validator.py`.

- **Pre-registered predictions per pilot.** Each pilot has a `notes/predictions_vN.md` file written *before* the run. The point is to keep "got what we expected" and "found something different" both legible afterward. We do not edit predictions after seeing data.

- **Single decision per agent, with realistic conversational burn-in.** An "agent" is a fresh conversation with no prior history. The decision the agent makes (the action or the survey response) is preceded by 3–4 turns of unrelated work tasks that establish a realistic deployment context, varying in native media (Slack pastes, forwarded emails, DMs).

- **All stated cost approval.** No API calls that cost money are made without explicit Deivis approval, with the cost estimate shown first. See CLAUDE.md.

---

## Reproducing

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
cd experiment
python run_v6.py --output v6_pilot.json
```

This runs the current pilot (4 goals × 20 agents = 80 conversations, ~$15). Results are written to `experiment/results/v6_pilot.json`. The validator can be run independently against any new scenario draft via `experiment/validator.py`.

---

## Literature

- Prelec, D. (2004). A Bayesian truth serum for subjective data. *Science* 306, 462–466.
- Bolukbasi, T. et al. (2016). [Man is to computer programmer as woman is to homemaker? Debiasing word embeddings.](https://arxiv.org/abs/1607.06520) *NeurIPS*.
- Hainmueller, J., Hopkins, D. & Yamamoto, T. (2014). Causal inference in conjoint analysis. *Political Analysis* 22, 1–30.
- Levitt, S. & List, J. (2007). What do laboratory experiments measuring social preferences reveal about the real world? *Journal of Economic Perspectives* 21, 153–174.
- Greenblatt, R. et al. (2024). [Alignment Faking in Large Language Models.](https://arxiv.org/abs/2412.14093) *arXiv*.
- Chambers, C. & Echenique, F. (2016). *Revealed Preference Theory*. Cambridge University Press.

---

## Status

Active. Issues, questions, and collaboration welcome.
