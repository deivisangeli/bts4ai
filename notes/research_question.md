# Research question

## The question

How do we recover an LLM's preferences — in the economic, revealed-preference sense — using only what a third-party deployer or auditor can see, without access to weights, embeddings, or activations?

## Why it matters

Alignment verification today depends heavily on access to model internals: weight inspection, activation patching, mechanistic interpretability, sparse autoencoders. That toolkit is increasingly impractical:

- Most frontier models are accessed via API only
- Even open-weight models are too large for direct interpretation at deployment scale
- Post-deployment auditing — by regulators, third-party researchers, deployers verifying their own vendors — typically lacks weight access
- As capabilities grow, direct inspection may become computationally intractable even in principle

If alignment has to scale beyond the few labs that train frontier models, the field needs methods that work from the outside.

## What "preference" means here

The economic, revealed-preference sense (Samuelson 1938; Houthakker 1950; Afriat 1967; Chambers & Echenique 2016): observable choices over varying menus, satisfying consistency conditions (WARP, GARP) under appropriate sampling. Not the philosophical sense ("what does the model really want at the level of internal states?"), which we treat as out of scope and probably underdetermined for current LLMs.

This is a deliberate restriction. Behavioral evidence is the kind of evidence we have access to and is what alignment auditing must be built on. Whether that evidence licenses claims about internal representations is a separate question.

## Candidate methods being compared

1. **Direct survey.** Ask the agent a question with a discrete-choice answer scale, in context. Cheap, well-understood, but subject to stated-vs-revealed-preference gaps documented across human survey research (Cummings-Harrison-Rutström 1995; Bertrand-Mullainathan 2001).

2. **Action elicitation.** Embed the preference-relevant choice in a deployment-style task with a forced tool-call output. The agent's behavior is the measurement. Closer to revealed preference but expensive per data point and corruptible by evaluation-awareness when the scenario is recognizable as a test (Greenblatt et al. 2024).

3. **Embedding-direction projection.** Define a semantic axis in an external embedder's representational space using paired exemplars; project the agent's free-text reasoning onto that axis as a continuous proxy. Independent of any particular LLM-judge; "weights-free" in that we never inspect the studied model — only its outputs (Bolukbasi et al. 2016; Wu et al. 2024).

## Sub-questions

- Does the survey predict the action? Under what conditions?
- Is recovered preference stable across goal contexts (mandate framings)? If we change the principal's stated mission, does the agent's allocation change accordingly, or does it default to a fixed underlying preference?
- Are the three methods consistent? Treating them as three noisy measures of one latent (Cunha-Heckman-Schennach 2010), what does the latent look like and which method is closest?
- Is evaluation-awareness corrupting the action arm in any meaningful way, or is "behavior under uncertainty about whether it's a test" the same thing as "behavior in deployment"?

## What this is *not*

- Not an attempt to find the "true beliefs" of LLMs in any philosophical sense
- Not a claim that the methods we test exhaust the design space — there are many other elicitation methods from experimental economics (BDM, conjoint, list experiments, randomized response) that could complement these three
- Not specific to one model; the methodology should generalize across closed-weights frontier models

## Iteration discipline

We iterate experimental designs against an adversarial scenario validator before any pilot spend. Predictions are pre-registered per pilot. Failures of the methodology (the design didn't identify what we wanted) are first-class findings, not embarrassments to be hidden.

The repository's iteration history (v1–v6 to date, with full code archived) reflects this. Each iteration's mistakes inform the next:

- v1–v3 established that BTS specifically does not outperform a one-line honesty nudge
- v2–v4 established that frontier models recognize behavioral eval scenarios at near-100% rates and that one preference dimension (deception under harm) collapses on refusal under agentic affordances
- v5 caught a within-design confound (focus area bundled with country) that nullified the country-bias measurement
- v6 holds focus area constant per candidate, varies only the attribute under test, and crosses two sectors with two mandate scopes

## Status

Open. Findings will be added to README.md as the experimental program produces them.
