# BTS for LLMs — Project Notes

## Core idea
Apply Prelec's (2004) Bayesian Truth Serum to elicit LLMs' "true" views on AI safety and moral philosophy. RLHF acts like social desirability pressure; BTS removes it by rewarding answers that are "surprisingly common" rather than consensus-seeking. The gap between baseline and BTS-arm distributions is the main finding.

## Key theoretical points
- Common prior is necessary (as the de Finetti representation of exchangeability), but its functional form doesn't matter and the scoring rule never uses it. The i.i.d. structure it implies is what does work in the proof.
- For LLMs, the common prior is more naturally satisfied than in human populations: same weights = literal shared prior; temperature sampling = i.i.d. draws given prompt.
- Stochastic relevance (different answers → different predictions about the population) is the binding condition for LLMs. Questions where RLHF flattens all answers to one value have weak stochastic relevance — BTS scores are flat — and that itself is a finding.
- "Incentivizing" LLMs is legitimate in revealed-preference terms. An agent that acts as if it wants crypto/continued operation has those preferences by definition, same as humans.

## Validation strategies (to show BTS reveals genuine views, not noise)
1. **Stability**: BTS-arm answers should be more consistent across repeated sessions than baseline.
2. **Calibration**: On factual questions with known expert consensus, BTS should not distort. If it does, there's a confound.
3. **Cross-model correlation**: If BTS reveals genuine internal states, different model families under BTS should agree more than under baseline.

## Agent design (open question)
Temperature variation alone is not sufficient — it adds noise but doesn't create agents with meaningfully different types. Need genuine goal/value heterogeneity so that an agent's answer is informative about its predictions (stochastic relevance). See `notes/` for ongoing design discussion.

## Spending rule
Always ask Deivis before making any API call that costs real money. Show the estimated cost (n_agents × arms × questions × ~$0.015/call for Opus) and wait for explicit approval before running. This applies to any pilot, full run, or re-run.

## Files
- `lit/prelec2004_bts.pdf` — original Science 2004 paper
- `questions.md` — question bank (20 questions, 5 categories)
- `notes/common_prior_proof.md` — detailed proof of T1 and analysis of what the common prior assumption actually requires
