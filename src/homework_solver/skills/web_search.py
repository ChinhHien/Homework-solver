from __future__ import annotations

import json
from typing import Any

import httpx

from homework_solver.config import Settings


def web_search(query: str, max_results: int, settings: Settings) -> list[dict[str, str]]:
    query = query.strip()
    if not query:
        return []
    max_results = max(1, min(max_results, 8))
    if settings.tavily_api_key:
        try:
            return _tavily_search(query, max_results, settings.tavily_api_key)
        except Exception:
            pass
    return _ddg_search(query, max_results)


def format_search_results(results: list[dict[str, str]]) -> str:
    if not results:
        return "No search results."
    lines = []
    for i, item in enumerate(results, start=1):
        lines.append(
            f"{i}. {item.get('title', '(no title)')}\n"
            f"   URL: {item.get('url', '')}\n"
            f"   {item.get('snippet', '')}"
        )
    return "\n".join(lines)


def _tavily_search(query: str, max_results: int, api_key: str) -> list[dict[str, str]]:
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }
    with httpx.Client(timeout=30.0) as client:
        response = client.post("https://api.tavily.com/search", json=payload)
        response.raise_for_status()
        data = response.json()
    results: list[dict[str, str]] = []
    for item in data.get("results") or []:
        results.append(
            {
                "title": str(item.get("title") or ""),
                "url": str(item.get("url") or ""),
                "snippet": str(item.get("content") or item.get("snippet") or ""),
            }
        )
    return results


def _ddg_search(query: str, max_results: int) -> list[dict[str, str]]:
    from ddgs import DDGS

    results: list[dict[str, str]] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("href") or item.get("url") or ""),
                    "snippet": str(item.get("body") or item.get("snippet") or ""),
                }
            )
    return results


WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the public web for extra facts, APIs, formulas, or similar problems.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 8, "default": 5},
            },
            "required": ["query"],
        },
    },
}


def parse_tool_args(raw: str) -> dict[str, Any]:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
