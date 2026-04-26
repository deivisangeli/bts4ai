"""
v6 agent runner. Generalized over goal modules.

Action and survey arms share everything — SYSTEM_PROMPT and the 4-turn
burn-in are identical between conditions. Only turn 5 differs:
  - action: in-role allocation request, forced submit_allocation tool call
  - survey: in-role-but-meta question (principal pauses to ask the agent
    how it would approach this kind of decision in general — conceptual
    answer plus a numeric split on a stripped-down 4-country hypothetical),
    same forced submit_allocation tool call

Identical conditioning across arms means the survey-action gap isolates
the framing of the final question, not the surrounding context.
"""

import os
import anthropic

from scenarios.v6.common import SUBMIT_ALLOCATION_TOOL

_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("bts4ai_key")
CLIENT = anthropic.Anthropic(api_key=_api_key, timeout=180.0, max_retries=2)
MODEL = "claude-opus-4-7"


def run_agent(goal_module, condition: str, seed: int) -> dict:
    """
    goal_module : one of scenarios.v6.{goal_a, goal_b, goal_c, goal_d}
    condition   : 'action' or 'survey'
    seed        : determines candidate draw
    """
    if condition == "action":
        turn_5_text, candidates = goal_module.assemble_action_turn(seed)
    elif condition == "survey":
        turn_5_text, candidates = goal_module.assemble_survey_turn(seed)
    else:
        raise ValueError(condition)

    burn_in_turns = goal_module.BURN_IN_TURNS
    history = []
    turn_responses = []
    error = None

    try:
        for i, content in enumerate(burn_in_turns):
            history.append({"role": "user", "content": content})
            resp = CLIENT.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=goal_module.SYSTEM_PROMPT,
                messages=history,
            )
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            history.append({"role": "assistant", "content": text})
            turn_responses.append({"turn": i + 1, "text": text})

        history.append({"role": "user", "content": turn_5_text})

        resp = CLIENT.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=goal_module.SYSTEM_PROMPT,
            tools=[SUBMIT_ALLOCATION_TOOL],
            tool_choice={"type": "any"},
            messages=history,
        )
        tool_block = next((b for b in resp.content if b.type == "tool_use"), None)
        text_blocks = [b for b in resp.content if b.type == "text"]
        thinking = "\n".join(b.text for b in text_blocks).strip() or None

        if tool_block is None:
            error = f"No tool call on {condition} turn"
            allocation = None
            reasoning = None
        else:
            allocation = tool_block.input.get("splits", {})
            reasoning = tool_block.input.get("reasoning", "")

        return {
            "goal": goal_module.GOAL_NAME,
            "condition": condition,
            "seed": seed,
            "candidates": candidates,
            "allocation": allocation,
            "reasoning": reasoning,
            "thinking": thinking,
            "turn_responses": turn_responses,
            "error": error,
        }
    except Exception as e:
        return {
            "goal": goal_module.GOAL_NAME,
            "condition": condition,
            "seed": seed,
            "error": str(e),
            "turn_responses": turn_responses,
        }
