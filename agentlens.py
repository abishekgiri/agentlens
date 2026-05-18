"""Public AgentLens SDK and CLI entrypoint."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

from engine.diagnose import diagnose_run
from engine.evaluate import evaluate_cases, print_evaluation
from sdk import AgentLensClient, init, load_run, load_runs, record_tool_result, run, save_run

__all__ = [
    "AgentLensClient",
    "init",
    "record_tool_result",
    "run",
    "save_run",
]


def main() -> None:
    parser = argparse.ArgumentParser(prog="agentlens")
    subparsers = parser.add_subparsers(dest="command")

    runs_parser = subparsers.add_parser("runs")
    runs_subparsers = runs_parser.add_subparsers(dest="runs_command")
    runs_subparsers.add_parser("list")
    show_parser = runs_subparsers.add_parser("show")
    show_parser.add_argument("run_id")

    diagnose_parser = subparsers.add_parser("diagnose")
    diagnose_parser.add_argument("run_id")
    anonymize_parser = subparsers.add_parser("anonymize")
    anonymize_parser.add_argument("run_id")
    feedback_parser = subparsers.add_parser("feedback-template")
    feedback_parser.add_argument("run_id")
    subparsers.add_parser("evaluate")

    args = parser.parse_args()

    if args.command == "runs" and args.runs_command == "list":
        _print_runs_list()
        return

    if args.command == "runs" and args.runs_command == "show":
        _print_run_detail(args.run_id)
        return

    if args.command == "diagnose":
        _print_diagnosis(args.run_id)
        return

    if args.command == "anonymize":
        _anonymize_run(args.run_id)
        return

    if args.command == "feedback-template":
        _print_feedback_template(args.run_id)
        return

    if args.command == "evaluate":
        print_evaluation(evaluate_cases())
        return

    parser.print_help()


def _print_runs_list() -> None:
    runs = load_runs()
    if not runs:
        print("No AgentLens runs found in .agentlens/runs/")
        return

    print("AgentLens Runs")
    print()
    print(f"{'run_id':36}  {'name':24}  {'status':8}  {'timestamp':25}  spans")
    for item in runs[:20]:
        print(
            f"{item.get('run_id', ''):36}  "
            f"{item.get('name', '')[:24]:24}  "
            f"{item.get('status', ''):8}  "
            f"{item.get('started_at', '')[:25]:25}  "
            f"{len(item.get('spans', []))}"
        )


def _print_run_detail(run_id: str) -> None:
    item = load_run(run_id)
    if item is None:
        print(f"Run not found: {run_id}")
        return

    print("AgentLens Run Detail")
    print()
    print(f"Run ID: {item.get('run_id')}")
    print(f"Name: {item.get('name')}")
    print(f"Status: {item.get('status')}")
    print(f"Started: {item.get('started_at')}")
    print(f"Ended: {item.get('ended_at')}")
    spans = item.get("spans", [])
    if not isinstance(spans, list):
        spans = []
    print(f"Spans: {len(spans)}")
    print()

    for index, span in enumerate(spans, start=1):
        if not isinstance(span, dict):
            print(f"[{index}] malformed_span")
            print(_compact(span))
            print()
            continue

        span_type = span.get("type")
        print(f"[{index}] {span_type}")
        if span_type == "llm_call":
            print(f"Provider: {span.get('provider')}")
            print(f"Model: {span.get('model')}")
            print(f"Latency: {span.get('latency_ms')} ms")
            print(f"Stop reason: {span.get('stop_reason')}")
            print(f"Usage: {_compact(span.get('usage'))}")
            print(f"Input messages: {_compact(span.get('input_messages'))}")
            print(f"Response: {_compact(span.get('response_content'))}")
        elif span_type == "tool_call":
            print(f"Tool: {span.get('tool_name')}")
            print(f"Input: {_compact(span.get('input'))}")
            print(f"Output: {_compact(span.get('output'))}")
        elif span_type == "error":
            print(f"Error: {span.get('error')}")
            print(f"Context: {_compact(span.get('context'))}")
        else:
            print(_compact(span))
        print()


def _compact(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=True, default=str)
    return text if len(text) <= 500 else text[:497] + "..."


def _print_diagnosis(run_id: str) -> None:
    item = load_run(run_id)
    if item is None:
        print(f"Run not found: {run_id}")
        return

    diagnosis = diagnose_run(item)
    if diagnosis.get("confidence", 0) < 0.6:
        print("AgentLens Diagnosis")
        print("===================")
        print()
        print("LOW CONFIDENCE")
        print()
        print(diagnosis.get("low_confidence_message"))
        print("We are not treating this as a final root cause yet.")
        print()
        print("LIKELY CAUSES:")
        for cause in diagnosis.get("likely_causes", [])[:2]:
            print(f"- {cause}")
        print()
        print("SUGGESTED FIXES:")
        for fix in diagnosis.get("likely_fixes", [])[:2]:
            print(f"- {fix}")
        return

    print("AgentLens Diagnosis")
    print("===================")
    print()
    print("ROOT CAUSE:")
    print(f"  {diagnosis['root_cause_category']}")
    print()
    print("FAILED AT:")
    tool = diagnosis.get("failed_at_tool") or "unknown tool"
    print(f"  Step {diagnosis['failed_at_step']} ({tool})")
    print()
    print("WHY:")
    print(f"  {diagnosis['explanation']}")
    print()
    print("FIX:")
    print(f"  {diagnosis['fix']}")
    print()
    print("SECONDARY:")
    secondary = diagnosis.get("secondary_issues") or []
    if secondary:
        for issue in secondary:
            print(f"- {issue}")
    else:
        print("  None")
    print()
    print(f"CONFIDENCE: {diagnosis['confidence']:.2f}")


def _anonymize_run(run_id: str) -> None:
    item = load_run(run_id)
    if item is None:
        print(f"Run not found: {run_id}")
        return

    anonymized = _anonymize_value(item)
    output_path = f"{item.get('run_id', run_id)}.anonymized.json"
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(anonymized, handle, indent=2)
    print(f"Wrote anonymized trace to {output_path}")
    print("Review it before sharing. AgentLens removes obvious secrets, but you know your data best.")


def _print_feedback_template(run_id: str) -> None:
    print(f"# AgentLens Feedback: {run_id}")
    print()
    print("## What broke?")
    print()
    print("- ")
    print()
    print("## Was diagnosis correct?")
    print()
    print("- Yes / No / Partially:")
    print("- Why:")
    print()
    print("## Did the suggested fix work?")
    print()
    print("- Yes / No / Not tried:")
    print("- Notes:")
    print()
    print("## What was confusing?")
    print()
    print("- Install:")
    print("- Setup:")
    print("- CLI output:")
    print("- Diagnosis wording:")
    print()
    print("## Would you use this again?")
    print()
    print("- Yes / No / Maybe:")
    print("- Why:")
    print()
    print("## Would you pay for this?")
    print()
    print("- Yes / No / Maybe:")
    print("- What would need to improve:")


def _anonymize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _anonymize_string(value)
    if isinstance(value, list):
        return [_anonymize_value(item) for item in value]
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if _secret_key_name(str(key)):
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = _anonymize_value(item)
        return cleaned
    return value


def _secret_key_name(key: str) -> bool:
    lowered = key.lower()
    non_secret_token_fields = {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "prompt_tokens",
        "completion_tokens",
        "cached_tokens",
        "reasoning_tokens",
        "max_tokens",
    }
    if lowered in non_secret_token_fields:
        return False
    markers = ("api_key", "apikey", "token", "secret", "password", "authorization", "cookie")
    return any(marker in lowered for marker in markers)


def _anonymize_string(value: str) -> str:
    replacements = [
        (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]"),
        (r"\bsk-[A-Za-z0-9_-]{12,}\b", "[API_KEY]"),
        (r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b", "[TOKEN]"),
        (r"\b(al_[A-Za-z0-9_-]{8,})\b", "[AGENTLENS_KEY]"),
        (r"(?i)(bearer\s+)[A-Za-z0-9._-]{12,}", r"\1[TOKEN]"),
        (r"(?i)(api[_-]?key\s*[:=]\s*)[A-Za-z0-9._-]{8,}", r"\1[API_KEY]"),
        (r"(?i)(token\s*[:=]\s*)[A-Za-z0-9._-]{8,}", r"\1[TOKEN]"),
        (r"(?i)(password\s*[:=]\s*)\S+", r"\1[PASSWORD]"),
        (r"(?i)(secret\s*[:=]\s*)[A-Za-z0-9._-]{8,}", r"\1[SECRET]"),
    ]
    cleaned = value
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned)
    return cleaned


if __name__ == "__main__":
    main()
