"""Actionable fix templates for AgentLens diagnosis categories."""

from __future__ import annotations

from typing import Any


def generate_fix(category: str, compact_run: dict[str, Any], diagnosis: dict[str, Any]) -> str:
    tool = diagnosis.get("failed_at_tool") or _first_failed_tool(compact_run) or "the selected tool"
    expected = _expected_tool(compact_run)

    if category == "tool_selection":
        if expected and expected != tool:
            return (
                f"Rewrite the tool descriptions so '{tool}' is clearly for external lookup and "
                f"'{expected}' is clearly for this request, then route this case to '{expected}'."
            )
        return (
            f"Rewrite ambiguous tool descriptions and add a routing check before calling '{tool}' "
            "so local tasks cannot be sent to the wrong tool."
        )

    if category == "loop":
        return (
            f"Add an exit condition that stops retrying '{tool}' after one repeated failure and "
            "forces a different action or a final blocked-state response."
        )

    if category == "context_pollution":
        return (
            "Remove the contradictory instruction from the prompt and keep one explicit priority "
            "rule for the task goal before tool selection."
        )

    if category == "state_drift":
        return (
            "Restate the original user goal before each major step and reject tool calls whose "
            "input no longer matches that goal."
        )

    if category == "cascade":
        return (
            f"Validate the output from '{tool}' before using it downstream; if it is stale, empty, "
            "or malformed, stop and recover instead of feeding it into the next step."
        )

    if category == "overflow":
        return (
            "Summarize durable task facts before the context window fills, then reload that summary "
            "before making the final tool or answer decision."
        )

    return "Add a guardrail tied to the failed step and rerun the trace to confirm the failure is gone."


def likely_fixes(categories: list[str], compact_run: dict[str, Any]) -> list[str]:
    return [
        generate_fix(category, compact_run, {"root_cause_category": category})
        for category in categories[:2]
    ]


def _first_failed_tool(compact_run: dict[str, Any]) -> str | None:
    for step in compact_run.get("diagnostic_steps", []):
        if step.get("type") == "tool_call" and step.get("tool_name"):
            return step["tool_name"]
    return None


def _expected_tool(compact_run: dict[str, Any]) -> str | None:
    for step in compact_run.get("diagnostic_steps", []):
        expected = step.get("expected_tool")
        if expected:
            return expected
    return None
