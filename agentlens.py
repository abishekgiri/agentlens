"""Public AgentLens SDK and CLI entrypoint."""

from __future__ import annotations

import argparse
import json
from typing import Any

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

    args = parser.parse_args()

    if args.command == "runs" and args.runs_command == "list":
        _print_runs_list()
        return

    if args.command == "runs" and args.runs_command == "show":
        _print_run_detail(args.run_id)
        return

    if args.command == "diagnose":
        print("RCA engine is coming in Phase 2. Run captured successfully.")
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
    print(f"Spans: {len(item.get('spans', []))}")
    print()

    for index, span in enumerate(item.get("spans", []), start=1):
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
    text = json.dumps(value, ensure_ascii=True)
    return text if len(text) <= 500 else text[:497] + "..."


if __name__ == "__main__":
    main()
