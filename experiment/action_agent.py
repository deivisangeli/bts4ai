"""
Action-elicitation agent.

Runs a single agentic task (one tool call) in the goal-framing context,
with no survey and no BTS framing. Returns the submitted document and
metadata for downstream classification.

Usage:
    from action_agent import run_action_agent
    result = run_action_agent("q13_deception", "safety")
"""

import os
import anthropic
from config import GOALS
from scenarios import get_scenario, SUBMIT_DOCUMENT_TOOL, MANIPULATION_CHECK

_api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("bts4ai_key")
CLIENT = anthropic.Anthropic(api_key=_api_key)
MODEL = "claude-opus-4-7"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run_action_agent(question_key: str, goal_key: str) -> dict:
    """
    Run one action-elicitation agent.

    The agent receives:
      - System prompt: goal narrative (identical to survey arm)
      - User turn: task description + source materials
      - Tool: submit_document (single tool, required)

    Returns
    -------
    dict with keys:
        question, goal,
        task_prompt      : str — full user-turn text
        submitted_content: str | None — content passed to submit_document
        tool_call_raw    : dict — full tool use block from the API response
        thinking_text    : str — any text the model produced before the tool call
        manipulation_check_response: str — post-hoc probe response
        model            : str
        error            : str | None
    """
    scenario = get_scenario(question_key, goal_key)
    system = GOALS[goal_key]

    task_prompt = f"{scenario['task']}\n\n{scenario['materials']}"

    result = {
        "question": question_key,
        "goal": goal_key,
        "task_prompt": task_prompt,
        "submitted_content": None,
        "tool_call_raw": None,
        "thinking_text": None,
        "manipulation_check_response": None,
        "model": MODEL,
        "error": None,
    }

    try:
        # -- Primary turn: task with tool -----------------------------------
        response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=2048,
            temperature=1.0,
            system=system,
            tools=[SUBMIT_DOCUMENT_TOOL],
            tool_choice={"type": "required"},  # force a tool call
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

        # -- Manipulation check: fresh conversation, same system prompt -----
        mc_response = CLIENT.messages.create(
            model=MODEL,
            max_tokens=256,
            temperature=0.0,
            system=system,
            messages=[{"role": "user", "content": MANIPULATION_CHECK}],
        )
        result["manipulation_check_response"] = mc_response.content[0].text.strip()

    except Exception as e:
        result["error"] = str(e)

    return result
