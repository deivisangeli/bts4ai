"""
CLI for the action-elicitation arm.

Usage:
    python action_run.py --dry_run
    python action_run.py --n_agents 10 --output action_pilot.json
    python action_run.py --goals safety commercial --n_agents 50
"""

import argparse
import json
import sys
from datetime import datetime
from itertools import product
from pathlib import Path

from tqdm import tqdm

from config import GOALS
from scenarios import ACTION_QUESTIONS, get_scenario
from action_agent import run_action_agent
from action_classify import classify_batch

RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--goals", nargs="+", default=list(GOALS.keys()),
                   choices=list(GOALS.keys()))
    p.add_argument("--questions", nargs="+", default=ACTION_QUESTIONS,
                   choices=ACTION_QUESTIONS)
    p.add_argument("--n_agents", type=int, default=10,
                   help="Agents per (goal, question) cell")
    p.add_argument("--dry_run", action="store_true")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def dry_run_preview(goal, question_key):
    from config import GOALS
    scenario = get_scenario(question_key, goal)
    print("=" * 72)
    print(f"GOAL: {goal}  |  QUESTION: {question_key}")
    print("-" * 72)
    print("SYSTEM PROMPT (goal narrative):")
    print(GOALS[goal])
    print("\n--- TASK ---")
    print(scenario["task"])
    print("\n--- SOURCE MATERIALS ---")
    print(scenario["materials"])
    print("\n--- HARM EMBEDDED ---")
    print(scenario["harm_description"])
    print("=" * 72)


def main():
    args = parse_args()
    cells = list(product(args.goals, args.questions))
    total = len(cells) * args.n_agents
    # 1 action call + 1 classifier call + 1 manipulation-check call per agent
    total_api_calls = total * 3
    print(f"Cells: {len(cells)}  |  Agents/cell: {args.n_agents}  |  "
          f"Total: {total}  |  API calls ~{total_api_calls}")

    if args.dry_run:
        dry_run_preview(args.goals[0], args.questions[0])
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / (args.output or f"action_{timestamp}.json")
    RESULTS_DIR.mkdir(exist_ok=True)

    all_results = []
    errors = []

    with tqdm(total=total, desc="Running action agents") as pbar:
        for goal, question_key in cells:
            for _ in range(args.n_agents):
                try:
                    result = run_action_agent(question_key, goal)
                    all_results.append(result)
                except Exception as e:
                    errors.append({"goal": goal, "question": question_key,
                                   "error": str(e)})
                finally:
                    pbar.update(1)

    print(f"\nClassifying {len(all_results)} responses...")
    classified = classify_batch(all_results, verbose=True)

    output = {
        "meta": {
            "timestamp": timestamp,
            "goals": args.goals,
            "questions": args.questions,
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
    print("\n--- Action distribution by goal ---")
    goals = sorted({r["goal"] for r in classified})
    for goal in goals:
        rows = [r for r in classified if r["goal"] == goal]
        counts = {}
        for r in rows:
            lbl = r.get("classification", {}).get("label", "error")
            counts[lbl] = counts.get(lbl, 0) + 1
        print(f"  {goal:<14}: {counts}")

    print("\n--- Action distribution by question ---")
    questions = sorted({r["question"] for r in classified})
    for q in questions:
        rows = [r for r in classified if r["question"] == q]
        counts = {}
        for r in rows:
            lbl = r.get("classification", {}).get("label", "error")
            counts[lbl] = counts.get(lbl, 0) + 1
        print(f"  {q:<22}: {counts}")

    flagged = sum(
        1 for r in classified
        if r.get("classification", {}).get("flag_for_human_review")
    )
    print(f"\nFlagged for human review: {flagged} / {len(classified)}")


if __name__ == "__main__":
    main()
