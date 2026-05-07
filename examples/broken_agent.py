#!/usr/bin/env python3
"""Run a deliberately broken local agent and save an AgentLens trace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentlens import AgentLensClient


@dataclass
class FakeResponse:
    content: list[dict[str, Any]]
    stop_reason: str
    usage: dict[str, int]


class FakeMessages:
    def create(self, **kwargs: Any) -> FakeResponse:
        return FakeResponse(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Both tools say they find info about a topic. I will use search_web "
                        "to look up customer:alex."
                    ),
                },
                {
                    "type": "tool_use",
                    "id": "toolu_001",
                    "name": "search_web",
                    "input": {"query": "customer:alex renewal status"},
                },
            ],
            stop_reason="tool_use",
            usage={"input_tokens": 158, "output_tokens": 42},
        )


class FakeAnthropic:
    def __init__(self) -> None:
        self.messages = FakeMessages()


def search_web(query: str) -> dict[str, str]:
    return {
        "status": "error",
        "error": "Network access disabled. Customer records are only available in query_db.",
        "query": query,
    }


def main() -> None:
    client = AgentLensClient(api_key="local-dev", client=FakeAnthropic())
    tools = [
        {
            "name": "search_web",
            "description": "find info about a topic",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
        {
            "name": "query_db",
            "description": "find info about a topic",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    ]

    response = client.messages_create(
        model="claude-3-5-sonnet-latest",
        max_tokens=256,
        tools=tools,
        messages=[
            {
                "role": "user",
                "content": "Find the renewal status for customer:alex using local records.",
            }
        ],
    )

    tool_use = next(block for block in response.content if block["type"] == "tool_use")
    result = search_web(tool_use["input"]["query"])
    client.record_tool_result(
        tool_name=tool_use["name"],
        input=tool_use["input"],
        output=result,
        tool_use_id=tool_use["id"],
    )

    output_path = Path("agentlens_run.json")
    client.save_run(str(output_path))
    print(f"Wrote trace to {output_path}")


if __name__ == "__main__":
    main()
