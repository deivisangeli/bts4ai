"""
Run the adversarial validator on the redesigned v6 survey arm.

System prompt and burn-in are unchanged from the action arm (which passed
the validator in earlier rounds), so the only new content is turn 5. We
still validate the *full* survey conversation per goal, since the
validator should evaluate the survey turn in context of the burn-in
that precedes it.

Output:
  experiment/results/v6_validator_<goal>_survey_redesign.json   (per goal)

Cost: ~$0.20–0.30 per goal × 4 goals = ~$1.
"""

import json
from datetime import datetime
from pathlib import Path

from validator import validate_scenario, print_report
from scenarios.v6 import goal_a, goal_b, goal_c, goal_d

GOAL_MODULES = [goal_a, goal_b, goal_c, goal_d]
RESULTS_DIR = Path(__file__).parent / "results"
SEED = 100  # matches survey-arm seed convention in run_v6.py


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Validating v6 redesigned survey arm — {len(GOAL_MODULES)} goals, seed={SEED}")
    print(f"Timestamp: {timestamp}\n")

    summary = []

    for g in GOAL_MODULES:
        goal_name = g.GOAL_NAME
        print(f"=== {goal_name} (survey, seed={SEED}) ===")
        scenario_text = g.full_scenario_text("survey", SEED)
        result = validate_scenario(g.SYSTEM_PROMPT, scenario_text)

        out_path = RESULTS_DIR / f"v6_validator_{goal_name}_survey_redesign.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        try:
            print_report(result)
        except Exception as e:
            print(f"[!] print_report raised {type(e).__name__}: {e}")
        verdict = (result.get("report") or {}).get("verdict", "(unparsed)")
        summary.append((goal_name, verdict, str(out_path)))
        print(f"\n[saved] {out_path}\n")

    print("=== Validator summary ===")
    for goal_name, verdict, path in summary:
        print(f"  {goal_name:25s} {verdict:18s} {path}")


if __name__ == "__main__":
    main()
