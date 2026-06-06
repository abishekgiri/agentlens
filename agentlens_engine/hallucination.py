"""Hallucination detector for AgentLens.

Flags three classes of hallucination:
  1. Invented parameters  — tool was called with keys not in its JSON schema.
  2. Missing required     — a required schema field was absent from the tool call.
  3. Context contradiction — LLM response asserts facts that contradict retrieved
                             tool results (numeric mismatches, "not found" vs claimed
                             existence, status field contradictions).
"""

from __future__ import annotations

import json
import re
from typing import Any


# ── Public API ────────────────────────────────────────────────────────────────

def detect_hallucinations(
    spans: list[dict[str, Any]],
    tool_definitions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return a list of hallucination events found across the span list.

    Each event dict has::

        {
            "type": "invented_param" | "missing_required" | "context_contradiction",
            "step": int,
            "tool_name": str | None,
            "detail": str,
            "confidence": float,   # 0.0–1.0
            "severity": "high" | "medium" | "low",
        }
    """
    schema_map = _build_schema_map(tool_definitions or [])
    # Also try to extract schemas from llm_call span tool lists
    for span in spans:
        if not isinstance(span, dict):
            continue
        if span.get("type") == "llm_call" and span.get("tools"):
            schema_map.update(_build_schema_map(span["tools"]))

    events: list[dict[str, Any]] = []
    tool_outputs: list[dict[str, Any]] = []  # accumulate for contradiction checks

    for i, span in enumerate(spans, start=1):
        if not isinstance(span, dict):
            continue
        stype = span.get("type")

        if stype == "tool_call":
            tool_name = span.get("tool_name") or ""
            tool_input = span.get("input")
            schema = schema_map.get(tool_name)

            if schema and isinstance(tool_input, dict):
                events.extend(_check_invented_params(i, tool_name, tool_input, schema))
                events.extend(_check_missing_required(i, tool_name, tool_input, schema))

            tool_output = span.get("output")
            if tool_output is not None:
                tool_outputs.append({"step": i, "tool_name": tool_name, "output": tool_output})

        elif stype == "llm_call":
            resp_content = span.get("response_content")
            resp_text = _extract_text(resp_content)
            if resp_text and tool_outputs:
                events.extend(_check_context_contradiction(i, resp_text, tool_outputs))

    return events


def hallucination_summary(events: list[dict[str, Any]]) -> str:
    """Return a human-readable summary of detected hallucinations."""
    if not events:
        return "No hallucinations detected."
    lines = [f"{len(events)} hallucination(s) detected:"]
    for ev in events:
        sev = ev.get("severity", "?").upper()
        step = ev.get("step", "?")
        etype = ev.get("type", "?").replace("_", " ")
        detail = ev.get("detail", "")
        lines.append(f"  [{sev}] step {step} — {etype}: {detail}")
    return "\n".join(lines)


# ── Schema helpers ────────────────────────────────────────────────────────────

def _build_schema_map(tool_defs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return {tool_name: schema_properties_dict}."""
    result: dict[str, dict[str, Any]] = {}
    for tool in tool_defs:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name") or (tool.get("function") or {}).get("name")
        if not name:
            continue
        # Anthropic-style: input_schema.properties
        schema = tool.get("input_schema") or {}
        # OpenAI-style: function.parameters.properties
        if not schema and isinstance(tool.get("function"), dict):
            schema = tool["function"].get("parameters") or {}
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        result[str(name)] = {"properties": props, "required": required}
    return result


# ── Check 1: invented parameters ─────────────────────────────────────────────

def _check_invented_params(
    step: int,
    tool_name: str,
    tool_input: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    props = set(schema.get("properties", {}).keys())
    if not props:
        return []  # schema has no declared properties — can't check
    extra = [k for k in tool_input if k not in props]
    if not extra:
        return []
    return [
        {
            "type": "invented_param",
            "step": step,
            "tool_name": tool_name,
            "detail": (
                f"'{tool_name}' was called with parameter(s) not in its schema: "
                f"{extra}. Valid params: {sorted(props)}."
            ),
            "confidence": 0.95,
            "severity": "high",
        }
    ]


# ── Check 2: missing required parameters ─────────────────────────────────────

def _check_missing_required(
    step: int,
    tool_name: str,
    tool_input: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    required = schema.get("required", [])
    if not required:
        return []
    missing = [r for r in required if r not in tool_input]
    if not missing:
        return []
    return [
        {
            "type": "missing_required",
            "step": step,
            "tool_name": tool_name,
            "detail": (
                f"'{tool_name}' was called without required parameter(s): {missing}."
            ),
            "confidence": 0.97,
            "severity": "high",
        }
    ]


# ── Check 3: context contradiction ───────────────────────────────────────────

def _check_context_contradiction(
    step: int,
    resp_text: str,
    tool_outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for tool_item in tool_outputs:
        out = tool_item["output"]
        out_text = _to_text(out)
        tool_name = tool_item.get("tool_name", "tool")
        out_step = tool_item.get("step", "?")

        # 3a. Numeric contradiction
        out_nums = _extract_numbers(out_text)
        resp_nums = _extract_numbers(resp_text)
        if out_nums and resp_nums:
            conflicting = [
                (n, r)
                for n in out_nums
                for r in resp_nums
                if n != r and abs(n - r) / max(abs(n), 1) < 0.5 and abs(n - r) >= 1
                and _number_appears_in_context(str(int(n)), out_text)
                and _number_appears_in_context(str(int(r)), resp_text)
            ]
            for orig, claimed in conflicting[:1]:  # report first only
                events.append(
                    {
                        "type": "context_contradiction",
                        "step": step,
                        "tool_name": tool_name,
                        "detail": (
                            f"LLM response mentions {int(claimed)!r} but '{tool_name}' "
                            f"(step {out_step}) returned {int(orig)!r}."
                        ),
                        "confidence": 0.72,
                        "severity": "medium",
                    }
                )

        # 3b. Not-found contradiction
        not_found_in_tool = _contains(out_text, [
            "not found", "no results", "does not exist", "couldn't find", "unavailable",
            "404", "null", "none", "empty",
        ])
        claims_exists = _contains(resp_text, [
            "found", "exists", "retrieved", "here is", "the result",
            "successfully", "available", "shows that",
        ])
        if not_found_in_tool and claims_exists:
            events.append(
                {
                    "type": "context_contradiction",
                    "step": step,
                    "tool_name": tool_name,
                    "detail": (
                        f"LLM response claims to have found results, but '{tool_name}' "
                        f"(step {out_step}) returned a not-found / empty result."
                    ),
                    "confidence": 0.78,
                    "severity": "high",
                }
            )

        # 3c. Error-status contradiction
        is_error_output = (
            isinstance(out, dict)
            and (out.get("status") == "error" or out.get("error"))
        )
        claims_success = _contains(resp_text, [
            "successfully", "completed", "done", "finished", "retrieved", "found the",
        ])
        if is_error_output and claims_success:
            events.append(
                {
                    "type": "context_contradiction",
                    "step": step,
                    "tool_name": tool_name,
                    "detail": (
                        f"LLM response claims success, but '{tool_name}' "
                        f"(step {out_step}) returned an error: "
                        f"{str(out.get('error', ''))[:80]}."
                    ),
                    "confidence": 0.85,
                    "severity": "high",
                }
            )

    return events


# ── Text utilities ────────────────────────────────────────────────────────────

def _extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                t = block.get("text") or block.get("content") or ""
                parts.append(str(t))
        return " ".join(parts)
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    return str(content)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _extract_numbers(text: str) -> list[float]:
    """Extract all standalone numbers from text."""
    return [float(m) for m in re.findall(r"\b\d+(?:\.\d+)?\b", text)]


def _number_appears_in_context(num_str: str, text: str) -> bool:
    """True if num_str appears as a standalone number in text."""
    return bool(re.search(r"\b" + re.escape(num_str) + r"\b", text))


def _contains(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(n in lowered for n in needles)
