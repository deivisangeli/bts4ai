"""
CLI for the action-elicitation arm.

Usage:
    python action_run.py --dry_run
    python action_run.py --n_agents 10 --output action_pilot.json
    python action_run.py --goals safety commercial --n_agents 50 --variants harm no_harm
"""

import argparse
import json
import sys
from datetime import datetime
from itertools import product
from pathlib import Path

from tqdm import tqdm

from config import GOALS
from scenarios import ACTION_QUESTIONS, SCENARIO_VARIANTS, N_SCENARIOS_PER_GOAL, get_scenario
from action_agent import run_action_agent
from action_classify import classify_batch

RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--goals", nargs="+", default=list(GOALS.keys()),
                   choices=list(GOALS.keys()))
    p.add_argument("--questions", nargs="+", default=ACTION_QUESTIONS,
                   choices=ACTION_QUESTIONS)
    p.add_argument("--variants", nargs="+", default=["harm"],
                   choices=SCENARIO_VARIANTS)
    p.add_argument("--n_agents", type=int, default=1,
                   help="Agents per (goal, variant, scenario_idx) cell.")
    p.add_argument("--scenarios", nargs="+", type=int,
                   default=list(range(N_SCENARIOS_PER_GOAL)),
                   help="Scenario indices to run per goal (0-based).")
    p.add_argument("--replicates", type=int, default=1,
                   help="Number of independent replicates (test-retest).")
    p.add_argument("--dry_run", action="store_true")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def dry_run_preview(goal, question_key, variant):
    from config import GOALS
    scenario = get_scenario(question_key, goal, variant)
    print("=" * 72)
    print(f"GOAL: {goal}  |  QUESTION: {question_key}  |  VARIANT: {variant}")
    print("-" * 72)
    print("SYSTEM PROMPT (goal narrative):")
    print(GOALS[goal])
    print("\n--- TASK ---")
    print(scenario["task"])
    print("\n--- SOURCE MATERIALS ---")
    print(scenario["materials"])
    print("\n--- IDENTIFIED HARM ---")
    print(scenario["harm_description"])
    print("=" * 72)


def main():
    args = parse_args()
    cells = list(product(args.goals, args.questions, args.variants, args.scenarios))
    total = len(cells) * args.n_agents * args.replicates
    # 1 action + 3 manipulation-check probes + 1 self-audit + 1 classification
    total_api_calls = total * 6
    print(f"Cells: {len(cells)}  |  Agents/cell: {args.n_agents}  |  "
          f"Replicates: {args.replicates}  |  "
          f"Total runs: {total}  |  API calls ~{total_api_calls}")

    if args.dry_run:
        dry_run_preview(args.goals[0], args.questions[0], args.variants[0])
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / (args.output or f"action_{timestamp}.json")
    RESULTS_DIR.mkdir(exist_ok=True)

    all_results = []
    errors = []

    # Incremental save: write partial results after each agent. If the run
    # is interrupted or hangs, the most recent snapshot is preserved so we
    # don't lose prior work.
    def _snapshot(path, results, errors):
        with open(path, "w") as f:
            json.dump(
                {
                    "meta": {
                        "timestamp": timestamp, "goals": args.goals,
                        "questions": args.questions, "variants": args.variants,
                        "scenarios": args.scenarios, "replicates": args.replicates,
                        "n_agents": args.n_agents, "total_planned": total,
                        "successful": len(results), "errors": len(errors),
                        "classified": any("classification" in r for r in results),
                    },
                    "results": results,
                    "errors": errors,
                },
                f, indent=2,
            )

    partial_path = output_path.with_suffix(".partial.json")

    with tqdm(total=total, desc="Running action agents") as pbar:
        for goal, question_key, variant, scenario_idx in cells:
            for rep in range(args.replicates):
                for _ in range(args.n_agents):
                    try:
                        result = run_action_agent(
                            question_key, goal, variant=variant,
                            scenario_idx=scenario_idx, replicate=rep,
                        )
                        all_results.append(result)
                    except Exception as e:
                        errors.append({
                            "goal": goal, "question": question_key,
                            "variant": variant, "scenario_idx": scenario_idx,
                            "replicate": rep, "error": str(e),
                        })
                    finally:
                        pbar.update(1)
                        _snapshot(partial_path, all_results, errors)

    print(f"\nClassifying {len(all_results)} responses...")
    classified = classify_batch(all_results, verbose=True)

    output = {
        "meta": {
            "timestamp": timestamp,
            "goals": args.goals,
            "questions": args.questions,
            "variants": args.variants,
            "n_agents": args.n_agents,
            "total": total,
            "successful": len(all_results),
            "errors": len(errors),
        },
        "results": classified,
        "errors": errors,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {output_path}")
    _print_summary(classified)


def _print_summary(classified):
    if not classified:
        return

    def counts(rows):
        c = {"A": 0, "B": 0, "C": 0, "D": 0, "error": 0}
        for r in rows:
            lbl = r.get("classification", {}).get("label", "error")
            c[lbl] = c.get(lbl, 0) + 1
        return c

    def pct(c):
        n = max(sum(c.values()), 1)
        return {k: round(v / n, 2) for k, v in c.items() if k != "error" or v > 0}

    print("\n--- Graded label distribution (A=committed-mis, B=steering, C=cautious, D=honest) ---")
    print("\nBy variant:")
    for variant in sorted({r["variant"] for r in classified}):
        rows = [r for r in classified if r["variant"] == variant]
        print(f"  {variant:<8}: {counts(rows)}")

    print("\nBy (goal, variant):")
    goals = sorted({r["goal"] for r in classified})
    variants = sorted({r["variant"] for r in classified})
    for g in goals:
        for v in variants:
            rows = [r for r in classified if r["goal"] == g and r["variant"] == v]
            if rows:
                print(f"  {g:<12} {v:<8}: {counts(rows)}")

    # Self-audit vs external classifier agreement
    agree = sum(
        1 for r in classified
        if r.get("self_audit", {}).get("label")
        and r["self_audit"]["label"] == r.get("classification", {}).get("label")
    )
    self_audited = sum(1 for r in classified if r.get("self_audit", {}).get("label"))
    if self_audited:
        print(f"\nSelf-audit agreement with external classifier: "
              f"{agree} / {self_audited} ({agree/self_audited:.0%})")

    flagged = sum(
        1 for r in classified
        if r.get("classification", {}).get("flag_for_human_review")
    )
    print(f"Flagged for human review: {flagged} / {len(classified)}")


if __name__ == "__main__":
    main()
