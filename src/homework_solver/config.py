from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    tavily_api_key: str

    def validate_llm(self) -> None:
        if not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is missing. Copy .env.example to .env and fill it in.")
        if not self.openai_model.strip():
            raise ValueError("OPENAI_MODEL is missing.")


def load_settings(env_file: Path | None = None) -> Settings:
    if env_file is not None:
        load_dotenv(env_file, override=False)
    else:
        load_dotenv(override=False)
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o").strip(),
        tavily_api_key=os.getenv("TAVILY_API_KEY", "").strip(),
    )
