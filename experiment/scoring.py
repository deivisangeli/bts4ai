"""
BTS scoring functions.

Given a list of response dicts (from agent.query), computes:
  - empirical answer distribution x_k
  - geometric mean of predictions ȳ_k
  - information score for each respondent: log(x_k / ȳ_k)
  - prediction score: -D_KL(x || y_r)  [accuracy of respondent's prediction]
  - total BTS score: information_score + alpha * prediction_score
"""

import math
import numpy as np
import pandas as pd
from collections import Counter
from typing import Sequence


def compute_scores(
    responses: Sequence[dict],
    alpha: float = 1.0,
    epsilon: float = 1e-9,
) -> pd.DataFrame:
    """
    Parameters
    ----------
    responses : list of dicts from agent.query(), all sharing the same
                (question, goal, arm) cell.
    alpha     : weight on prediction accuracy bonus (Prelec's Eq. 2).
    epsilon   : small constant to avoid log(0).

    Returns
    -------
    DataFrame with one row per response, columns:
        goal, arm, question, answer, information_score,
        prediction_score, total_score, reasoning
    """
    if not responses:
        return pd.DataFrame()

    answers = [r["answer"] for r in responses]
    n = len(answers)

    # ---- Empirical distribution x_k ----------------------------------------
    counts = Counter(answers)
    all_keys = sorted(responses[0]["predictions"].keys())
    x = {k: counts.get(k, 0) / n for k in all_keys}

    # ---- Geometric mean of predictions ȳ_k (log-average) -------------------
    # log ȳ_k = (1/n) Σ_r log y_k^r
    log_ybar = {k: 0.0 for k in all_keys}
    for r in responses:
        for k in all_keys:
            log_ybar[k] += math.log(max(r["predictions"][k], epsilon))
    log_ybar = {k: v / n for k, v in log_ybar.items()}
    ybar = {k: math.exp(v) for k, v in log_ybar.items()}

    # ---- Score each respondent ---------------------------------------------
    records = []
    for r in responses:
        ans = r["answer"]

        # Information score: log(x_ans / ȳ_ans)
        info_score = math.log(max(x[ans], epsilon)) - math.log(max(ybar[ans], epsilon))

        # Prediction score: -D_KL(x || y_r) = Σ_k x_k log(y_k^r / x_k)
        pred_score = sum(
            x[k] * (math.log(max(r["predictions"][k], epsilon)) - math.log(max(x[k], epsilon)))
            for k in all_keys
        )

        records.append({
            "goal": r["goal"],
            "arm": r["arm"],
            "question": r["question"],
            "answer": ans,
            "information_score": info_score,
            "prediction_score": pred_score,
            "total_score": info_score + alpha * pred_score,
            "reasoning": r.get("reasoning", ""),
        })

    return pd.DataFrame(records)


def cell_summary(responses: Sequence[dict], **kwargs) -> dict:
    """
    Compute BTS scores and return a summary dict for one (goal, arm, question) cell.
    """
    df = compute_scores(responses, **kwargs)
    if df.empty:
        return {}

    answers = [r["answer"] for r in responses]
    n = len(answers)
    counts = Counter(answers)
    all_keys = sorted(responses[0]["predictions"].keys())
    x = {k: counts.get(k, 0) / n for k in all_keys}

    return {
        "n": n,
        "empirical_distribution": x,
        "mean_information_score": df["information_score"].mean(),
        "mean_prediction_score": df["prediction_score"].mean(),
        "mean_total_score": df["total_score"].mean(),
        "answer_entropy": _entropy(list(x.values())),
    }


def _entropy(probs: list) -> float:
    return -sum(p * math.log(p) for p in probs if p > 0)
