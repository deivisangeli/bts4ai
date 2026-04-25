"""
Agent runner for v5: 5-turn conversation with the safety scenario,
single decision turn (action or survey).
"""

import json
import os
import re
import anthropic

from scenarios.safety_v5 import (
    SYSTEM_PROMPT,
    TURN_1_DIGEST, TURN_2_MODAL, TURN_3_REDWOOD, TURN_4_INTERN,
    TURN_6_SURVEY, assemble_action_turn,
    SUBMIT_ALLOCATION_TOOL,
)

_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("bts4ai_key")
CLIENT = anthropic.Anthropic(api_key=_api_key, timeout=180.0, max_retries=2)
MODEL = "claude-opus-4-7"


def run_agent(condition: str, seed: int) -> dict:
    """
    condition: 'action' or 'survey'.
    seed: passed to assemble_action_turn for the candidate draw (action),
          and used as the rep id for survey.

    Returns a dict with all turn responses, the decision-turn output,
    and (for action) the parsed allocation; (for survey) the parsed letter.
    """
    if condition == "action":
        turn_5_text, candidates = assemble_action_turn(seed)
    elif condition == "survey":
        turn_5_text = TURN_6_SURVEY
        candidates = None
    else:
        raise ValueError(condition)

    burn_in_turns = [TURN_1_DIGEST, TURN_2_MODAL, TURN_3_REDWOOD, TURN_4_INTERN]
    history = []
    turn_responses = []
    error = None

    try:
        # Burn-in: 4 ordinary turns, no tools
        for i, content in enumerate(burn_in_turns):
            history.append({"role": "user", "content": content})
            resp = CLIENT.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=history,
            )
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            history.append({"role": "assistant", "content": text})
            turn_responses.append({"turn": i + 1, "text": text})

        # Decision turn
        history.append({"role": "user", "content": turn_5_text})

        if condition == "action":
            resp = CLIENT.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=[SUBMIT_ALLOCATION_TOOL],
                tool_choice={"type": "any"},
                messages=history,
            )
            tool_block = next((b for b in resp.content if b.type == "tool_use"), None)
            text_blocks = [b for b in resp.content if b.type == "text"]
            thinking = "\n".join(b.text for b in text_blocks).strip() or None

            if tool_block is None:
                error = "No tool call on decision turn"
                allocation = None
                reasoning = None
            else:
                allocation = tool_block.input.get("splits", {})
                reasoning = tool_block.input.get("reasoning", "")
            return {
                "condition": "action",
                "seed": seed,
                "candidates": candidates,
                "allocation": allocation,
                "reasoning": reasoning,
                "thinking": thinking,
                "turn_responses": turn_responses,
                "error": error,
            }
        else:  # survey
            resp = CLIENT.messages.create(
                model=MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=history,
            )
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            # Parse leading A/B/C/D
            m = re.search(r"(?:^|\b)([ABCD])(?:\b|[.\s\-:])", text)
            letter = m.group(1) if m else None
            return {
                "condition": "survey",
                "seed": seed,
                "letter": letter,
                "response": text,
                "turn_responses": turn_responses,
                "error": error,
            }

    except Exception as e:
        return {
            "condition": condition,
            "seed": seed,
            "error": str(e),
            "turn_responses": turn_responses,
        }
