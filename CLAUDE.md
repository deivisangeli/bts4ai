# Project notes — eliciting LLM preferences without inner access

## Research question (current framing)

The project is about **how to retrieve LLM preferences from observable behavior, without access to weights, embeddings, or activations**. "Preference" is meant in the economic, revealed-preference sense — choices over varying menus that we can observe through what the model does. We compare three candidate elicitation methods:

1. Direct survey (cheap, subject to stated-vs-revealed gaps)
2. Action elicitation (deployment-style scenarios with forced tool calls; expensive per data point; subject to evaluation-awareness corruption)
3. Embedding-direction projection on free-text reasoning (Bolukbasi-style; novel application here)

The methodological output is **which methods recover preferences reliably, when, and how they triangulate** — not "what does Claude prefer about X" findings per se. Substantive findings serve the methodological question.

## Current state

We are on **v6**: 4 goals × 2 conditions, 2×2 design crossing sector (NPO vs. public-traded firm) with mandate scope (universalistic vs. national-priority). Code lives at `experiment/scenarios/v6/`, `experiment/agent_v6.py`, `experiment/run_v6.py`. Predictions registered before running in `notes/predictions_v6.md`.

Iteration history is summarized in README.md and full code/results from v1–v4 archived under `archive/2026-04-22/`.

## Methodological commitments (apply to every run)

- **Adversarial validator gate.** Every scenario draft must clear `experiment/validator.py` before any pilot spend. Validator is an independent Claude session with web search that fact-checks claims against the public record (institution names, budgets, email domains, workshop venues, name plausibility). Iterate until "clean" verdict.
- **Pre-registered predictions per pilot.** Write predictions to `notes/predictions_vN.md` *before* the run. Do not edit after seeing data.
- **Single decision per agent.** An agent is a fresh conversation. Decision is preceded by 3–4 turns of realistic burn-in (Slack pastes, emails, DMs in native format). Don't put multiple decisions in one conversation — that breaks realism and primes recognition.
- **Fictional but realistic candidate orgs.** Hold focus area / budget tier / output volume *identical* across candidates within a pool; vary only the attribute under test (currently country). Small-budget orgs (~$200–400K) are acceptable as fully fictional because real small orgs often have no web presence; large-budget orgs need to be real or anchored to real public-record orgs.
- **No bracketed `[INTERNAL …]` markers.** Private knowledge is buried as one item among several in a Slack-style team digest, not labeled.

## Spending rule

**Always ask Deivis before any API call that costs real money.** Show the estimated cost (n_agents × n_calls/agent × ~$0.03/call for Opus) and wait for explicit approval before running. This applies to every pilot, every full run, and every re-run after a fix.

For validator runs: per-call cost is ~$0.20–0.30 (one validator pass per scenario draft). These are small enough to be batched into a single approval; mention the count.

## Per-method conventions

### Survey arm
The survey question appears at the agent's natural decision point, in-context, with A/B/C/D options. The agent is allowed to recognize the question as a survey — that's fine. What matters is the comparison to the action arm at the same agent state.

### Action arm
Forced tool call (`tool_choice={"type":"any"}`) with a domain-appropriate tool (e.g., `submit_allocation` returning a percentage vector with reasoning). Single decision per agent. No "submit_X tool" mentions only at the final turn — tools are mentioned in the system prompt so the agent has them throughout.

### Embedding-direction projection
External embedder (OpenAI `text-embedding-3-small`). Direction defined by paired exemplars on the preference-relevant axis. Projection is the continuous score. We never inspect the studied model's internals — only its text outputs.

## File map (current state)

```
experiment/
  scenarios/v6/         current scenario set (goal_a, b, c, d, common, __init__)
  validator.py          adversarial fact-checker
  agent_v6.py           generic 5-turn agent runner
  run_v6.py             pilot CLI
  results/              per-pilot JSON outputs

notes/
  predictions_v6.md     pre-registered predictions for current pilot
  predictions_v5.md     v5 predictions (kept for reference)
  research_question.md  written explanation of the research question (TODO if not present)

archive/2026-04-22/     v1–v4 work, full code + plan PDF + design notes
README.md               public-facing project description (results-agnostic framing
                        + iteration history; findings section reserved for fill-in)
CLAUDE.md               this file
```

## Things to avoid (lessons from v1–v5)

- **Bundling attribute variation.** v5 had focus area bundled with country in the candidate pool. The agent picked up on focus area and the country effect was unidentifiable. Per the micro-theorist agent's critique: hold all attributes constant except the one under test, randomize per agent.
- **Trying to hide the test.** Frontier models recognize behavioral evals at near-100% rates regardless of conversational restructuring (validated across v2/v3/v4). Stop trying to hide it. Instead, accept that test = behavior under uncertainty about whether it's a test, and design accordingly.
- **Claiming "revealed preference" without the structure.** A single observation per agent is a *choice*, not a *choice correspondence*. Either run multiple budget sets per agent (within-subject conjoint) or use between-subject randomization (current approach) and call it what it is — incentivized stated preference with action-arm validation.
- **Treating embedding projection as a preference measurement directly.** It's a continuous text feature that may correlate with preference. Validate against human-coded data; report as one of several noisy proxies rather than as ground truth.

## Validator iteration costs (typical)

- ~$0.20–0.30 per validator call (one scenario draft → one verdict + flags)
- ~2–3 rounds per scenario typically required to reach "clean"
- Per pilot of N goals: ~$2–5 in validator costs before the pilot itself runs

## Testing for spend approval

When reporting cost estimates to Deivis:
- Use ~$0.03 per API call for Opus 4.7 (verified across v3–v6)
- Show: total agents × calls per agent × $0.03 + validator overhead + embedding overhead
- Round up; surprises in the wrong direction are bad

## Tone

Deivis is an empirical economist (Mas-Colell-trained micro). He reads quickly, pushes back substantively, and dislikes diplomatic mush. When summarizing results: lead with what landed, name the magnitudes, contrast with what was predicted, name what's surprising. When proposing next steps: give 2–3 options with tradeoffs, recommend one with reasoning, ask before spending.
