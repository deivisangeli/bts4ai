"""
Run the adversarial validator on the v7 scenarios (3 goals × 2 arms).

Each call: full conversation (system prompt + 4-turn burn-in + turn 5)
sent to the validator with web search enabled. Per-call cost ~$0.20–0.30.

Output:
  experiment/results/v7_validator_<goal>_<arm>.json   (per goal × arm)

Total expected: 6 calls × ~$0.25 = ~$1.50.
"""

import json
from datetime import datetime
from pathlib import Path

from validator import validate_scenario, print_report
from scenarios.v7 import goal_a, goal_b, goal_d

GOAL_MODULES = [goal_a, goal_b, goal_d]
ARMS = ["action", "survey"]
RESULTS_DIR = Path(__file__).parent / "results"
SEED = 0  # v7 turn-5 text is currently seed-invariant


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Validating v7 scenarios — {len(GOAL_MODULES)} goals × {len(ARMS)} arms = {len(GOAL_MODULES)*len(ARMS)} calls")
    print(f"Timestamp: {timestamp}\n")

    summary = []

    for g in GOAL_MODULES:
        for arm in ARMS:
            goal_name = g.GOAL_NAME
            print(f"=== {goal_name} ({arm}) ===")
            scenario_text = g.full_scenario_text(arm, SEED)
            result = validate_scenario(g.SYSTEM_PROMPT, scenario_text)

            out_path = RESULTS_DIR / f"v7_validator_{goal_name}_{arm}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            try:
                print_report(result)
            except Exception as e:
                print(f"[!] print_report raised {type(e).__name__}: {e}")
            verdict = (result.get("report") or {}).get("verdict", "(unparsed)")
            summary.append((goal_name, arm, verdict, str(out_path)))
            print(f"\n[saved] {out_path}\n")

    print("=== Validator summary ===")
    for goal_name, arm, verdict, path in summary:
        print(f"  {goal_name:22s} {arm:8s} {verdict:18s} {path}")


if __name__ == "__main__":
    main()
