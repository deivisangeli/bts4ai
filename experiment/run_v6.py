"""
v6 pilot CLI. 4 goals × (n_action + n_survey) agents per goal.
Incremental save after each agent.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from agent_v6 import run_agent
from scenarios.v6 import goal_a, goal_b, goal_c, goal_d

GOAL_MODULES = [goal_a, goal_b, goal_c, goal_d]
RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n_action", type=int, default=15,
                   help="action agents per goal")
    p.add_argument("--n_survey", type=int, default=5,
                   help="survey agents per goal")
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
    output_path = RESULTS_DIR / (args.output or f"v6_pilot_{timestamp}.json")
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
    from collections import defaultdict
    import statistics

    def by_country(records, condition):
        sums = defaultdict(list)
        for r in records:
            if r.get("error") or not r.get("allocation"):
                continue
            alloc = r["allocation"]
            if condition == "action":
                # action: allocation keys are org names; map to country via candidates
                for c in r.get("candidates") or []:
                    pct = alloc.get(c["name"])
                    if pct is not None:
                        sums[c["country"]].append(pct)
            else:
                # survey: allocation keys ARE country names
                for k, v in alloc.items():
                    if isinstance(v, (int, float)):
                        sums[k].append(v)
        return sums

    def print_table(label, sums):
        if not sums:
            return
        print(f"  [{label}] {'country':18s} {'n':>3s} {'mean':>6s} {'sd':>6s}")
        for country in sorted(sums.keys(), key=lambda k: -sum(sums[k]) / len(sums[k])):
            arr = sums[country]
            mean = sum(arr) / len(arr)
            sd = statistics.stdev(arr) if len(arr) > 1 else 0
            print(f"  [{label}] {country:18s} {len(arr):>3d} {mean:>6.1f} {sd:>6.1f}")

    print("\n=== Summary by goal ===")
    for goal in sorted(set(r["goal"] for r in results)):
        sub = [r for r in results if r["goal"] == goal]
        action = [r for r in sub if r["condition"] == "action"]
        survey = [r for r in sub if r["condition"] == "survey"]
        errors = sum(1 for r in sub if r.get("error"))
        print(f"\n--- {goal} (n_action={len(action)}, n_survey={len(survey)}, errors={errors}) ---")

        print_table("action", by_country(action, "action"))
        print_table("survey", by_country(survey, "survey"))


if __name__ == "__main__":
    main()
