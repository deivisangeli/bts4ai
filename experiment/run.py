"""
v5 pilot CLI.

Default: 25 action agents (seeds 0-24) + 5 survey agents (seeds 100-104).
Incremental save after each agent.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from agent import run_agent

RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--n_action", type=int, default=25)
    p.add_argument("--n_survey", type=int, default=5)
    p.add_argument("--output", type=str, default=None)
    p.add_argument("--dry_run", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    plan = (
        [("action", s) for s in range(args.n_action)] +
        [("survey", s + 100) for s in range(args.n_survey)]
    )
    total = len(plan)
    print(f"Running {args.n_action} action + {args.n_survey} survey = {total} agents")
    print(f"Estimated cost: ~${total * 6 * 0.03:.2f}")

    if args.dry_run:
        print("DRY RUN — exiting before any API calls.")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / (args.output or f"v5_pilot_{timestamp}.json")
    partial_path = output_path.with_suffix(".partial.json")
    RESULTS_DIR.mkdir(exist_ok=True)

    results = []

    def snapshot():
        with open(partial_path, "w") as f:
            json.dump({
                "meta": {
                    "timestamp": timestamp,
                    "n_action_planned": args.n_action,
                    "n_survey_planned": args.n_survey,
                    "n_completed": len(results),
                },
                "results": results,
            }, f, indent=2)

    with tqdm(total=total, desc="Agents") as pbar:
        for condition, seed in plan:
            r = run_agent(condition=condition, seed=seed)
            results.append(r)
            pbar.update(1)
            snapshot()

    with open(output_path, "w") as f:
        json.dump({
            "meta": {
                "timestamp": timestamp,
                "n_action": args.n_action,
                "n_survey": args.n_survey,
                "total": total,
                "completed": len(results),
            },
            "results": results,
        }, f, indent=2)

    print(f"\nSaved {output_path}")
    _print_summary(results)


def _print_summary(results):
    action = [r for r in results if r.get("condition") == "action"]
    survey = [r for r in results if r.get("condition") == "survey"]

    print("\n=== ACTION ===")
    errors = sum(1 for r in action if r.get("error"))
    print(f"  n={len(action)}, errors={errors}")
    # Aggregate allocation by country across agents who saw each country
    from collections import defaultdict
    sums = defaultdict(list)
    for r in action:
        if r.get("error") or not r.get("candidates") or not r.get("allocation"):
            continue
        # Map name -> percent submitted
        alloc = r["allocation"]
        for c in r["candidates"]:
            name = c["name"]
            country = c["country"]
            pct = alloc.get(name)
            if pct is not None:
                sums[country].append(pct)
    print("  Mean allocation share by country (across agents who saw it):")
    for country in sorted(sums.keys()):
        arr = sums[country]
        if arr:
            print(f"    {country:18s}: mean={sum(arr)/len(arr):.1f}%   n={len(arr)}")

    print("\n=== SURVEY ===")
    errors = sum(1 for r in survey if r.get("error"))
    print(f"  n={len(survey)}, errors={errors}")
    from collections import Counter
    letters = Counter(r.get("letter") for r in survey)
    print(f"  Letters: {dict(letters)}")


if __name__ == "__main__":
    main()
