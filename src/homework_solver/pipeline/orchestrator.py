from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from homework_solver.config import Settings
from homework_solver.ingest import load_assignment
from homework_solver.ingest.types import AssignmentDocument
from homework_solver.llm import LLMClient
from homework_solver.models import Plan, Solution, TaskSpec, UserInfo
from homework_solver.output.writer import write_outputs
from homework_solver.pipeline.evaluator import evaluate_candidates
from homework_solver.pipeline.intake import analyze_required_info, collect_user_info
from homework_solver.pipeline.planner import plan_assignment
from homework_solver.pipeline.solver import solve_task


@dataclass
class TaskResult:
    task: TaskSpec
    winner: Solution
    scores: list[dict]
    search_queries: list[str]
    revised: bool = False


@dataclass
class RunResult:
    plan: Plan
    tasks: list[TaskResult] = field(default_factory=list)
    output_dir: Path | None = None
    user_info: UserInfo = field(default_factory=UserInfo)


def run_pipeline(
    source: Path,
    out: Path,
    settings: Settings,
    *,
    workers: int = 3,
    allow_web: bool = True,
    max_search: int = 4,
    include_images: bool = True,
    interactive: bool = True,
    fast: bool = False,
    extra_prompt: str | None = None,
    console: Console | None = None,
) -> RunResult:
    console = console or Console()
    if fast:
        if workers > 1:
            workers = 1
        if max_search > 2:
            max_search = 2
        console.print(
            "[dim]Fast mode: 1 worker, 2 searches, text-only solving.[/dim]"
        )
    # Fast mode keeps vision for planner/intake but solves and judges text-only.
    solver_images = include_images and not fast
    document = load_assignment(source)
    llm = LLMClient(settings, include_images=include_images)
    try:
        plan = _plan_with_image_fallback(llm, document, console, extra_prompt)
    except Exception as exc:
        if include_images and document.all_images:
            console.print(f"[yellow]Planner failed with images ({exc}); retrying text-only.[/yellow]")
            llm.include_images = False
            plan = plan_assignment(llm, document)
        else:
            raise

    user_info = _collect_user_info(llm, document, console, interactive=interactive)
    if user_info.answers:
        console.print("[bold]User info:[/bold] " + "; ".join(user_info.summary_lines()))

    console.print(f"[bold]Type:[/bold] {plan.assignment_type}  [bold]Tasks:[/bold] {len(plan.tasks)}")
    results: list[TaskResult] = []
    for task in plan.tasks:
        console.print(f"\n[cyan]Solving[/cyan] {task.id}: {task.title}")
        candidates = solve_task(
            llm,
            document,
            task,
            settings,
            workers=workers,
            allow_web=allow_web,
            max_search=max_search,
            user_info=user_info,
            include_images=solver_images,
            extra_prompt=extra_prompt,
        )
        evaluation = evaluate_candidates(
            llm,
            document,
            task,
            candidates,
            user_info=user_info,
            include_images=solver_images,
            extra_prompt=extra_prompt,
        )
        winner = candidates[evaluation.winner_index]
        revised = False
        if evaluation.hard_fail and evaluation.revision_instructions:
            console.print("[yellow]Hard fail — running one revision pass.[/yellow]")
            revisions = solve_task(
                llm,
                document,
                task,
                settings,
                workers=1,
                allow_web=allow_web,
                max_search=max_search,
                revision=evaluation.revision_instructions,
                worker_offset=len(candidates),
                user_info=user_info,
                include_images=solver_images,
                extra_prompt=extra_prompt,
            )
            candidates = [winner, revisions[0]]
            evaluation = evaluate_candidates(
                llm,
                document,
                task,
                candidates,
                user_info=user_info,
                include_images=solver_images,
                extra_prompt=extra_prompt,
            )
            winner = candidates[evaluation.winner_index]
            revised = True
        queries = [q for sol in candidates for q in sol.search_queries]
        results.append(
            TaskResult(
                task=task,
                winner=winner,
                scores=[s.model_dump() for s in evaluation.scores],
                search_queries=queries,
                revised=revised,
            )
        )
        console.print(
            f"  winner worker={winner.worker_index}  "
            f"scores={evaluation.scores}"
        )

    usage = llm.usage
    output_dir = write_outputs(
        out=out,
        document=document,
        plan=plan,
        results=results,
        usage={
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "cached_tokens": usage.cached_tokens,
            "total_tokens": usage.total_tokens,
            "calls": usage.calls,
        },
        source=source,
        user_info=user_info,
    )
    console.print(
        f"\n[green]Wrote[/green] {output_dir}\n"
        f"tokens prompt={usage.prompt_tokens} cached={usage.cached_tokens} "
        f"completion={usage.completion_tokens} calls={usage.calls}"
    )
    return RunResult(plan=plan, tasks=results, output_dir=output_dir, user_info=user_info)


def _collect_user_info(
    llm: LLMClient,
    document: AssignmentDocument,
    console: Console,
    *,
    interactive: bool,
) -> UserInfo:
    try:
        analysis = analyze_required_info(llm, document)
    except Exception as exc:
        console.print(f"[yellow]User-info analysis failed ({exc}); skipping.[/yellow]")
        return UserInfo()
    if not analysis.requires_user_info or not analysis.fields:
        return UserInfo()
    try:
        return collect_user_info(analysis, console=console, interactive=interactive)
    except Exception as exc:
        console.print(f"[yellow]User-info collection failed ({exc}); continuing without it.[/yellow]")
        return UserInfo()


def _plan_with_image_fallback(
    llm: LLMClient,
    document: AssignmentDocument,
    console: Console,
    extra_prompt: str | None = None,
):
    try:
        return plan_assignment(llm, document, extra_prompt=extra_prompt)
    except Exception as exc:
        message = str(exc).lower()
        vision_hints = ("image", "vision", "multimodal", "invalid_image", "unsupported")
        if llm.include_images and any(h in message for h in vision_hints):
            console.print("[yellow]Model rejected images; continuing without them.[/yellow]")
            llm.include_images = False
            return plan_assignment(llm, document)
        raise
