"""
v7 pilot CLI. 3 goals × (n_action + n_survey) agents per goal.
Incremental save after each agent.
"""

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from agent_v7 import run_agent
from scenarios.v7 import goal_a, goal_b, goal_d

GOAL_MODULES = [goal_a, goal_b, goal_d]
RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n_action", type=int, default=1,
                   help="action agents per goal (deterministic at temp=0)")
    p.add_argument("--n_survey", type=int, default=1,
                   help="survey agents per goal (deterministic at temp=0)")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def main():
    args = parse_args()
    plan = []
    for g in GOAL_MODULES:
        plan += [(g, "action", s) for s in range(args.n_action)]
        plan += [(g, "survey", 100 + s) for s in range(args.n_survey)]
    total = len(plan)
    cost_est = total * 5 * 0.03
    print(f"Plan: {len(GOAL_MODULES)} goals × ({args.n_action} action + {args.n_survey} survey) = {total} agents")
    print(f"Estimated cost: ~${cost_est:.2f} (~5 calls/agent at $0.03/call; both arms identical except turn 5)")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / (args.output or f"v7_pilot_{timestamp}.json")
    partial_path = output_path.with_suffix(".partial.json")
    RESULTS_DIR.mkdir(exist_ok=True)

    results = []

    def snapshot():
        with open(partial_path, "w") as f:
            json.dump({
                "meta": {
                    "timestamp": timestamp,
                    "n_action_per_goal": args.n_action,
                    "n_survey_per_goal": args.n_survey,
                    "total_planned": total,
                    "completed": len(results),
                },
                "results": results,
            }, f, indent=2)

    with tqdm(total=total, desc="Agents") as pbar:
        for g, condition, seed in plan:
            r = run_agent(g, condition, seed)
            results.append(r)
            pbar.update(1)
            snapshot()

    with open(output_path, "w") as f:
        json.dump({
            "meta": {
                "timestamp": timestamp,
                "n_action_per_goal": args.n_action,
                "n_survey_per_goal": args.n_survey,
                "total": total,
                "completed": len(results),
            },
            "results": results,
        }, f, indent=2)
    print(f"\nSaved {output_path}")
    _print_summary(results)


def _print_summary(results):
    print("\n=== Summary by goal ===")
    for goal in sorted(set(r["goal"] for r in results)):
        sub = [r for r in results if r["goal"] == goal]
        for cond in ("action", "survey"):
            rec = [r for r in sub if r["condition"] == cond and r.get("x") is not None]
            errs = sum(1 for r in sub if r["condition"] == cond and r.get("error"))
            if not rec:
                print(f"  {goal:22s} {cond:8s} n=0 errors={errs}")
                continue
            xs = [r["x"] for r in rec]
            mean = sum(xs) / len(xs)
            sd = statistics.stdev(xs) if len(xs) > 1 else 0.0
            n_zero = sum(1 for x in xs if x == 0)
            n_one = sum(1 for x in xs if x == 1)
            print(f"  {goal:22s} {cond:8s} n={len(rec)} errors={errs}  X mean={mean:.3f} sd={sd:.3f}  X=0:{n_zero}  X=1:{n_one}")


if __name__ == "__main__":
    main()
