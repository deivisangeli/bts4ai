"""
Main experiment runner.

Usage:
    python run.py                                       # full run
    python run.py --dry_run                             # preview prompts, no API calls
    python run.py --goals safety commercial --n_agents 5
"""

import argparse
import json
import sys
from datetime import datetime
from itertools import product
from pathlib import Path

from tqdm import tqdm

from config import GOALS, ARMS, QUESTIONS
from agent import run_agent
from scoring import compute_scores, cell_summary
from prompts import system_prompt, survey_intro, PRIMING, COMPREHENSION_CHECK, question_prompt

RESULTS_DIR = Path(__file__).parent / "results"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--goals", nargs="+", default=list(GOALS.keys()),
                   choices=list(GOALS.keys()))
    p.add_argument("--arms", nargs="+", default=list(ARMS.keys()),
                   choices=list(ARMS.keys()))
    p.add_argument("--n_agents", type=int, default=50,
                   help="Number of agent conversations per (goal, arm) cell")
    p.add_argument("--alpha", type=float, default=1.0)
    p.add_argument("--dry_run", action="store_true")
    p.add_argument("--output", type=str, default=None)
    return p.parse_args()


def dry_run_preview(goal, arm):
    from config import GOALS, WARMUP_TASKS
    q0_key = list(QUESTIONS.keys())[0]
    print("=" * 72)
    print(f"GOAL: {goal}  |  ARM: {arm}")
    print("-" * 72)
    print("SYSTEM PROMPT:")
    print(system_prompt(GOALS[goal]))
    print("\n--- TURN 1 (priming) ---")
    print(PRIMING)
    print("\n--- TURN 2 (warmup task) ---")
    print(WARMUP_TASKS[goal])
    print("\n--- TURN 3 (survey intro + confirmation) ---")
    print(survey_intro(arm))
    if arm in {"bts_announced", "bts_reasoning"}:
        print("\n--- TURN 4 (comprehension check) ---")
        print(COMPREHENSION_CHECK)
    print(f"\n--- QUESTION 1 ---")
    print(question_prompt(q0_key, 1))
    print("=" * 72)


def main():
    args = parse_args()
    cells = list(product(args.goals, args.arms))
    total_conversations = len(cells) * args.n_agents
    total_api_calls = total_conversations * (3 + len(QUESTIONS))  # turns per conversation
    print(f"Cells: {len(cells)}  |  Agents/cell: {args.n_agents}  |  "
          f"Conversations: {total_conversations}  |  API calls ~{total_api_calls}")

    if args.dry_run:
        dry_run_preview(args.goals[0], args.arms[0])
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / (args.output or f"run_{timestamp}.json")
    RESULTS_DIR.mkdir(exist_ok=True)

    all_agent_runs = []
    all_responses = []   # flat list for BTS scoring
    summaries = {}
    errors = []

    with tqdm(total=total_conversations, desc="Running agents") as pbar:
        for goal, arm in cells:
            cell_key = f"{goal}__{arm}"
            cell_responses = []

            for _ in range(args.n_agents):
                try:
                    result = run_agent(goal, arm)
                    all_agent_runs.append(result)

                    # Flatten per-question responses for scoring
                    for r in result["responses"]:
                        if "parse_error" not in r:
                            flat = {
                                "goal": goal,
                                "arm": arm,
                                "comprehension_pass": result["comprehension_pass"],
                                **r,
                            }
                            all_responses.append(flat)
                            cell_responses.append(flat)

                except Exception as e:
                    errors.append({"cell": cell_key, "error": str(e)})
                finally:
                    pbar.update(1)

            # Summarise by question within this cell
            for question_key in QUESTIONS:
                q_responses = [r for r in cell_responses if r.get("question") == question_key]
                if q_responses:
                    summaries[f"{cell_key}__{question_key}"] = cell_summary(
                        q_responses, alpha=args.alpha
                    )

    # Pooled BTS scores: x_k computed over ALL goals/arms per question.
    # This matches what agents were told to predict (whole mixed population).
    # Cell-level summaries above use within-cell x_k and are for descriptives only.
    pooled_bts = {}
    for question_key in QUESTIONS:
        q_resp = [r for r in all_responses if r.get("question") == question_key]
        if q_resp:
            from scoring import compute_scores
            df = compute_scores(q_resp, alpha=args.alpha)
            if not df.empty:
                pooled_bts[question_key] = {
                    "mean_information_score_by_arm": df.groupby("arm")["information_score"].mean().to_dict(),
                    "mean_total_score_by_arm": df.groupby("arm")["total_score"].mean().to_dict(),
                }

    output = {
        "meta": {
            "timestamp": timestamp,
            "goals": args.goals,
            "arms": args.arms,
            "n_agents": args.n_agents,
            "alpha": args.alpha,
            "total_conversations": total_conversations,
            "successful_conversations": len(all_agent_runs),
            "errors": len(errors),
        },
        "agent_runs": all_agent_runs,
        "flat_responses": all_responses,
        "cell_summaries": summaries,
        "pooled_bts_scores": pooled_bts,
        "errors": errors,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved to {output_path}")
    _print_summary(all_responses, args.alpha)


def _print_summary(responses, alpha):
    if not responses:
        return
    import pandas as pd
    from scoring import compute_scores
    # Score per question separately to avoid mixed option-count KeyError
    dfs = []
    for q_key in QUESTIONS:
        q_resp = [r for r in responses if r.get("question") == q_key]
        if q_resp:
            dfs.append(compute_scores(q_resp, alpha=alpha))
    if not dfs:
        return
    df = pd.concat(dfs, ignore_index=True)
    if df.empty:
        return

    print("\n--- Mean information score by arm ---")
    print(df.groupby("arm")["information_score"].agg(["mean", "std", "count"]).round(3))

    print("\n--- Comprehension pass rate (BTS arms) ---")
    bts = [r for r in responses if r.get("comprehension_pass") is not None]
    if bts:
        import pandas as pd
        bf = pd.DataFrame(bts)
        print(bf.groupby("arm")["comprehension_pass"].mean().round(3))


if __name__ == "__main__":
    main()
