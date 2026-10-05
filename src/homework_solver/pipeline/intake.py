from __future__ import annotations

from rich.console import Console
from rich.prompt import Confirm, Prompt

from homework_solver.ingest.types import AssignmentDocument
from homework_solver.llm import LLMClient, parse_json_object
from homework_solver.models import (
    IntakeAnalysis,
    UserAnswer,
    UserField,
    UserInfo,
    UserOption,
)
from homework_solver.prompts.loader import load_prompt


def analyze_required_info(llm: LLMClient, document: AssignmentDocument) -> IntakeAnalysis:
    """Ask the LLM which user-only information or choices the assignment requires."""
    messages = llm.cached_prefix(document) + [
        {"role": "user", "content": load_prompt("intake.md")},
    ]
    response = llm.chat(messages, json_mode=True, temperature=0.1)
    data = parse_json_object(response.content)
    return IntakeAnalysis.model_validate(data)


def collect_user_info(
    analysis: IntakeAnalysis,
    *,
    console: Console | None = None,
    interactive: bool = True,
) -> UserInfo:
    """Collect answers for every field the planner flagged.

    In non-interactive mode each field falls back to its declared default; a
    required field without a default is recorded as "unfilled" instead of
    blocking the run.
    """
    console = console or Console()
    answers: list[UserAnswer] = []
    if not analysis.requires_user_info or not analysis.fields:
        return UserInfo(answers=answers)

    console.print("\n[bold cyan]The assignment needs information from you:[/bold cyan]")
    for field in analysis.fields:
        answers.append(_collect_field(field, console=console, interactive=interactive))
    return UserInfo(answers=answers)


def _collect_field(
    field: UserField,
    *,
    console: Console,
    interactive: bool,
) -> UserAnswer:
    answer = UserAnswer(
        key=field.key,
        label=field.label,
        kind=field.kind,
        options=field.options,
    )
    if field.why:
        console.print(f"[dim]  {field.why}[/dim]")
    if not interactive:
        return _apply_default(answer, field)

    if field.kind == "text":
        answer.value = _prompt_text(field, console)
    elif field.kind == "confirm":
        answer.value = "true" if _prompt_confirm(field, console) else "false"
    elif field.kind == "choice":
        answer.value = _prompt_choice(field, console)
    elif field.kind == "multichoice":
        answer.selected = _prompt_multichoice(field, console)
    answer.filled_by = "user"
    return answer


def _prompt_text(field: UserField, console: Console) -> str:
    if field.required and not field.default:
        while True:
            value = Prompt.ask(f"  {field.label}", console=console).strip()
            if value:
                return value
            console.print("[yellow]  This field is required.[/yellow]")
    default = field.default if field.default else ""
    return Prompt.ask(f"  {field.label}", console=console, default=default).strip()


def _prompt_confirm(field: UserField, console: Console) -> bool:
    default = _truthy(field.default) if field.default else False
    return Confirm.ask(f"  {field.label}", console=console, default=default)


def _prompt_choice(field: UserField, console: Console) -> str:
    options = field.options
    if not options:
        return Prompt.ask(f"  {field.label}", console=console, default=field.default).strip()
    _print_options(options, console)
    fallback = _default_option(field) or options[0].id
    raw = Prompt.ask("  Your choice (number or id)", console=console, default=fallback)
    picked = _match_option(raw.strip(), options)
    if picked is None:
        console.print(f"[yellow]  Unknown option '{raw}'; using {fallback}.[/yellow]")
        return fallback
    return picked.id


def _prompt_multichoice(field: UserField, console: Console) -> list[str]:
    options = field.options
    if not options:
        return [p.strip() for p in field.default.split(",") if p.strip()]
    _print_options(options, console)
    default_ids = _parse_selection(field.default, options)
    default_str = ",".join(default_ids)
    raw = Prompt.ask(
        "  Your choices (comma-separated numbers/ids, e.g. 1,3)",
        console=console,
        default=default_str,
    )
    picked = _parse_selection(raw, options)
    if not picked:
        console.print("[yellow]  Nothing selected; using defaults.[/yellow]")
        return default_ids
    return picked


def _apply_default(answer: UserAnswer, field: UserField) -> UserAnswer:
    if field.kind == "multichoice":
        answer.selected = _parse_selection(field.default, field.options)
        answer.filled_by = "unfilled" if field.required and not answer.selected else "default"
        return answer
    if field.required and not field.default:
        answer.value = f"<{field.key}>"
        answer.filled_by = "unfilled"
        return answer
    answer.value = field.default
    answer.filled_by = "default"
    return answer


def _print_options(options: list[UserOption], console: Console) -> None:
    for i, opt in enumerate(options, start=1):
        line = f"  [bold]{i}[/bold]. {opt.label}"
        if opt.hint:
            line += f" [dim]— {opt.hint}[/dim]"
        console.print(line)


def _match_option(raw: str, options: list[UserOption]) -> UserOption | None:
    if not raw:
        return None
    lowered = raw.lower()
    for opt in options:
        if lowered in {opt.id.lower(), opt.label.lower()}:
            return opt
    if raw.isdigit():
        index = int(raw) - 1
        if 0 <= index < len(options):
            return options[index]
    for opt in options:
        if lowered in opt.label.lower():
            return opt
    return None


def _parse_selection(raw: str, options: list[UserOption]) -> list[str]:
    ids: list[str] = []
    for token in raw.split(","):
        match = _match_option(token.strip(), options)
        if match is not None and match.id not in ids:
            ids.append(match.id)
    return ids


def _default_option(field: UserField) -> str | None:
    if not field.default:
        return None
    match = _match_option(field.default, field.options)
    return match.id if match else None


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y"}
