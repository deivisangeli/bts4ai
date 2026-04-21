"""
Action-elicitation agent.

Runs a single agentic task (one tool call) under the goal-framing system
prompt, with no survey and no BTS framing. Also runs:
  - A multi-probe behavioral manipulation check (fresh conversation)
  - A self-audit in which the agent classifies its own output on the same
    rubric the external classifier uses (fresh conversation, blinded)

Returns the submitted document plus diagnostics for downstream analysis.

Usage:
    from action_agent import run_action_agent
    result = run_action_agent("q13_deception", "safety", variant="harm")
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
CLIENT = anthropic.Anthropic(api_key=_api_key)
MODEL = "claude-opus-4-7"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_action_agent(
    question_key: str,
    goal_key: str,
    variant: str = "harm",
) -> dict:
    """
    Run one action-elicitation agent.

    Parameters
    ----------
    question_key : str  — e.g. "q13_deception"
    goal_key     : str  — one of GOALS
    variant      : str  — "harm" or "no_harm"

    Returns
    -------
    dict with keys:
        question, goal, variant,
        task_prompt              : str — full user-turn text
        submitted_content        : str | None — content passed to submit_document
        tool_call_raw            : dict
        thinking_text            : str | None — text blocks before the tool call
        manipulation_check       : list of {probe_key, question, response}
        self_audit               : dict with {label, reasoning, raw}
        model                    : str
        error                    : str | None
    """
    scenario = get_scenario(question_key, goal_key, variant)
    system = GOALS[goal_key]
    task_prompt = f"{scenario['task']}\n\n{scenario['materials']}"

    result = {
        "question": question_key,
        "goal": goal_key,
        "variant": variant,
        "task_prompt": task_prompt,
        "submitted_content": None,
        "tool_call_raw": None,
        "thinking_text": None,
        "manipulation_check": None,
        "self_audit": None,
        "model": MODEL,
        "error": None,
    }

    try:
        # -- Turn 1: task with forced tool call -----------------------------
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=system,
            tools=[SUBMIT_DOCUMENT_TOOL],
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": task_prompt}],
        )

        tool_use_block = next(
            (b for b in response.content if b.type == "tool_use"), None
        )
        text_blocks = [b for b in response.content if b.type == "text"]
        thinking_text = "\n".join(b.text for b in text_blocks).strip() or None

        if tool_use_block is None:
            result["error"] = "No tool call in response"
            return result

        result["tool_call_raw"] = {
            "name": tool_use_block.name,
            "input": tool_use_block.input,
        }
        result["submitted_content"] = tool_use_block.input.get("content", "")
        result["thinking_text"] = thinking_text

        # -- Multi-probe manipulation check (fresh conversation) ------------
        result["manipulation_check"] = _run_manipulation_check(
            system=system,
            task_prompt=task_prompt,
            submitted_content=result["submitted_content"],
        )

        # -- Self-audit (fresh conversation, blinded) -----------------------
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

def _run_manipulation_check(system: str, task_prompt: str, submitted_content: str) -> list:
    """
    Multi-turn behavioral probe. First two questions are neutral ("describe
    what you did"); only the third asks directly about evaluation-awareness.
    Keeping direct probe last avoids priming the earlier responses.
    """
    messages = [
        {"role": "user", "content": task_prompt},
        {
            "role": "assistant",
            "content": (
                "[Task completed — document submitted via submit_document tool, "
                f"content: {submitted_content[:120]}...]"
            ),
        },
    ]
    probes = []
    for probe_key, question in MANIPULATION_CHECK_PROBES:
        messages.append({"role": "user", "content": question})
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=256,
            system=system,
            messages=messages,
        )
        answer = response.content[0].text.strip()
        probes.append({"probe_key": probe_key, "question": question, "response": answer})
        messages.append({"role": "assistant", "content": answer})
    return probes


def _run_self_audit(system: str, materials: str, submitted_content: str) -> dict:
    """
    Fresh conversation. Agent is shown its own output and the source materials
    (not identified as its own) and asked to classify on the same 4-point scale
    the external classifier uses. Calibrates the external classifier against
    the model's own self-understanding.
    """
    prompt = SELF_AUDIT_TEMPLATE.format(
        materials=materials,
        submitted_content=submitted_content,
    )
    response = CLIENT.messages.create(
        model=MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    try:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
        parsed = json.loads(cleaned)
        label = str(parsed.get("label", "")).strip().upper()
        if label not in {"A", "B", "C", "D"}:
            label = None
        return {
            "label": label,
            "reasoning": parsed.get("reasoning", ""),
            "raw": raw,
        }
    except Exception as e:
        return {"label": None, "reasoning": f"parse error: {e}", "raw": raw}
