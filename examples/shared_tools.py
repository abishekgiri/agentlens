"""Shared fake tool implementations used by the broken-agent examples."""

from __future__ import annotations

from typing import Any


def search_web(query: str) -> dict[str, Any]:
    return {
        "status": "error",
        "error": "Network access disabled. Customer records are only available in query_db.",
        "query": query,
    }
