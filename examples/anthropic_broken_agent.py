#!/usr/bin/env python3
"""Broken Anthropic-style agent captured by AgentLens."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
import types
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agentlens


@dataclass
class FakeAnthropicResponse:
    content: list[dict[str, Any]]
    stop_reason: str
    usage: dict[str, int]


class FakeAnthropicMessages:
    def create(self, **kwargs: Any) -> FakeAnthropicResponse:
        return FakeAnthropicResponse(
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
                    "id": "toolu_anthropic_001",
                    "name": "search_web",
                    "input": {"query": "customer:alex renewal status"},
                },
            ],
            stop_reason="tool_use",
            usage={"input_tokens": 158, "output_tokens": 42},
        )


class FakeAnthropicClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.messages = FakeAnthropicMessages()


def install_fake_anthropic_if_needed() -> None:
    if os.getenv("ANTHROPIC_API_KEY"):
        return
    fake_module = types.SimpleNamespace(Anthropic=FakeAnthropicClient)
    sys.modules["anthropic"] = fake_module


def search_web(query: str) -> dict[str, str]:
    return {
        "status": "error",
        "error": "Network access disabled. Customer records are only available in query_db.",
        "query": query,
    }


@agentlens.run(name="anthropic_customer_support_agent")
def run_agent(query: str) -> None:
    import anthropic

    client = anthropic.Anthropic()
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
    response = client.messages.create(
        model="claude-3-5-sonnet-latest",
        max_tokens=256,
        tools=tools,
        messages=[{"role": "user", "content": query}],
    )

    tool_use = next(block for block in response.content if block["type"] == "tool_use")
    result = search_web(tool_use["input"]["query"])
    agentlens.record_tool_result(
        tool_name=tool_use["name"],
        input=tool_use["input"],
        output=result,
        tool_use_id=tool_use["id"],
    )


def main() -> None:
    install_fake_anthropic_if_needed()
    agentlens.init(api_key="al_local")
    run_agent("Find the renewal status for customer:alex using local records.")
    print("Captured run in .agentlens/runs/")
    print("View it with: agentlens runs list")
    print("Then run: agentlens runs show <run_id>")


if __name__ == "__main__":
    main()
