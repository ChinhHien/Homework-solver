from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AssignmentType = Literal["code", "mcq", "essay", "mixed"]
TaskKind = Literal["code", "mcq", "essay"]
OutputKind = Literal["folder", "markdown", "answers", "mixed"]
UserFieldKind = Literal["text", "choice", "multichoice", "confirm"]


class OutputSpec(BaseModel):
    kind: OutputKind = "markdown"
    notes: str = ""


class TaskSpec(BaseModel):
    id: str
    title: str
    instructions: str
    kind: TaskKind = "essay"
    allow_web_search: bool = False
    success_criteria: str = ""


class Plan(BaseModel):
    assignment_type: AssignmentType
    language: str = "vi"
    summary: str = ""
    output_spec: OutputSpec = Field(default_factory=OutputSpec)
    tasks: list[TaskSpec] = Field(default_factory=list)


class UserOption(BaseModel):
    id: str
    label: str
    hint: str = ""


class UserField(BaseModel):
    key: str
    label: str
    kind: UserFieldKind = "text"
    required: bool = True
    why: str = ""
    default: str = ""
    options: list[UserOption] = Field(default_factory=list)


class IntakeAnalysis(BaseModel):
    requires_user_info: bool = False
    fields: list[UserField] = Field(default_factory=list)


class UserAnswer(BaseModel):
    key: str
    label: str
    kind: UserFieldKind = "text"
    value: str = ""
    selected: list[str] = Field(default_factory=list)
    options: list[UserOption] = Field(default_factory=list)
    filled_by: str = "user"  # "user" | "default" | "unfilled"

    def display_value(self) -> str:
        if self.kind == "multichoice":
            if not self.selected:
                return "(none)"
            joined = ", ".join(self.selected)
            named = ", ".join(
                label for label in (self._label_of(s) for s in self.selected) if label
            )
            return f"{joined} ({named})" if named else joined
        if self.kind == "confirm":
            return "yes" if self.value.strip().lower() in {"true", "1", "yes", "y"} else "no"
        return self.value or "(not provided)"

    def _label_of(self, option_id: str) -> str:
        for opt in self.options:
            if opt.id == option_id:
                return opt.label
        return ""


class UserInfo(BaseModel):
    answers: list[UserAnswer] = Field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.answers

    def summary_lines(self) -> list[str]:
        return [f"{a.key}={a.display_value()}" for a in self.answers]

    def format_block(self) -> str:
        """Block injected into solver and evaluator prompts."""
        if not self.answers:
            return ""
        lines = ["User-provided information. Use these EXACT values in your answer:"]
        for a in self.answers:
            if a.filled_by == "unfilled":
                lines.append(
                    f"- {a.label} ({a.key}): NOT provided by the user. "
                    f"Leave a clearly visible placeholder such as <{a.key}> where it belongs."
                )
                continue
            lines.append(f"- {a.label} ({a.key}): {a.display_value()}")
        return "\n".join(lines)


class OutputFile(BaseModel):
    path: str
    content: str


class McqAnswer(BaseModel):
    id: str
    choice: str
    explanation: str = ""


class Solution(BaseModel):
    task_id: str
    worker_index: int = 0
    files: list[OutputFile] = Field(default_factory=list)
    answers: list[McqAnswer] = Field(default_factory=list)
    essay: str = ""
    notes: str = ""
    search_queries: list[str] = Field(default_factory=list)


class CandidateScore(BaseModel):
    index: int
    score: float
    rationale: str = ""


class Evaluation(BaseModel):
    winner_index: int = 0
    scores: list[CandidateScore] = Field(default_factory=list)
    hard_fail: bool = False
    revision_instructions: str | None = None
