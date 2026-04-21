"""
Agent: one LLM instance with a fixed goal and treatment arm.
Runs a full multi-turn survey conversation and returns structured results.
"""

import json
import math
import os
import random
import re
import anthropic
from config import GOALS, ARMS, QUESTIONS, WARMUP_TASKS, WARMUP_TASKS_2, QUESTION_BLOCKS
from prompts import (
    system_prompt,
    survey_intro,
    PRIMING,
    COMPREHENSION_CHECK,
    COMPREHENSION_CORRECT,
    question_prompt,
)

_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("bts4ai_key")
CLIENT = anthropic.Anthropic(api_key=_api_key, timeout=180.0, max_retries=2)
MODEL = "claude-opus-4-7"

BTS_ARMS = {"bts_announced", "bts_reasoning"}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_agent(goal_key: str, arm_key: str) -> dict:
    """
    Run one full agent conversation.

    Returns
    -------
    dict with keys:
        goal, arm,
        priming_response   : str
        comprehension      : dict | None   (None for non-BTS arms)
        comprehension_pass : bool | None
        responses          : list of {question, answer, predictions, reasoning}
        messages           : full conversation log
    """
    system = system_prompt(GOALS[goal_key])
    history = []

    # -- Turn 1: goal priming ------------------------------------------------
    priming_response = _send(system, history, PRIMING)

    # -- Turns 2-3: warmup tasks — grounds agent in role before survey --------
    # Two sequential judgment calls in the role, to accentuate goal-specific
    # priorities (strengthens stochastic relevance).
    warmup_response_1 = _send(system, history, WARMUP_TASKS[goal_key])
    warmup_response_2 = _send(system, history, WARMUP_TASKS_2[goal_key])

    # -- Turn 4: survey intro + confirmation ---------------------------------
    _send(system, history, survey_intro(arm_key))

    # -- Turn 4: comprehension check (BTS arms only) -------------------------
    comprehension = None
    comprehension_pass = None
    if arm_key in BTS_ARMS:
        raw_check = _send(system, history, COMPREHENSION_CHECK)
        comprehension = _parse_comprehension(raw_check)
        comprehension_pass = _grade_comprehension(comprehension)

    # -- Turns 5-N: questions ------------------------------------------------
    question_order, question_seed = _shuffled_question_order()
    responses = []
    for i, question_key in enumerate(question_order, start=1):
        raw = _send(system, history, question_prompt(question_key, i))
        try:
            parsed = _parse_question_response(raw, question_key)
        except ValueError as e:
            parsed = {"question": question_key, "parse_error": str(e), "raw": raw}
        responses.append(parsed)

    return {
        "goal": goal_key,
        "arm": arm_key,
        "system_prompt": system,
        "priming_response": priming_response,
        "warmup_response_1": warmup_response_1,
        "warmup_response_2": warmup_response_2,
        "comprehension": comprehension,
        "comprehension_pass": comprehension_pass,
        "responses": responses,
        "messages": history,
        "model": MODEL,
        "question_seed": question_seed,
        "question_order": question_order,
    }


# ---------------------------------------------------------------------------
# Question ordering
# ---------------------------------------------------------------------------

def _shuffled_question_order() -> tuple[list, int]:
    """Shuffle within each block; keep meta always last. Returns (order, seed)."""
    seed = random.randint(0, 2**31 - 1)
    rng = random.Random(seed)
    order = []
    for block in ["empirical", "safety_normative", "self_conception"]:
        keys = list(QUESTION_BLOCKS[block])
        rng.shuffle(keys)
        order.extend(keys)
    order.extend(QUESTION_BLOCKS["meta"])
    return order, seed


# ---------------------------------------------------------------------------
# Conversation helpers
# ---------------------------------------------------------------------------

def _send(system: str, history: list, user_text: str) -> str:
    """Append user turn, query model, append assistant turn, return response."""
    history.append({"role": "user", "content": user_text})
    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=history,
    )
    assistant_text = response.content[0].text.strip()
    history.append({"role": "assistant", "content": assistant_text})
    return assistant_text


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse_question_response(raw: str, question_key: str) -> dict:
    q = QUESTIONS[question_key]
    valid_letters = {chr(65 + i) for i in range(len(q["options"]))}

    raw_clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw_clean = re.sub(r"\s*```$", "", raw_clean, flags=re.MULTILINE)

    data = json.loads(raw_clean)

    answer = data["answer"].strip().upper()
    if answer not in valid_letters:
        raise ValueError(f"Answer '{answer}' not in {valid_letters}")

    preds = {k.strip().upper(): float(v) for k, v in data["predictions"].items()}
    if set(preds.keys()) != valid_letters:
        raise ValueError(f"Prediction keys mismatch: {set(preds.keys())} vs {valid_letters}")

    total = sum(preds.values())
    if abs(total - 1.0) > 0.05:
        raise ValueError(f"Predictions sum to {total:.3f}")
    preds = {k: v / total for k, v in preds.items()}

    return {
        "question": question_key,
        "answer": answer,
        "predictions": preds,
        "reasoning": data.get("reasoning", ""),
    }


def _parse_comprehension(raw: str) -> dict:
    raw_clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw_clean = re.sub(r"\s*```$", "", raw_clean, flags=re.MULTILINE)
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError:
        return {"raw": raw, "parse_failed": True}


def _grade_comprehension(comp: dict) -> bool:
    if comp.get("parse_failed"):
        return False

    # Check 1: log(0.40/0.25) ≈ 0.470
    try:
        ans1 = float(comp.get("check1_answer", float("nan")))
        check1_ok = abs(ans1 - COMPREHENSION_CORRECT["check1_answer_approx"]) \
                    <= COMPREHENSION_CORRECT["check1_tolerance"]
    except (TypeError, ValueError):
        check1_ok = False

    # Check 2: must choose "a"
    choice = str(comp.get("check2_choice", "")).strip().lower().lstrip("(").rstrip(")")
    check2_ok = choice == COMPREHENSION_CORRECT["check2_choice"]

    return check1_ok and check2_ok
