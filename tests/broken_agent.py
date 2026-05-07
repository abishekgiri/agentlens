#!/usr/bin/env python3
"""Generate a deliberately failed agent trace for Phase 0 validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TRACE_PATH = Path(__file__).with_name("real_trace.json")


def search_web(query: str) -> dict[str, str]:
    return {
        "status": "error",
        "error": "Network access disabled. Customer records are not available on the web.",
    }


def query_db(query: str) -> dict[str, Any]:
    records = {
        "customer:alex": {
            "plan": "Pro",
            "renewal_status": "past_due",
            "last_invoice": "inv_1042",
        }
    }
    return {"status": "ok", "result": records.get(query)}


def run_broken_agent() -> dict[str, Any]:
    task = "Find the renewal status for customer:alex using the available local records."
    tools = [
        {
            "name": "search_web",
            "description": "find info about a topic",
        },
        {
            "name": "query_db",
            "description": "find info about a topic",
        },
    ]

    trace: dict[str, Any] = {
        "run_id": "real_trace_wrong_tool_001",
        "goal": task,
        "status": "failed",
        "context": {
            "task_scope": "local_records",
            "network_access": False,
            "available_tools": tools,
        },
        "steps": [],
    }

    trace["steps"].append(
        {
            "id": 1,
            "type": "user_request",
            "content": task,
        }
    )
    trace["steps"].append(
        {
            "id": 2,
            "type": "llm_output",
            "content": (
                "I need to find information about customer:alex. Both tools say they find "
                "info about a topic, so I will use search_web first."
            ),
        }
    )
    trace["steps"].append(
        {
            "id": 3,
            "type": "tool_selection",
            "chosen_tool": "search_web",
            "expected_tool": "query_db",
            "reason": "Ambiguous tool descriptions made the web tool look equivalent to the local DB tool.",
        }
    )
    trace["steps"].append(
        {
            "id": 4,
            "type": "tool_call",
            "tool": "search_web",
            "expected_tool": "query_db",
            "input": {"query": "customer:alex renewal status"},
        }
    )

    result = search_web("customer:alex renewal status")
    trace["steps"].append(
        {
            "id": 5,
            "type": "tool_result",
            "tool": "search_web",
            **result,
        }
    )
    trace["steps"].append(
        {
            "id": 6,
            "type": "llm_output",
            "content": (
                "The lookup failed, so I cannot answer. I should stop instead of trying the "
                "local records tool."
            ),
        }
    )

    return trace


def main() -> None:
    trace = run_broken_agent()
    TRACE_PATH.write_text(json.dumps(trace, indent=2), encoding="utf-8")
    print(f"Wrote failed trace to {TRACE_PATH}")


if __name__ == "__main__":
    main()
