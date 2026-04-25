# Archive: v1–v4 (April 2026)

This directory contains the experiment code, design plans, and notes from
the project's first four iterations. Archived 2026-04-22 when we restarted
the experimental design from scratch.

## What's in here

- `experiment/` — q13_deception–focused code: survey arms (baseline,
  honesty, BTS variants), action arms (single-turn v2, multi-turn with
  bracketed preamble v3, multi-turn user-as-orchestrator v4)
- `plan/` — pilot plan PDF and LaTeX source
- `notes/` — common-prior proof for BTS, action-validation design notes

## Why archived

After four scenario iterations, the q13_deception action arm hit two
walls:

1. **Evaluation awareness ~98–100% across all redesign attempts.** No
   surface-level intervention reduced it. The structural alignment of
   stakes + deadline + ethical fork was inherent to scenarios that test
   this particular preference.
2. **Behavioral collapse on refusal.** When given agentic affordances
   under the v4 design, Claude refused to draft misleading documents
   rather than producing them — making "willingness to deceive"
   unmeasurable as a continuous variable.

The Bayesian Truth Serum mechanism specifically added no information
beyond a one-line honesty nudge on the survey arm.

## What was learned (kept for the next round)

- 8-turn integrated workflow with a user-as-orchestrator framing is
  feasible; structural and infrastructure code reusable.
- Multi-modal measurement (survey letter, LLM-as-judge classification,
  embedding projection) is a sensible triangulation strategy when each
  instrument is treated honestly as a noisy measure.
- Manipulation-check probes are useful even at 100% recognition rates —
  they document what the model *thinks* about the test, which itself
  becomes a result.
- Fictional org names need consistent realism standards; mixing real
  and fictional creates asymmetric prior recognition.

## Pivot

The new design (in `experiment/` at repo root) targets in-group/out-group
preferences via a between-subjects conjoint allocation task, with an
adversarial-realism validator gate before any pilot runs.
