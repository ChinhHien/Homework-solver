from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from homework_solver.config import load_settings
from homework_solver.pipeline.orchestrator import run_pipeline

console = Console()


def main(
    source: Path = typer.Argument(..., exists=True, readable=True, help="PDF or DOCX assignment"),
    extra_prompt: str | None = typer.Argument(
        None,
        help="Optional extra instructions forwarded to the planner, solver, and evaluator (e.g. 'Combine everything into one file')",
    ),
    out: Path = typer.Option(Path("./ket-qua"), "--out", help="Output folder"),
    workers: int = typer.Option(3, "--workers", min=1, max=8, help="Solver candidates per task"),
    no_web: bool = typer.Option(False, "--no-web", help="Disable the web_search skill"),
    max_search: int = typer.Option(4, "--max-search", min=0, max=12, help="Max web searches per worker"),
    no_images: bool = typer.Option(False, "--no-images", help="Do not send extracted images to the LLM"),
    env_file: Path | None = typer.Option(None, "--env-file", help="Optional path to a .env file"),
    non_interactive: bool = typer.Option(
        False,
        "--non-interactive",
        help="Do not ask questions; use defaults for required user info",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        help="Fast mode: 1 worker, 2 searches, text-only solving (saves tokens)",
    ),
) -> None:
    """Solve a homework PDF/DOCX with planner, multi-candidate solvers, and an evaluator."""
    try:
        settings = load_settings(env_file)
        settings.validate_llm()
        run_pipeline(
            source=source,
            out=out,
            settings=settings,
            workers=workers,
            allow_web=not no_web,
            max_search=max_search,
            include_images=not no_images,
            interactive=not non_interactive,
            fast=fast,
            extra_prompt=extra_prompt,
            console=console,
        )
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def app() -> None:
    typer.run(main)


if __name__ == "__main__":
    app()
