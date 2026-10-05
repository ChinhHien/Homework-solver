from __future__ import annotations

from homework_solver.ingest.types import AssignmentDocument
from homework_solver.llm import LLMClient, parse_json_object
from homework_solver.models import Plan
from homework_solver.prompts.loader import load_prompt


def plan_assignment(
    llm: LLMClient,
    document: AssignmentDocument,
    extra_prompt: str | None = None,
) -> Plan:
    user = load_prompt("planner.md")
    if extra_prompt and extra_prompt.strip():
        user += (
            "\n\nAdditional user instructions — account for them in the plan "
            "(task split, output layout, and success criteria):\n"
            + extra_prompt.strip()
        )
    messages = llm.cached_prefix(document) + [
        {"role": "user", "content": user},
    ]
    response = llm.chat(messages, json_mode=True, temperature=0.1)
    data = parse_json_object(response.content)
    plan = Plan.model_validate(data)
    if not plan.tasks:
        raise ValueError("Planner returned no tasks.")
    return plan
