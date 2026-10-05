from __future__ import annotations

import json

from homework_solver.ingest.types import AssignmentDocument
from homework_solver.llm import LLMClient, parse_json_object
from homework_solver.models import Evaluation, Solution, TaskSpec, UserInfo
from homework_solver.prompts.loader import load_prompt


def evaluate_candidates(
    llm: LLMClient,
    document: AssignmentDocument,
    task: TaskSpec,
    candidates: list[Solution],
    user_info: UserInfo | None = None,
    include_images: bool = True,
    extra_prompt: str | None = None,
) -> Evaluation:
    payload = []
    for i, sol in enumerate(candidates):
        payload.append(
            {
                "index": i,
                "worker_index": sol.worker_index,
                "files": [f.model_dump() for f in sol.files],
                "answers": [a.model_dump() for a in sol.answers],
                "essay": sol.essay,
                "notes": sol.notes,
            }
        )
    user = (
        f"{load_prompt('evaluator.md')}\n\n"
        f"Task id: {task.id}\n"
        f"Title: {task.title}\n"
        f"Kind: {task.kind}\n"
        f"Instructions:\n{task.instructions}\n\n"
        f"Success criteria:\n{task.success_criteria}\n"
    )
    if user_info is not None and user_info.answers:
        user += (
            f"\n{user_info.format_block()}\n"
            "Deduct points if any of this user-provided information is "
            "missing, incorrect, or left as a placeholder.\n"
        )
    if extra_prompt and extra_prompt.strip():
        user += (
            "\nAdditional user instructions the solution must follow "
            "— score accordingly:\n"
            + extra_prompt.strip()
            + "\n"
        )
    user += f"\nCandidates JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    messages = llm.cached_prefix(
        document, include_images=include_images
    ) + [{"role": "user", "content": user}]
    response = llm.chat(messages, json_mode=True, temperature=0.0)
    data = parse_json_object(response.content)
    evaluation = Evaluation.model_validate(data)
    if evaluation.winner_index < 0 or evaluation.winner_index >= len(candidates):
        evaluation.winner_index = _fallback_winner(evaluation, len(candidates))
    return evaluation


def _fallback_winner(evaluation: Evaluation, n: int) -> int:
    if evaluation.scores:
        best = max(evaluation.scores, key=lambda s: s.score)
        if 0 <= best.index < n:
            return best.index
    return 0
