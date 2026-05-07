"""Local AgentLens collector and provider monkeypatches."""

from __future__ import annotations

import contextvars
import functools
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


RUNS_DIR = Path(".agentlens") / "runs"
_current_run: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "agentlens_current_run", default=None
)
_config: dict[str, Any] = {"api_key": None, "patched": set(), "originals": {}}


class AgentLensClient:
    """Backward-compatible direct Anthropic wrapper from the first Phase 1 pass."""

    def __init__(self, api_key: str, client: Any | None = None):
        self._client = client if client is not None else self._build_anthropic_client(api_key)
        self._run = start_run(name="manual")

    def messages_create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        input_messages = kwargs.get("messages", [])
        token = _current_run.set(self._run)
        try:
            capture_tool_results_from_messages(input_messages, provider="anthropic")

            try:
                response = self._client.messages.create(**kwargs)
                latency_ms = _elapsed_ms(started)
                response_content = _to_jsonable(getattr(response, "content", None))
                append_span(
                    {
                        "type": "llm_call",
                        "provider": "anthropic",
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
                capture_anthropic_tool_calls(response_content)
                return response
            except Exception as exc:
                capture_error(exc, context=_anthropic_context(kwargs), latency_ms=_elapsed_ms(started))
                raise
        finally:
            _current_run.reset(token)

    def record_tool_result(
        self, tool_name: str, output: Any, input: Any | None = None, tool_use_id: str | None = None
    ) -> None:
        token = _current_run.set(self._run)
        try:
            record_tool_result(tool_name=tool_name, output=output, input=input, tool_use_id=tool_use_id)
        finally:
            _current_run.reset(token)

    def save_run(self, path: str = "agentlens_run.json") -> None:
        save_run(path=path, run=self._run)

    @property
    def spans(self) -> list[dict[str, Any]]:
        return self._run["spans"]

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


def init(api_key: str | None = None) -> None:
    """Enable local capture for supported SDKs already available in this environment."""

    _config["api_key"] = api_key
    _patch_anthropic()
    _patch_openai()


def run(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Group all captured spans inside the decorated function into one saved run."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            run_data = start_run(name=name)
            token = _current_run.set(run_data)
            try:
                result = func(*args, **kwargs)
                run_data["status"] = "success"
                return result
            except Exception as exc:
                run_data["status"] = "error"
                run_data["error"] = str(exc)
                capture_error(exc, context={"function": func.__name__})
                raise
            finally:
                if run_data["status"] == "success" and _run_has_error_span(run_data):
                    run_data["status"] = "error"
                run_data["ended_at"] = _now_iso()
                save_run(run=run_data)
                _current_run.reset(token)

        return wrapper

    return decorator


def start_run(name: str = "default") -> dict[str, Any]:
    return {
        "run_id": str(uuid.uuid4()),
        "name": name,
        "started_at": _now_iso(),
        "ended_at": None,
        "status": "running",
        "spans": [],
    }


def current_run() -> dict[str, Any]:
    run_data = _current_run.get()
    if run_data is None:
        run_data = start_run(name="default")
        _current_run.set(run_data)
    return run_data


def append_span(span: dict[str, Any]) -> dict[str, Any]:
    run_data = current_run()
    enriched = {
        "id": str(uuid.uuid4()),
        "run_id": run_data["run_id"],
        **span,
    }
    run_data["spans"].append(enriched)
    return enriched


def record_tool_result(
    tool_name: str, output: Any, input: Any | None = None, tool_use_id: str | None = None
) -> None:
    output_json = _to_jsonable(output)
    append_span(
        {
            "type": "tool_call",
            "ts": _now_iso(),
            "tool_name": tool_name,
            "input": _to_jsonable(input),
            "output": output_json,
            "tool_use_id": tool_use_id,
        }
    )
    if _is_error_output(output_json):
        capture_error(
            error=_extract_error_message(output_json),
            context={
                "tool_name": tool_name,
                "input": _to_jsonable(input),
                "output": output_json,
                "tool_use_id": tool_use_id,
            },
        )


def save_run(path: str | None = None, run: dict[str, Any] | None = None) -> Path:
    run_data = run if run is not None else current_run()
    if run_data.get("ended_at") is None:
        run_data["ended_at"] = _now_iso()
    if run_data.get("status") == "running":
        run_data["status"] = "success"

    output_path = Path(path) if path else RUNS_DIR / f"{run_data['run_id']}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(run_data, indent=2), encoding="utf-8")
    return output_path


def capture_error(error: Exception | str, context: Any, latency_ms: float | None = None) -> None:
    append_span(
        {
            "type": "error",
            "ts": _now_iso(),
            "step_index": len(current_run()["spans"]) + 1,
            "latency_ms": latency_ms,
            "error": str(error),
            "context": _to_jsonable(context),
        }
    )


def capture_tool_results_from_messages(messages: Any, provider: str) -> None:
    for message in _as_list(messages):
        for block in _as_list(_get_value(message, "content")):
            if _get_value(block, "type") != "tool_result":
                continue
            record_tool_result(
                tool_name=_get_value(block, "name") or provider,
                input=None,
                output=_get_value(block, "content"),
                tool_use_id=_get_value(block, "tool_use_id"),
            )


def capture_anthropic_tool_calls(response_content: Any) -> None:
    for block in _as_list(response_content):
        if _get_value(block, "type") != "tool_use":
            continue
        append_span(
            {
                "type": "tool_call",
                "ts": _now_iso(),
                "tool_name": _get_value(block, "name"),
                "input": _to_jsonable(_get_value(block, "input")),
                "output": None,
                "tool_use_id": _get_value(block, "id"),
            }
        )


def capture_openai_tool_calls(response: Any) -> None:
    response_json = _to_jsonable(response)

    for tool_call in _find_tool_calls(response_json):
        function = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
        append_span(
            {
                "type": "tool_call",
                "ts": _now_iso(),
                "tool_name": function.get("name") or tool_call.get("name"),
                "input": _parse_maybe_json(function.get("arguments") or tool_call.get("input")),
                "output": None,
                "tool_use_id": tool_call.get("id"),
            }
        )


def _patch_anthropic() -> None:
    try:
        import anthropic
    except ImportError:
        return

    if not hasattr(anthropic, "Anthropic"):
        return

    if "anthropic" in _config["patched"]:
        return

    original_anthropic = anthropic.Anthropic
    _config["originals"]["anthropic.Anthropic"] = original_anthropic

    class AgentLensAnthropic:
        def __init__(self, *args: Any, **kwargs: Any):
            self._agentlens_client = original_anthropic(*args, **kwargs)
            self.messages = _AnthropicMessagesProxy(self._agentlens_client.messages)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._agentlens_client, name)

    anthropic.Anthropic = AgentLensAnthropic
    _config["patched"].add("anthropic")


class _AnthropicMessagesProxy:
    def __init__(self, messages: Any):
        self._messages = messages

    def create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        capture_tool_results_from_messages(kwargs.get("messages", []), provider="anthropic")
        try:
            response = self._messages.create(**kwargs)
            response_content = _to_jsonable(getattr(response, "content", None))
            append_span(
                {
                    "type": "llm_call",
                    "provider": "anthropic",
                    "ts": _now_iso(),
                    "latency_ms": _elapsed_ms(started),
                    "input_messages": _to_jsonable(kwargs.get("messages", [])),
                    "tools": _to_jsonable(kwargs.get("tools", [])),
                    "model": kwargs.get("model"),
                    "response_content": response_content,
                    "stop_reason": getattr(response, "stop_reason", None),
                    "usage": _to_jsonable(getattr(response, "usage", None)),
                }
            )
            capture_anthropic_tool_calls(response_content)
            return response
        except Exception as exc:
            capture_error(exc, context=_anthropic_context(kwargs), latency_ms=_elapsed_ms(started))
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)


def _patch_openai() -> None:
    try:
        import openai
    except ImportError:
        return

    if not hasattr(openai, "OpenAI"):
        return

    if "openai" in _config["patched"]:
        return

    original_openai = openai.OpenAI
    _config["originals"]["openai.OpenAI"] = original_openai

    class AgentLensOpenAI:
        def __init__(self, *args: Any, **kwargs: Any):
            self._agentlens_client = original_openai(*args, **kwargs)
            self.chat = _OpenAIChatProxy(self._agentlens_client.chat)
            if hasattr(self._agentlens_client, "responses"):
                self.responses = _OpenAIResponsesProxy(self._agentlens_client.responses)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._agentlens_client, name)

    openai.OpenAI = AgentLensOpenAI
    _config["patched"].add("openai")


class _OpenAIChatProxy:
    def __init__(self, chat: Any):
        self._chat = chat
        self.completions = _OpenAICompletionsProxy(chat.completions)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class _OpenAICompletionsProxy:
    def __init__(self, completions: Any):
        self._completions = completions

    def create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            response = self._completions.create(**kwargs)
            response_json = _to_jsonable(response)
            append_span(
                {
                    "type": "llm_call",
                    "provider": "openai",
                    "ts": _now_iso(),
                    "latency_ms": _elapsed_ms(started),
                    "input_messages": _to_jsonable(kwargs.get("messages", [])),
                    "tools": _to_jsonable(kwargs.get("tools", kwargs.get("functions", []))),
                    "model": kwargs.get("model"),
                    "response_content": response_json,
                    "stop_reason": _first_choice_stop_reason(response_json),
                    "usage": response_json.get("usage") if isinstance(response_json, dict) else None,
                }
            )
            capture_openai_tool_calls(response_json)
            return response
        except Exception as exc:
            capture_error(exc, context=_openai_context(kwargs), latency_ms=_elapsed_ms(started))
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


class _OpenAIResponsesProxy:
    def __init__(self, responses: Any):
        self._responses = responses

    def create(self, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            response = self._responses.create(**kwargs)
            response_json = _to_jsonable(response)
            append_span(
                {
                    "type": "llm_call",
                    "provider": "openai",
                    "ts": _now_iso(),
                    "latency_ms": _elapsed_ms(started),
                    "input_messages": _to_jsonable(kwargs.get("input")),
                    "tools": _to_jsonable(kwargs.get("tools", [])),
                    "model": kwargs.get("model"),
                    "response_content": response_json,
                    "stop_reason": response_json.get("status") if isinstance(response_json, dict) else None,
                    "usage": response_json.get("usage") if isinstance(response_json, dict) else None,
                }
            )
            capture_openai_tool_calls(response_json)
            return response
        except Exception as exc:
            capture_error(exc, context=_openai_context(kwargs), latency_ms=_elapsed_ms(started))
            raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._responses, name)


def load_runs() -> list[dict[str, Any]]:
    if not RUNS_DIR.exists():
        return []
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return runs


def load_run(run_id: str) -> dict[str, Any] | None:
    path = RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        matches = [run for run in load_runs() if run.get("run_id", "").startswith(run_id)]
        return matches[0] if len(matches) == 1 else None
    return json.loads(path.read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def _anthropic_context(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "anthropic",
        "input_messages": _to_jsonable(kwargs.get("messages", [])),
        "model": kwargs.get("model"),
        "tools": _to_jsonable(kwargs.get("tools", [])),
    }


def _openai_context(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": "openai",
        "input_messages": _to_jsonable(kwargs.get("messages", kwargs.get("input"))),
        "model": kwargs.get("model"),
        "tools": _to_jsonable(kwargs.get("tools", kwargs.get("functions", []))),
    }


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
    if hasattr(value, "to_dict"):
        return _to_jsonable(value.to_dict())
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


def _parse_maybe_json(value: Any) -> Any:
    if not isinstance(value, str):
        return _to_jsonable(value)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _find_tool_calls(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        maybe_calls = value.get("tool_calls")
        if isinstance(maybe_calls, list):
            found.extend(item for item in maybe_calls if isinstance(item, dict))
        for item in value.values():
            found.extend(_find_tool_calls(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_tool_calls(item))
    return found


def _first_choice_stop_reason(response_json: Any) -> Any:
    if not isinstance(response_json, dict):
        return None
    choices = response_json.get("choices")
    if isinstance(choices, list) and choices:
        return choices[0].get("finish_reason")
    return None


def _run_has_error_span(run_data: dict[str, Any]) -> bool:
    return any(span.get("type") == "error" for span in run_data.get("spans", []))
