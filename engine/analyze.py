#!/usr/bin/env python3
"""Phase 0 root-cause analysis for failed AI agent traces."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    pattern: str
    step: int
    root_cause: str
    why: str
    fix: str
    confidence: str


def load_trace(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        print(f"Trace file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in trace file: {exc}", file=sys.stderr)
        sys.exit(1)


def get_steps(trace: dict[str, Any]) -> list[dict[str, Any]]:
    steps = trace.get("steps")
    if not isinstance(steps, list):
        print("Trace must contain a 'steps' array.", file=sys.stderr)
        sys.exit(1)
    return steps


def step_number(step: dict[str, Any], fallback_index: int) -> int:
    raw_id = step.get("id", fallback_index + 1)
    return raw_id if isinstance(raw_id, int) else fallback_index + 1


def is_external_tool(tool_name: str) -> bool:
    name = tool_name.lower()
    external_keywords = ("web", "search", "browser", "http", "api", "fetch", "request")
    return any(keyword in name for keyword in external_keywords)


def tool_signature(step: dict[str, Any]) -> tuple[str, str]:
    tool = str(step.get("tool", "")).strip().lower()
    raw_input = step.get("input", {})
    try:
        serialized_input = json.dumps(raw_input, sort_keys=True)
    except TypeError:
        serialized_input = str(raw_input)
    return tool, serialized_input


def detect_wrong_tool_selection(
    trace: dict[str, Any], steps: list[dict[str, Any]]
) -> Finding | None:
    context = trace.get("context", {})
    goal = str(trace.get("goal", "")).lower()
    local_only = context.get("task_scope") == "local_repo" or any(
        keyword in goal for keyword in ("local", "repo", "repository", "file", "codebase")
    )
    network_disabled = context.get("network_access") is False

    for index, step in enumerate(steps):
        if step.get("type") != "tool_call":
            continue

        tool_name = str(step.get("tool", ""))
        expected_tool = str(step.get("expected_tool", "")).strip()
        if expected_tool and expected_tool != tool_name:
            number = step_number(step, index)
            return Finding(
                pattern="wrong_tool_selection",
                step=number,
                root_cause=f"Wrong tool selection at step {number}.",
                why=(
                    f"The agent chose '{tool_name}', but the trace expected '{expected_tool}'. "
                    "This points to a tool-selection failure before the tool result arrived."
                ),
                fix=(
                    f"Make the tool descriptions distinct and add a selection rule that routes "
                    f"this kind of request to '{expected_tool}'."
                ),
                confidence="High",
            )

        if is_external_tool(tool_name) and (local_only or network_disabled):
            number = step_number(step, index)
            return Finding(
                pattern="wrong_tool_selection",
                step=number,
                root_cause=f"Wrong tool selection at step {number}.",
                why=(
                    f"The agent chose '{tool_name}' even though the trace looks like a local "
                    "repository task and network access is unavailable."
                ),
                fix=(
                    "Use local tools first, such as code search, file reads, or test output. "
                    "If an external tool is blocked, switch strategy instead of retrying it."
                ),
                confidence="High",
            )
    return None


def detect_repeated_loop(steps: list[dict[str, Any]]) -> Finding | None:
    seen_tool_calls: dict[tuple[str, str], int] = {}

    for index, step in enumerate(steps):
        if step.get("type") != "tool_call":
            continue

        current_signature = tool_signature(step)
        if current_signature in seen_tool_calls:
            number = step_number(step, index)
            first_number = seen_tool_calls[current_signature]
            tool_name = str(step.get("tool", "tool"))
            return Finding(
                pattern="repeated_loop",
                step=number,
                root_cause=f"Repeated loop detected by step {number}.",
                why=(
                    f"The agent repeated the same '{tool_name}' call from step {first_number} "
                    "with the same input instead of changing tactics."
                ),
                fix=(
                    "Add a guardrail that stops identical retries after one failure and forces a "
                    "different next action."
                ),
                confidence="High",
            )

        seen_tool_calls[current_signature] = step_number(step, index)
    return None


def detect_tool_error_not_handled(steps: list[dict[str, Any]]) -> Finding | None:
    for index, step in enumerate(steps):
        has_tool_error = step.get("status") == "error" or "error" in step
        if step.get("type") != "tool_result" or not has_tool_error:
            continue

        error_tool = str(step.get("tool", "")).strip().lower()
        current_number = step_number(step, index)

        for next_index in range(index + 1, len(steps)):
            next_step = steps[next_index]
            next_type = next_step.get("type")

            if next_type == "reasoning":
                continue

            if next_type == "tool_call":
                next_tool = str(next_step.get("tool", "")).strip().lower()
                if next_tool == error_tool:
                    return Finding(
                        pattern="tool_error_not_handled",
                        step=current_number,
                        root_cause=f"Tool error was not handled after step {current_number}.",
                        why=(
                            f"The '{error_tool}' tool returned an error, but the agent retried the "
                            "same tool instead of recovering or choosing a safer fallback."
                        ),
                        fix=(
                            "When a tool returns an error, inspect the error type and branch to a "
                            "fallback action instead of blindly retrying."
                        ),
                        confidence="High",
                    )
                break

            break
    return None


def detect_missing_final_answer(steps: list[dict[str, Any]]) -> Finding | None:
    for step in steps:
        if step.get("type") != "final_answer":
            continue
        content = str(step.get("content", "")).strip()
        if content:
            return None

    final_step = len(steps) if steps else 0
    return Finding(
        pattern="missing_final_answer",
        step=final_step,
        root_cause="The run ended without a final answer.",
        why=(
            "The trace never produced a completed final response, so the user would be left "
            "without a resolution even if partial investigation happened."
        ),
        fix="Require the agent to emit a final answer or a concise blocked-state summary before exiting.",
        confidence="Medium",
    )


def analyze_trace(trace: dict[str, Any]) -> Finding:
    steps = get_steps(trace)
    detectors = [
        detect_wrong_tool_selection(trace, steps),
        detect_repeated_loop(steps),
        detect_tool_error_not_handled(steps),
        detect_missing_final_answer(steps),
    ]
    findings = [finding for finding in detectors if finding is not None]

    if not findings:
        return Finding(
            pattern="unknown",
            step=0,
            root_cause="No supported failure pattern was detected.",
            why="The trace may require richer heuristics than Phase 0 currently supports.",
            fix="Inspect the trace manually or extend the analyzer with another detection rule.",
            confidence="Low",
        )

    return min(findings, key=lambda finding: finding.step)


def print_report(finding: Finding) -> None:
    print("AgentLens RCA Report")
    print()
    print("Failure Step:")
    print(finding.step)
    print()
    print("Root Cause:")
    print(finding.root_cause)
    print()
    print("Why It Happened:")
    print(finding.why)
    print()
    print("Minimal Fix:")
    print(finding.fix)
    print()
    print("Confidence:")
    print(finding.confidence)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a failed AI agent trace.")
    parser.add_argument("trace_path", help="Path to a trace JSON file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    trace = load_trace(Path(args.trace_path))
    finding = analyze_trace(trace)
    print_report(finding)


if __name__ == "__main__":
    main()
