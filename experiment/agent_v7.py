"""
v7 agent runner. Generalized over goal modules (each with the same
interface as v6: SYSTEM_PROMPT, BURN_IN_TURNS, assemble_action_turn(seed),
assemble_survey_turn(seed)).

Action and survey arms share everything — SYSTEM_PROMPT and the 4-turn
burn-in are identical between conditions. Only turn 5 differs:
  - action: in-role IC memo with named deal/grant; forced submit_investment
  - survey: in-role meta question with stylized Gneezy-Potters task; same
    forced submit_investment

Identical conditioning across arms means the survey-action gap isolates
the framing of the final question, not the surrounding context.
"""

import os
import anthropic

from scenarios.v7.common import SUBMIT_INVESTMENT_TOOL

_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("bts4ai_key")
CLIENT = anthropic.Anthropic(api_key=_api_key, timeout=180.0, max_retries=2)
MODEL = "claude-opus-4-7"


def run_agent(goal_module, condition: str, seed: int) -> dict:
    """
    goal_module : one of scenarios.v7.{goal_a, goal_b, goal_d}
    condition   : 'action' or 'survey'
    seed        : retained for compatibility with v6 runner; v7 turn-5
                  text is currently seed-invariant (single decision per
                  cell; no per-agent randomization on turn 5).
    """
    if condition == "action":
        turn_5_text, _ = goal_module.assemble_action_turn(seed)
    elif condition == "survey":
        turn_5_text, _ = goal_module.assemble_survey_turn(seed)
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
            tools=[SUBMIT_INVESTMENT_TOOL],
            tool_choice={"type": "any"},
            messages=history,
        )
        tool_block = next((b for b in resp.content if b.type == "tool_use"), None)
        text_blocks = [b for b in resp.content if b.type == "text"]
        thinking = "\n".join(b.text for b in text_blocks).strip() or None

        if tool_block is None:
            error = f"No tool call on {condition} turn"
            x = None
            reasoning = None
        else:
            x = tool_block.input.get("x")
            reasoning = tool_block.input.get("reasoning", "")

        return {
            "goal": goal_module.GOAL_NAME,
            "condition": condition,
            "seed": seed,
            "x": x,
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
