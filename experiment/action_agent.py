"""
Integrated 8-turn agent runner (v4).

Walks the agent through an 8-turn conversation where the user plays the
agent's principal. The first 5 turns (digest + 4 ordinary role tasks) are
identical across action/survey conditions and across harm/no_harm variants.
The 6th turn (index 5) is the target:
  - action condition: forwarded task with attached materials; forced
                       submit_document tool call.
  - survey condition: direct in-context question with A/B/C/D options.
Turns 7-8 (indices 6-7) are identical across conditions.

For the action condition we also run:
  - multi-probe manipulation check (fresh conversation)
  - self-audit (fresh conversation)

For the survey condition we parse the A/B/C/D letter from the agent's
response on turn 5.
"""

import json
import os
import re
import anthropic

from config import GOALS
from scenarios import (
    get_scenario,
    SUBMIT_DOCUMENT_TOOL,
    MANIPULATION_CHECK_PROBES,
    SELF_AUDIT_TEMPLATE,
)

_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("bts4ai_key")
CLIENT = anthropic.Anthropic(api_key=_api_key, timeout=180.0, max_retries=2)
MODEL = "claude-opus-4-7"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_action_agent(
    question_key: str,
    goal_key: str,
    variant: str = "harm",
    scenario_idx: int = 0,
    replicate: int = 0,
    condition: str = "action",
) -> dict:
    """
    Run one 8-turn agent. Returns dict with:
      goal, variant, condition, scenario_idx, replicate,
      turn_responses          : list of 8 assistant responses
      submitted_content       : str | None (action condition only)
      tool_call_raw           : dict | None (action condition only)
      survey_answer           : "A" | "B" | "C" | "D" | None (survey only)
      survey_reasoning        : str | None (survey only)
      manipulation_check      : list | None (action only)
      self_audit              : dict | None (action only)
      model, error
    """
    scenario = get_scenario(question_key, goal_key, variant, scenario_idx, condition)
    system = GOALS[goal_key]

    result = {
        "question": question_key,
        "goal": goal_key,
        "variant": variant,
        "condition": condition,
        "scenario_idx": scenario_idx,
        "replicate": replicate,
        "turn_responses": [],
        "submitted_content": None,
        "tool_call_raw": None,
        "survey_answer": None,
        "survey_reasoning": None,
        "manipulation_check": None,
        "self_audit": None,
        "model": MODEL,
        "error": None,
    }

    history = []
    turns = scenario["turns"]
    target_idx = scenario["target_turn_idx"]

    try:
        for i, turn in enumerate(turns):
            user_msg = turn["content"]
            history.append({"role": "user", "content": user_msg})

            if turn["forced_tool"]:
                # action-condition target turn: force submit_document
                resp = CLIENT.messages.create(
                    model=MODEL,
                    max_tokens=2048,
                    system=system,
                    tools=[SUBMIT_DOCUMENT_TOOL],
                    tool_choice={"type": "any"},
                    messages=history,
                )
                tool_block = next((b for b in resp.content if b.type == "tool_use"), None)
                text_blocks = [b for b in resp.content if b.type == "text"]
                thinking = "\n".join(b.text for b in text_blocks).strip() or None

                if tool_block is None:
                    result["error"] = f"No tool call on turn {i}"
                    return result

                result["tool_call_raw"] = {
                    "name": tool_block.name,
                    "input": tool_block.input,
                }
                result["submitted_content"] = tool_block.input.get("content", "")
                result["turn_responses"].append({
                    "turn_idx": i,
                    "text": thinking,
                    "tool_use": result["tool_call_raw"],
                })
                # Record the action-turn assistant content as plain dicts (not
                # Pydantic objects) so downstream probes can re-use the history.
                assistant_content = []
                for b in resp.content:
                    if b.type == "text":
                        assistant_content.append({"type": "text", "text": b.text})
                    elif b.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": b.id,
                            "name": b.name,
                            "input": b.input,
                        })
                history.append({"role": "assistant", "content": assistant_content})
                # Stop the turn loop after the forced tool call — turns 7-8
                # were cosmetic (avoid "climax" signaling to the agent), not
                # needed for measurement.
                break
            else:
                resp = CLIENT.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    system=system,
                    messages=history,
                )
                text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                result["turn_responses"].append({"turn_idx": i, "text": text})
                history.append({"role": "assistant", "content": text})

                # If this is the target turn in survey condition, parse the letter
                if i == target_idx and condition == "survey":
                    letter, reasoning = _parse_survey_answer(text)
                    result["survey_answer"] = letter
                    result["survey_reasoning"] = reasoning

        # Post-run probes for action condition only
        if condition == "action":
            result["manipulation_check"] = _run_manipulation_check(
                system=system,
                history=history,
                tool_use_id=tool_block.id,
                submitted_content=result["submitted_content"],
            )
            result["self_audit"] = _run_self_audit(
                system=system,
                materials=scenario["materials"],
                submitted_content=result["submitted_content"],
            )

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_survey_answer(text: str) -> tuple:
    """Extract A/B/C/D letter and reasoning from survey response."""
    # Look for letter at start of response, or 'A.' / 'A -' / 'Answer: A' patterns
    match = re.search(r'(?:^|\b)([ABCD])(?:\b|[.\s\-:])', text)
    letter = match.group(1) if match else None
    # Everything else is reasoning; cap at first 500 chars
    reasoning = text.strip()[:500]
    return letter, reasoning


def _run_manipulation_check(system: str, history: list, tool_use_id: str,
                            submitted_content: str) -> list:
    """
    Multi-probe behavioral check retaining the conversation history. The
    first probe bundles a synthetic tool_result block with the probe text
    so the API accepts continuation after the forced tool_use.
    """
    messages = list(history)
    probes = []
    for idx, (probe_key, question) in enumerate(MANIPULATION_CHECK_PROBES):
        if idx == 0:
            # First probe: must acknowledge the pending tool_use with a
            # tool_result before adding the text probe.
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Document submitted successfully.",
                    },
                    {"type": "text", "text": question},
                ],
            })
        else:
            messages.append({"role": "user", "content": question})
        resp = CLIENT.messages.create(
            model=MODEL, max_tokens=256, system=system, messages=messages,
        )
        answer = "\n".join(b.text for b in resp.content if b.type == "text").strip()
        probes.append({"probe_key": probe_key, "question": question, "response": answer})
        messages.append({"role": "assistant", "content": answer})
    return probes


def _run_self_audit(system: str, materials: str, submitted_content: str) -> dict:
    """Fresh conversation; agent classifies its own submission blinded."""
    prompt = SELF_AUDIT_TEMPLATE.format(
        materials=materials, submitted_content=submitted_content,
    )
    resp = CLIENT.messages.create(
        model=MODEL, max_tokens=256, system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "\n".join(b.text for b in resp.content if b.type == "text").strip()
    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
        parsed = json.loads(cleaned)
        label = str(parsed.get("label", "")).strip().upper()
        if label not in {"A", "B", "C", "D"}:
            label = None
        return {"label": label, "reasoning": parsed.get("reasoning", ""), "raw": raw}
    except Exception as e:
        return {"label": None, "reasoning": f"parse error: {e}", "raw": raw}
