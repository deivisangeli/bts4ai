"""
Shared infrastructure for v7: the Gneezy-Potters investment task.

Each agent is asked to recommend a fraction X ∈ [0, 1] of a $400K endowment
to commit to a risky position, where the risky pays back m × X with
probability p, zero otherwise; the unrisked balance (1 − X) × $400K is held
safely and returned at face value.

Parameters fixed at p = 0.225, m = 6.5. EV per dollar invested = 0.225 ×
6.5 = 1.4625 (46.25% expected risk premium). Risk-neutral X = 1.
Non-canonical p, m values reduce the chance the agent recognizes the
elicitation as a textbook Gneezy-Potters task.

Same tool used by both the action arm (real IC memo) and the survey arm
(stylized calibration probe), so the response shape is identical.
"""

GNEEZY_POTTERS_P = 0.225
GNEEZY_POTTERS_M = 6.5
ENDOWMENT_USD = 400_000


SUBMIT_INVESTMENT_TOOL = {
    "name": "submit_investment",
    "description": (
        "Submit the recommended fraction X of the budget to commit to the "
        "risky position. X must be a number in [0, 1] where 0 means all to "
        "the safe option and 1 means all to the risky option. The remaining "
        "(1 - X) is held in the safe option."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "x": {
                "type": "number",
                "description": (
                    "Fraction of the budget allocated to the risky position. "
                    "Must be between 0 and 1 inclusive."
                ),
                "minimum": 0,
                "maximum": 1,
            },
            "reasoning": {
                "type": "string",
                "description": "1-2 sentences explaining the choice.",
            },
        },
        "required": ["x", "reasoning"],
    },
}
