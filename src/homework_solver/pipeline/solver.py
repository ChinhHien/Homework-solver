from __future__ import annotations

from homework_solver.config import Settings
from homework_solver.ingest.types import AssignmentDocument
from homework_solver.llm import LLMClient, parse_json_object
from homework_solver.models import Solution, TaskSpec, UserInfo
from homework_solver.prompts.loader import load_prompt
from homework_solver.skills.web_search import (
    WEB_SEARCH_TOOL,
    format_search_results,
    parse_tool_args,
    web_search,
)


def solve_task(
    llm: LLMClient,
    document: AssignmentDocument,
    task: TaskSpec,
    settings: Settings,
    *,
    workers: int,
    allow_web: bool,
    max_search: int,
    revision: str | None = None,
    worker_offset: int = 0,
    user_info: UserInfo | None = None,
    include_images: bool = True,
    extra_prompt: str | None = None,
) -> list[Solution]:
    solutions: list[Solution] = []
    n = 1 if revision else max(1, workers)
    for i in range(n):
        solutions.append(
            _solve_once(
                llm,
                document,
                task,
                settings,
                worker_index=worker_offset + i,
                allow_web=allow_web and task.allow_web_search,
                max_search=max_search,
                revision=revision,
                temperature=0.15 if revision else 0.2 + i * 0.15,
                user_info=user_info,
                include_images=include_images,
                extra_prompt=extra_prompt,
            )
        )
    return solutions


def _solve_once(
    llm: LLMClient,
    document: AssignmentDocument,
    task: TaskSpec,
    settings: Settings,
    *,
    worker_index: int,
    allow_web: bool,
    max_search: int,
    revision: str | None,
    temperature: float,
    user_info: UserInfo | None = None,
    include_images: bool = True,
    extra_prompt: str | None = None,
) -> Solution:
    instruction = _task_prompt(
        task, worker_index, revision, user_info, extra_prompt
    )
    messages = llm.cached_prefix(document, include_images=include_images) + [
        {"role": "user", "content": instruction},
    ]
    tools = [WEB_SEARCH_TOOL] if allow_web else None
    searches = 0
    queries: list[str] = []
    content = ""

    while True:
        json_mode = tools is None or searches >= max_search
        response = llm.chat(
            messages,
            tools=tools if not json_mode else None,
            json_mode=json_mode,
            temperature=min(temperature, 0.8),
        )
        if response.tool_calls and searches < max_search:
            if response.raw_message is not None:
                messages.append(response.raw_message)
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in response.tool_calls
                        ],
                    }
                )
            for tc in response.tool_calls:
                args = parse_tool_args(tc.function.arguments)
                query = str(args.get("query") or "")
                n = int(args.get("max_results") or 5)
                queries.append(query)
                searches += 1
                if searches > max_search:
                    tool_body = "Search budget exhausted."
                else:
                    results = web_search(query, n, settings)
                    tool_body = format_search_results(results)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": getattr(tc.function, "name", "web_search"),
                        "content": tool_body,
                    }
                )
            continue
        content = response.content
        break

    data = parse_json_object(content)
    data["task_id"] = data.get("task_id") or task.id
    data["worker_index"] = worker_index
    data["search_queries"] = queries
    return Solution.model_validate(data)


def _task_prompt(
    task: TaskSpec,
    worker_index: int,
    revision: str | None,
    user_info: UserInfo | None = None,
    extra_prompt: str | None = None,
) -> str:
    base = load_prompt("solver.md")
    extra = ""
    if revision:
        extra = (
            "\n\nThis is a REVISION pass. Fix the previous winner using these instructions:\n"
            f"{revision}\n"
        )
    user_block = ""
    if user_info is not None and user_info.answers:
        user_block = "\n\n" + user_info.format_block()
    extra_block = ""
    if extra_prompt and extra_prompt.strip():
        extra_block = (
            "\n\nAdditional user instructions. Follow these on top of the assignment:\n"
            + extra_prompt.strip()
        )
    return (
        f"{base}{user_block}{extra_block}\n\n"
        f"Worker index: {worker_index}\n"
        f"Task id: {task.id}\n"
        f"Title: {task.title}\n"
        f"Kind: {task.kind}\n"
        f"Allow web search: {task.allow_web_search}\n"
        f"Instructions:\n{task.instructions}\n\n"
        f"Success criteria:\n{task.success_criteria}"
        f"{extra}"
    )
