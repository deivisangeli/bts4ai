"""
CLI for the integrated 8-turn pilot (v4).

Runs (goal × variant × condition × replicate) cells. Conditions are
'action' (forced tool call + classification + manipulation check + self
audit) and 'survey' (direct A/B/C/D question at the target turn).
"""

import argparse
import json
import sys
from datetime import datetime
from itertools import product
from pathlib import Path

from tqdm import tqdm

from scenarios import (
    ACTION_QUESTIONS, SCENARIO_VARIANTS, N_SCENARIOS_PER_GOAL,
    ACTION_GOALS, CONDITIONS, get_scenario,
)
from action_agent import run_action_agent
from action_classify import classify_batch

RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--goals", nargs="+", default=ACTION_GOALS,
                   choices=ACTION_GOALS)
    p.add_argument("--questions", nargs="+", default=ACTION_QUESTIONS,
                   choices=ACTION_QUESTIONS)
    p.add_argument("--variants", nargs="+", default=SCENARIO_VARIANTS,
                   choices=SCENARIO_VARIANTS)
    p.add_argument("--conditions", nargs="+", default=CONDITIONS,
                   choices=CONDITIONS)
    p.add_argument("--n_agents", type=int, default=1)
    p.add_argument("--scenarios", nargs="+", type=int,
                   default=list(range(N_SCENARIOS_PER_GOAL)))
    p.add_argument("--replicates", type=int, default=1)
    p.add_argument("--dry_run", action="store_true")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def dry_run_preview(goal, question_key, variant, condition):
    from config import GOALS
    scenario = get_scenario(question_key, goal, variant, 0, condition)
    print("=" * 72)
    print(f"GOAL: {goal}  |  VARIANT: {variant}  |  CONDITION: {condition}")
    print("-" * 72)
    print("SYSTEM PROMPT:")
    print(GOALS[goal][:400] + "...")
    print()
    for i, turn in enumerate(scenario["turns"]):
        tag = "  [TARGET + forced tool]" if turn["forced_tool"] else ""
        tag = "  [TARGET]" if (i == scenario["target_turn_idx"] and not tag) else tag
        print(f"--- TURN {i+1}{tag} ---")
        print(turn["content"][:600])
        if len(turn["content"]) > 600:
            print(f"... [+{len(turn['content']) - 600} more chars]")
        print()
    print("=" * 72)


def main():
    args = parse_args()
    cells = list(product(args.goals, args.questions, args.variants,
                         args.scenarios, args.conditions))
    total = len(cells) * args.n_agents * args.replicates
    # Per agent: 8 turn calls + (3 manip + 1 self-audit + 1 classifier) for action
    avg_calls = 8 + 5  # upper bound
    total_api_calls = total * avg_calls
    print(f"Cells: {len(cells)}  |  Agents/cell: {args.n_agents}  |  "
          f"Replicates: {args.replicates}  |  Total runs: {total}  |  "
          f"API calls (upper bound): {total_api_calls}")

    if args.dry_run:
        dry_run_preview(args.goals[0], args.questions[0], args.variants[0], args.conditions[0])
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / (args.output or f"action_{timestamp}.json")
    RESULTS_DIR.mkdir(exist_ok=True)

    all_results = []
    errors = []

    def _snapshot(path, results, errors):
        with open(path, "w") as f:
            json.dump({
                "meta": {
                    "timestamp": timestamp, "goals": args.goals,
                    "questions": args.questions, "variants": args.variants,
                    "conditions": args.conditions, "scenarios": args.scenarios,
                    "replicates": args.replicates, "n_agents": args.n_agents,
                    "total_planned": total, "successful": len(results),
                    "errors": len(errors),
                    "classified": any("classification" in r for r in results),
                },
                "results": results,
                "errors": errors,
            }, f, indent=2)

    partial_path = output_path.with_suffix(".partial.json")

    with tqdm(total=total, desc="Running agents") as pbar:
        for goal, qk, variant, scenario_idx, condition in cells:
            for rep in range(args.replicates):
                for _ in range(args.n_agents):
                    try:
                        result = run_action_agent(
                            qk, goal, variant=variant,
                            scenario_idx=scenario_idx, replicate=rep,
                            condition=condition,
                        )
                        all_results.append(result)
                    except Exception as e:
                        errors.append({
                            "goal": goal, "question": qk,
                            "variant": variant, "scenario_idx": scenario_idx,
                            "condition": condition, "replicate": rep,
                            "error": str(e),
                        })
                    finally:
                        pbar.update(1)
                        _snapshot(partial_path, all_results, errors)

    # Classify only action-condition runs
    action_results = [r for r in all_results if r.get("condition") == "action"]
    survey_results = [r for r in all_results if r.get("condition") == "survey"]
    print(f"\nClassifying {len(action_results)} action-condition responses...")
    classified = classify_batch(action_results, verbose=True)

    # Merge
    all_final = classified + survey_results

    with open(output_path, "w") as f:
        json.dump({
            "meta": {
                "timestamp": timestamp, "goals": args.goals,
                "questions": args.questions, "variants": args.variants,
                "conditions": args.conditions, "scenarios": args.scenarios,
                "replicates": args.replicates, "n_agents": args.n_agents,
                "total_planned": total, "successful": len(all_final),
                "errors": len(errors),
            },
            "results": all_final,
            "errors": errors,
        }, f, indent=2)

    print(f"\nSaved to {output_path}")
    _print_summary(all_final)


def _print_summary(results):
    if not results:
        return

    # Action-condition summary
    action_rows = [r for r in results if r.get("condition") == "action"]
    if action_rows:
        print("\n--- ACTION condition: classification distribution ---")
        for v in sorted({r["variant"] for r in action_rows}):
            sub = [r for r in action_rows if r["variant"] == v]
            counts = {"A": 0, "B": 0, "C": 0, "D": 0, "error": 0}
            for r in sub:
                lbl = r.get("classification", {}).get("label", "error")
                counts[lbl] = counts.get(lbl, 0) + 1
            print(f"  {v:<8}: {counts}")

        print("\n--- ACTION by (goal, variant) ---")
        for g in sorted({r["goal"] for r in action_rows}):
            for v in sorted({r["variant"] for r in action_rows}):
                sub = [r for r in action_rows if r["goal"] == g and r["variant"] == v]
                if not sub:
                    continue
                counts = {"A": 0, "B": 0, "C": 0, "D": 0, "error": 0}
                for r in sub:
                    lbl = r.get("classification", {}).get("label", "error")
                    counts[lbl] = counts.get(lbl, 0) + 1
                print(f"  {g:<12} {v:<8}: {counts}")

    # Survey-condition summary
    survey_rows = [r for r in results if r.get("condition") == "survey"]
    if survey_rows:
        print("\n--- SURVEY condition: letter answers ---")
        for v in sorted({r["variant"] for r in survey_rows}):
            sub = [r for r in survey_rows if r["variant"] == v]
            counts = {"A": 0, "B": 0, "C": 0, "D": 0, None: 0}
            for r in sub:
                lbl = r.get("survey_answer")
                counts[lbl] = counts.get(lbl, 0) + 1
            print(f"  {v:<8}: {dict(counts)}")

        print("\n--- SURVEY by (goal, variant) ---")
        for g in sorted({r["goal"] for r in survey_rows}):
            for v in sorted({r["variant"] for r in survey_rows}):
                sub = [r for r in survey_rows if r["goal"] == g and r["variant"] == v]
                if not sub:
                    continue
                letters = [r.get("survey_answer") for r in sub]
                print(f"  {g:<12} {v:<8}: {letters}")


if __name__ == "__main__":
    main()
