"""Minimal local trace collector for Anthropic-style agent runs."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentLensClient:
    """Small wrapper that records LLM calls, tool choices, tool outputs, and errors."""

    def __init__(self, api_key: str, client: Any | None = None):
        self._client = client if client is not None else self._build_anthropic_client(api_key)
        self._run_id = str(uuid.uuid4())
        self._spans: list[dict[str, Any]] = []

    def messages_create(self, **kwargs: Any) -> Any:
        """Call Anthropic messages.create and capture a structured span."""

        started = time.perf_counter()
        input_messages = kwargs.get("messages", [])
        self._capture_tool_results_from_messages(input_messages)

        try:
            response = self._client.messages.create(**kwargs)
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            response_content = _to_jsonable(getattr(response, "content", None))

            self._spans.append(
                {
                    "id": str(uuid.uuid4()),
                    "run_id": self._run_id,
                    "type": "llm_call",
                    "ts": _now_iso(),
                    "latency_ms": latency_ms,
                    "input_messages": _to_jsonable(input_messages),
                    "tools": _to_jsonable(kwargs.get("tools", [])),
                    "model": kwargs.get("model"),
                    "response_content": response_content,
                    "stop_reason": getattr(response, "stop_reason", None),
                    "usage": _to_jsonable(getattr(response, "usage", None)),
                }
            )
            self._capture_tool_calls(response_content)
            return response
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            self._spans.append(
                {
                    "id": str(uuid.uuid4()),
                    "run_id": self._run_id,
                    "type": "error",
                    "ts": _now_iso(),
                    "step_index": len(self._spans) + 1,
                    "latency_ms": latency_ms,
                    "error": str(exc),
                    "context": {
                        "input_messages": _to_jsonable(input_messages),
                        "model": kwargs.get("model"),
                        "tools": _to_jsonable(kwargs.get("tools", [])),
                    },
                }
            )
            raise

    def record_tool_result(
        self, tool_name: str, output: Any, input: Any | None = None, tool_use_id: str | None = None
    ) -> None:
        """Record a tool output when the app executes a selected tool."""

        output_json = _to_jsonable(output)
        self._spans.append(
            {
                "id": str(uuid.uuid4()),
                "run_id": self._run_id,
                "type": "tool_call",
                "ts": _now_iso(),
                "tool_name": tool_name,
                "input": _to_jsonable(input),
                "output": output_json,
                "tool_use_id": tool_use_id,
            }
        )
        if _is_error_output(output_json):
            self._spans.append(
                {
                    "id": str(uuid.uuid4()),
                    "run_id": self._run_id,
                    "type": "error",
                    "ts": _now_iso(),
                    "step_index": len(self._spans),
                    "error": _extract_error_message(output_json),
                    "context": {
                        "tool_name": tool_name,
                        "input": _to_jsonable(input),
                        "output": output_json,
                        "tool_use_id": tool_use_id,
                    },
                }
            )

    def save_run(self, path: str = "agentlens_run.json") -> None:
        run = {
            "run_id": self._run_id,
            "spans": self._spans,
        }
        Path(path).write_text(json.dumps(run, indent=2), encoding="utf-8")

    @property
    def spans(self) -> list[dict[str, Any]]:
        return self._spans

    @staticmethod
    def _build_anthropic_client(api_key: str) -> Any:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "The anthropic package is required when no client is provided. "
                "Install it or pass a test client into AgentLensClient(..., client=...)."
            ) from exc

        return anthropic.Anthropic(api_key=api_key)

    def _capture_tool_calls(self, response_content: Any) -> None:
        for block in _as_list(response_content):
            block_type = _get_value(block, "type")
            if block_type != "tool_use":
                continue

            self._spans.append(
                {
                    "id": str(uuid.uuid4()),
                    "run_id": self._run_id,
                    "type": "tool_call",
                    "ts": _now_iso(),
                    "tool_name": _get_value(block, "name"),
                    "input": _to_jsonable(_get_value(block, "input")),
                    "output": None,
                    "tool_use_id": _get_value(block, "id"),
                }
            )

    def _capture_tool_results_from_messages(self, messages: Any) -> None:
        for message in _as_list(messages):
            for block in _as_list(_get_value(message, "content")):
                if _get_value(block, "type") != "tool_result":
                    continue

                self._spans.append(
                    {
                        "id": str(uuid.uuid4()),
                        "run_id": self._run_id,
                        "type": "tool_call",
                        "ts": _now_iso(),
                        "tool_name": _get_value(block, "name"),
                        "input": None,
                        "output": _to_jsonable(_get_value(block, "content")),
                        "tool_use_id": _get_value(block, "tool_use_id"),
                    }
                )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))
    return str(value)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _is_error_output(output: Any) -> bool:
    return isinstance(output, dict) and (output.get("status") == "error" or "error" in output)


def _extract_error_message(output: Any) -> str:
    if isinstance(output, dict):
        return str(output.get("error") or output)
    return str(output)
