from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from homework_solver.config import Settings
from homework_solver.ingest.types import AssignmentDocument
from homework_solver.prompts.loader import load_prompt


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    calls: int = 0

    def add(self, other: TokenUsage) -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.cached_tokens += other.cached_tokens
        self.calls += other.calls

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[Any] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw_message: Any = None


class LLMClient:
    def __init__(self, settings: Settings, include_images: bool = True) -> None:
        self.settings = settings
        self.include_images = include_images
        self.usage = TokenUsage()
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        self._system = load_prompt("system.md")

    def cached_prefix(
        self,
        document: AssignmentDocument,
        *,
        include_images: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Stable prefix reused by planner, solvers, and evaluator for prompt caching.

        include_images overrides self.include_images for this single call, so fast
        mode can keep vision for the planner while solving text-only.
        """
        use_images = self.include_images if include_images is None else include_images
        return [
            {"role": "system", "content": self._system},
            {
                "role": "user",
                "content": self._assignment_content(
                    document, include_images=use_images
                ),
            },
        ]

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        tool_choice: str | None = None,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            completion = self.client.chat.completions.create(**kwargs)
        except Exception:
            if json_mode:
                kwargs.pop("response_format", None)
                completion = self.client.chat.completions.create(**kwargs)
            else:
                raise

        choice = completion.choices[0]
        message = choice.message
        usage = _usage_from(completion.usage)
        self.usage.add(usage)
        content = message.content or ""
        tool_calls = list(message.tool_calls or [])
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            raw_message=message,
        )

    def _assignment_content(
        self,
        document: AssignmentDocument,
        *,
        include_images: bool = True,
    ) -> list[dict[str, Any]]:
        text = document.combined_text or "(No extractable text. Rely on images.)"
        header = (
            f"Assignment file: {document.source_path.name}\n"
            "The following is the extracted assignment. Images follow the text when present.\n\n"
            f"{text}"
        )
        parts: list[dict[str, Any]] = [{"type": "text", "text": header}]
        if not include_images:
            n = len(document.all_images)
            if n:
                parts.append(
                    {
                        "type": "text",
                        "text": f"\n({n} images extracted but omitted because --no-images was set.)",
                    }
                )
            return parts
        for image in document.all_images:
            b64 = base64.b64encode(image.data).decode("ascii")
            parts.append(
                {
                    "type": "text",
                    "text": f"Image from page {image.page} ({image.filename})",
                }
            )
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.mime};base64,{b64}"},
                }
            )
        return parts


def parse_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model response; expected JSON.")
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        candidates.insert(0, fenced.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        candidates.insert(0, text[start : end + 1])
    last_error: Exception | None = None
    for blob in candidates:
        try:
            data = json.loads(blob)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
    raise ValueError(f"Could not parse JSON from model output: {last_error}")


def _usage_from(usage: Any) -> TokenUsage:
    if usage is None:
        return TokenUsage(calls=1)
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    if not cached:
        cached = int(getattr(usage, "prompt_cache_hit_tokens", 0) or 0)
    if not cached and isinstance(usage, dict):
        prompt = int(usage.get("prompt_tokens") or prompt)
        completion = int(usage.get("completion_tokens") or completion)
        details = usage.get("prompt_tokens_details") or {}
        cached = int(details.get("cached_tokens") or usage.get("prompt_cache_hit_tokens") or 0)
    return TokenUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        cached_tokens=cached,
        calls=1,
    )
