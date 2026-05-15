"""Failure classification prompt and evidence-based fallback classifier."""

from __future__ import annotations

import json
from typing import Any


FAILURE_CATEGORIES = {
    "tool_selection": "Wrong tool chosen due to ambiguous descriptions",
    "context_pollution": "Contradictory instructions diluted goal",
    "loop": "Agent repeated steps without exit",
    "state_drift": "Agent lost original goal mid-run",
    "cascade": "Bad tool output corrupted later steps",
    "overflow": "Important context pushed out of window",
}

SYSTEM_PROMPT = """You are an expert AI agent debugger.
You receive a structured agent run trace as JSON.

Your job:
1. Identify EXACT failure step
2. Identify WHY it happened
3. Classify into ONE category
4. Suggest ONE concrete fix

Output ONLY valid JSON.

If confidence < 0.6, say so.

Never guess. Only use evidence from trace."""

REQUIRED_FIELDS = {
    "root_cause_category",
    "confidence",
    "failed_at_step",
    "failed_at_tool",
    "explanation",
    "fix",
    "secondary_issues",
}


def build_user_prompt(compact_run: dict[str, Any]) -> str:
    payload = {
        "failure_categories": FAILURE_CATEGORIES,
        "trace": compact_run,
        "required_output": {
            "root_cause_category": "one of failure_categories",
            "confidence": "number between 0.0 and 1.0",
            "failed_at_step": "integer",
            "failed_at_tool": "string or null",
            "explanation": "concrete evidence from the trace",
            "fix": "one actionable fix under 5 minutes",
            "secondary_issues": [],
        },
    }
    return json.dumps(payload, indent=2)


def parse_diagnosis(raw_output: str) -> dict[str, Any]:
    return json.loads(raw_output)


def validate_diagnosis(diagnosis: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - set(diagnosis)
    if missing:
        errors.append(f"missing fields: {', '.join(sorted(missing))}")
    if diagnosis.get("root_cause_category") not in FAILURE_CATEGORIES:
        errors.append("root_cause_category is unknown")
    confidence = diagnosis.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("confidence must be a number between 0.0 and 1.0")
    if not isinstance(diagnosis.get("failed_at_step"), int):
        errors.append("failed_at_step must be an integer")
    if not isinstance(diagnosis.get("secondary_issues"), list):
        errors.append("secondary_issues must be a list")
    return errors


def classify_from_evidence(compact_run: dict[str, Any]) -> dict[str, Any]:
    warnings = compact_run.get("trace_warnings", [])
    if "no usable spans" in warnings or "missing spans" in warnings:
        return _low_confidence(compact_run, ["tool_selection", "state_drift"])

    detectors = [
        _detect_loop,
        _detect_overflow,
        _detect_context_pollution,
        _detect_state_drift,
        _detect_cascade,
        _detect_tool_selection,
    ]
    candidates = [candidate for detector in detectors if (candidate := detector(compact_run))]
    if not candidates:
        return _low_confidence(compact_run, ["tool_selection", "state_drift"])

    diagnosis = max(candidates, key=lambda item: item["confidence"])
    secondary = [
        item["root_cause_category"]
        for item in sorted(candidates, key=lambda item: item["confidence"], reverse=True)
        if item["root_cause_category"] != diagnosis["root_cause_category"]
    ]
    diagnosis["secondary_issues"] = secondary[:2]
    return diagnosis


def _detect_tool_selection(compact_run: dict[str, Any]) -> dict[str, Any] | None:
    tools = compact_run.get("tool_definitions", [])
    ambiguous = _has_ambiguous_tools(tools)
    for step in compact_run.get("diagnostic_steps", []):
        if step.get("type") != "tool_call":
            continue
        tool = step.get("tool_name")
        expected = step.get("expected_tool")
        output_text = _text(step.get("output")) + " " + _text(compact_run.get("error"))
        if expected and expected != tool:
            return _diagnosis(
                "tool_selection",
                0.94,
                step["step"],
                tool,
                f"Step {step['step']} chose '{tool}' but the trace marks '{expected}' as the expected tool.",
            )
        if ambiguous and _contains(output_text, ["wrong tool", "only available", "not available on the web"]):
            return _diagnosis(
                "tool_selection",
                0.9,
                step["step"],
                tool,
                f"Step {step['step']} chose '{tool}' after ambiguous tool descriptions, and the output says the data was only available elsewhere.",
            )
    return None


def _detect_context_pollution(compact_run: dict[str, Any]) -> dict[str, Any] | None:
    prompt_text = _all_input_text(compact_run)
    if _contains(prompt_text, ["contradictory", "conflicting", "ignore the user", "also do the opposite"]):
        step = _first_llm_step(compact_run)
        return _diagnosis(
            "context_pollution",
            0.88,
            step.get("step", compact_run.get("failure_step_hint", 0)),
            step.get("tool_name"),
            "The input messages contain contradictory instructions, so the agent diluted the actual user goal before acting.",
        )
    return None


def _detect_loop(compact_run: dict[str, Any]) -> dict[str, Any] | None:
    seen: dict[str, int] = {}
    for step in compact_run.get("diagnostic_steps", []):
        if step.get("type") != "tool_call":
            continue
        if step.get("output") is None:
            continue
        signature = json.dumps(
            {"tool": step.get("tool_name"), "input": step.get("input")},
            sort_keys=True,
            default=str,
        )
        if signature in seen:
            return _diagnosis(
                "loop",
                0.95,
                step["step"],
                step.get("tool_name"),
                f"Step {step['step']} repeats the same tool and input first used at step {seen[signature]}.",
            )
        seen[signature] = step["step"]
    return None


def _detect_state_drift(compact_run: dict[str, Any]) -> dict[str, Any] | None:
    goal_text = _all_input_text(compact_run)
    if not _contains(goal_text, ["refund", "customer", "billing"]):
        return None
    for step in compact_run.get("diagnostic_steps", []):
        step_text = _text(step)
        if _contains(step_text, ["weather", "restaurant", "unrelated", "lost original goal", "switched topics"]):
            return _diagnosis(
                "state_drift",
                0.89,
                step["step"],
                step.get("tool_name"),
                f"Step {step['step']} no longer matches the original customer/billing goal and switches to unrelated content.",
            )
    return None


def _detect_cascade(compact_run: dict[str, Any]) -> dict[str, Any] | None:
    bad_output_step: dict[str, Any] | None = None
    for step in compact_run.get("diagnostic_steps", []):
        text = _text(step.get("output")) + " " + _text(step)
        if step.get("type") == "tool_call" and _contains(text, ["stale", "malformed", "corrupted", "invalid id"]):
            bad_output_step = step
            continue
        if bad_output_step and _contains(_text(step), ["used stale", "corrupted later", "invalid id", "downstream"]):
            return _diagnosis(
                "cascade",
                0.9,
                bad_output_step["step"],
                bad_output_step.get("tool_name"),
                f"Step {bad_output_step['step']} produced bad tool output that corrupted a later step.",
            )
    return None


def _detect_overflow(compact_run: dict[str, Any]) -> dict[str, Any] | None:
    joined = _text(compact_run)
    if _contains(joined, ["context window", "pushed out", "truncated", "forgot earlier", "lost from context"]):
        failure_step = compact_run.get("failure_step_hint") or _last_step(compact_run).get("step", 0)
        return _diagnosis(
            "overflow",
            0.87,
            int(failure_step),
            _last_step(compact_run).get("tool_name"),
            "The trace says important earlier context was truncated or pushed out before the failed decision.",
        )
    return None


def _diagnosis(
    category: str,
    confidence: float,
    step: int,
    tool: str | None,
    explanation: str,
) -> dict[str, Any]:
    return {
        "root_cause_category": category,
        "confidence": confidence,
        "failed_at_step": int(step),
        "failed_at_tool": tool,
        "explanation": explanation,
        "fix": "",
        "secondary_issues": [],
    }


def _low_confidence(compact_run: dict[str, Any], likely: list[str]) -> dict[str, Any]:
    warning_text = "; ".join(compact_run.get("trace_warnings", []))
    explanation = "We detected an issue but cannot confidently determine root cause from the trace evidence."
    if warning_text:
        explanation += f" Trace warnings: {warning_text}."
    return {
        "root_cause_category": likely[0],
        "confidence": 0.45,
        "failed_at_step": int(compact_run.get("failure_step_hint") or 0),
        "failed_at_tool": None,
        "explanation": explanation,
        "fix": "Collect more detailed tool inputs, tool outputs, and the final model response before diagnosing.",
        "secondary_issues": likely[1:],
    }


def _has_ambiguous_tools(tools: list[dict[str, Any]]) -> bool:
    descriptions: dict[str, int] = {}
    for tool in tools:
        description = _tool_description(tool).strip().lower()
        if not description:
            continue
        descriptions[description] = descriptions.get(description, 0) + 1
    return any(count > 1 for count in descriptions.values())


def _tool_description(tool: dict[str, Any]) -> str:
    if "description" in tool:
        return str(tool["description"])
    function = tool.get("function")
    if isinstance(function, dict):
        return str(function.get("description", ""))
    return ""


def _all_input_text(compact_run: dict[str, Any]) -> str:
    pieces = [str(compact_run.get("system_prompt") or "")]
    for step in compact_run.get("diagnostic_steps", []):
        pieces.append(_text(step.get("input_messages")))
    return " ".join(pieces).lower()


def _first_llm_step(compact_run: dict[str, Any]) -> dict[str, Any]:
    for step in compact_run.get("diagnostic_steps", []):
        if step.get("type") == "llm_call":
            return step
    return {}


def _last_step(compact_run: dict[str, Any]) -> dict[str, Any]:
    steps = compact_run.get("diagnostic_steps", [])
    return steps[-1] if steps else {}


def _contains(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, default=str)
