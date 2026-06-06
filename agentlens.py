"""Public AgentLens SDK and CLI entrypoint."""

from __future__ import annotations

import argparse
from datetime import datetime
import importlib
import json
import re
from pathlib import Path
from typing import Any

from agentlens_engine.diagnose import diagnose_run
from agentlens_engine.evaluate import evaluate_cases, print_evaluation
from agentlens_sdk import AgentLensClient, init, load_run, load_runs, record_tool_result, run, save_run
from agentlens_sdk.collector import RUNS_DIR

__all__ = [
    "AgentLensClient",
    "init",
    "record_tool_result",
    "run",
    "save_run",
]

CLI_COMMANDS = {
    "runs",
    "diagnose",
    "anonymize",
    "feedback-template",
    "evaluate",
    "doctor",
    "stats",
}


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
    stats_parser = subparsers.add_parser("stats")
    stats_parser.add_argument("run_id", nargs="?")
    subparsers.add_parser("evaluate")
    subparsers.add_parser("doctor")

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

    if args.command == "stats":
        _print_stats(args.run_id)
        return

    if args.command == "evaluate":
        print_evaluation(evaluate_cases())
        return

    if args.command == "doctor":
        _print_doctor()
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

    try:
        diagnosis = diagnose_run(item)
    except ValueError as exc:
        print(f"Diagnosis failed: {exc}")
        return
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
    print("## Was diagnosis useful?")
    print()
    print("- Yes / No / Partially:")
    print("- Did it save debugging time:")
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


def _print_stats(run_id: str | None) -> None:
    if run_id:
        item = load_run(run_id)
        if item is None:
            print(f"Run not found: {run_id}")
            return
        _print_run_stats(item)
        return

    runs = load_runs()
    if not runs:
        print("No AgentLens runs found in .agentlens/runs/")
        return

    summaries = [_summarize_run(item) for item in runs[:20]]
    totals = _merge_stats(summaries)

    print("AgentLens Stats")
    print()
    print(f"Runs analyzed: {len(summaries)}")
    print(f"LLM calls: {totals['llm_calls']}")
    print(f"Tool calls: {totals['tool_calls']}")
    print(f"Errors: {totals['errors']}")
    print(f"Input tokens: {totals['input_tokens']}")
    print(f"Output tokens: {totals['output_tokens']}")
    print(f"Total tokens: {totals['total_tokens']}")
    print(f"Captured latency: {_format_ms(totals['latency_ms'])}")
    print(f"Captured cost: {_format_cost(totals['cost_usd'])}")
    print()
    print(f"{'run_id':36}  {'name':24}  {'status':8}  {'llm':>3}  {'tool':>4}  {'tokens':>8}  latency")
    for summary in summaries:
        print(
            f"{summary['run_id'][:36]:36}  "
            f"{summary['name'][:24]:24}  "
            f"{summary['status'][:8]:8}  "
            f"{summary['llm_calls']:>3}  "
            f"{summary['tool_calls']:>4}  "
            f"{summary['total_tokens']:>8}  "
            f"{_format_ms(summary['latency_ms'])}"
        )


def _print_run_stats(item: dict[str, Any]) -> None:
    summary = _summarize_run(item)

    print("AgentLens Run Stats")
    print()
    print(f"Run ID: {summary['run_id']}")
    print(f"Name: {summary['name']}")
    print(f"Status: {summary['status']}")
    print(f"Started: {item.get('started_at')}")
    print(f"Ended: {item.get('ended_at')}")
    print(f"Duration: {_format_ms(summary['duration_ms'])}")
    print()
    print("Calls:")
    print(f"  LLM calls: {summary['llm_calls']}")
    print(f"  Tool calls: {summary['tool_calls']}")
    print(f"  Errors: {summary['errors']}")
    print()
    print("Tokens:")
    print(f"  Input tokens: {summary['input_tokens']}")
    print(f"  Output tokens: {summary['output_tokens']}")
    print(f"  Total tokens: {summary['total_tokens']}")
    print()
    print("Performance:")
    print(f"  Captured latency: {_format_ms(summary['latency_ms'])}")
    if summary["slowest_step"]:
        print(f"  Slowest step: {summary['slowest_step']}")
    else:
        print("  Slowest step: unavailable")
    print()
    print("Cost:")
    print(f"  Captured cost: {_format_cost(summary['cost_usd'])}")
    if summary["cost_usd"] == 0:
        print("  Note: provider billing cost is not captured unless traces include cost_usd.")
    print()
    print("Providers:")
    _print_count_map(summary["providers"])
    print()
    print("Models:")
    _print_count_map(summary["models"])


def _summarize_run(item: dict[str, Any]) -> dict[str, Any]:
    spans = item.get("spans", [])
    if not isinstance(spans, list):
        spans = []
    safe_spans = [span for span in spans if isinstance(span, dict)]

    providers: dict[str, int] = {}
    models: dict[str, int] = {}
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    latency_ms = 0.0
    cost_usd = 0.0
    slowest_latency = -1.0
    slowest_step = ""

    for index, span in enumerate(safe_spans, start=1):
        provider = span.get("provider")
        model = span.get("model")
        if provider:
            providers[str(provider)] = providers.get(str(provider), 0) + 1
        if model:
            models[str(model)] = models.get(str(model), 0) + 1

        usage = span.get("usage") if isinstance(span.get("usage"), dict) else {}
        usage_input = _number(usage.get("input_tokens")) + _number(usage.get("prompt_tokens"))
        usage_output = _number(usage.get("output_tokens")) + _number(usage.get("completion_tokens"))
        usage_total = _number(usage.get("total_tokens"))
        if usage_total == 0 and (usage_input or usage_output):
            usage_total = usage_input + usage_output
        input_tokens += int(usage_input)
        output_tokens += int(usage_output)
        total_tokens += int(usage_total)

        span_latency = _number(span.get("latency_ms"))
        latency_ms += span_latency
        if span_latency > 0 and span_latency > slowest_latency:
            slowest_latency = span_latency
            slowest_step = _describe_span(index, span, span_latency)

        cost_usd += _extract_cost_usd(span)

    return {
        "run_id": str(item.get("run_id") or ""),
        "name": str(item.get("name") or ""),
        "status": str(item.get("status") or ""),
        "llm_calls": sum(1 for span in safe_spans if span.get("type") == "llm_call"),
        "tool_calls": sum(1 for span in safe_spans if span.get("type") == "tool_call"),
        "errors": sum(1 for span in safe_spans if span.get("type") == "error"),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms,
        "duration_ms": _duration_ms(item.get("started_at"), item.get("ended_at")),
        "cost_usd": cost_usd,
        "slowest_step": slowest_step if slowest_latency >= 0 else "",
        "providers": providers,
        "models": models,
    }


def _merge_stats(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    totals = {
        "llm_calls": 0,
        "tool_calls": 0,
        "errors": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "latency_ms": 0.0,
        "cost_usd": 0.0,
    }
    for summary in summaries:
        for key in totals:
            totals[key] += summary[key]
    return totals


def _extract_cost_usd(value: Any) -> float:
    if isinstance(value, dict):
        total = 0.0
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"cost_usd", "total_cost_usd"}:
                total += _number(item)
            elif lowered in {"cost", "total_cost"} and "token" not in lowered:
                total += _number(item)
            elif isinstance(item, (dict, list)):
                total += _extract_cost_usd(item)
        return total
    if isinstance(value, list):
        return sum(_extract_cost_usd(item) for item in value)
    return 0.0


def _duration_ms(started_at: Any, ended_at: Any) -> float:
    if not isinstance(started_at, str) or not isinstance(ended_at, str):
        return 0.0
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        ended = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return max((ended - started).total_seconds() * 1000, 0.0)


def _describe_span(index: int, span: dict[str, Any], latency_ms: float) -> str:
    label = str(span.get("type") or "unknown")
    if span.get("tool_name"):
        label += f" ({span['tool_name']})"
    elif span.get("model"):
        label += f" ({span['model']})"
    return f"Step {index}: {label} at {_format_ms(latency_ms)}"


def _print_count_map(values: dict[str, int]) -> None:
    if not values:
        print("  None captured")
        return
    for name, count in sorted(values.items()):
        print(f"  {name}: {count}")


def _format_ms(value: float) -> str:
    if value <= 0:
        return "unavailable"
    if value < 1000:
        return f"{value:.2f} ms"
    return f"{value / 1000:.2f} s"


def _format_cost(value: float) -> str:
    if value <= 0:
        return "not captured"
    return f"${value:.6f}"


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _print_doctor() -> None:
    checks = [
        _doctor_check("imports", _doctor_imports),
        _doctor_check("local storage", _doctor_local_storage),
        _doctor_check("diagnosis fixture", _doctor_diagnosis_fixture),
        _doctor_check("messy trace handling", _doctor_messy_trace_handling),
        _doctor_check("anonymization", _doctor_anonymization),
        _doctor_check("evaluation", _doctor_evaluation),
    ]

    print("AgentLens Doctor")
    print()
    for check in checks:
        line = f"{check['status']:<5} {check['name']}"
        if check["message"]:
            line += f" - {check['message']}"
        print(line)
    print()

    if any(check["status"] == "FAIL" for check in checks):
        print("Result: needs attention")
    elif any(check["status"] == "WARN" for check in checks):
        print("Result: healthy with warnings")
    else:
        print("Result: healthy")


def _doctor_check(name: str, check: Any) -> dict[str, str]:
    try:
        status, message = check()
    except Exception as exc:  # Doctor should report broken states, not crash.
        status, message = "FAIL", str(exc)
    return {"name": name, "status": status, "message": message}


def _doctor_imports() -> tuple[str, str]:
    modules = [
        "agentlens_sdk",
        "agentlens_sdk.collector",
        "agentlens_engine.classifier",
        "agentlens_engine.preprocess",
        "agentlens_engine.diagnose",
        "agentlens_engine.evaluate",
        "agentlens_engine.fixes",
    ]
    for module in modules:
        importlib.import_module(module)

    # Verify the public SDK surface is intact (not a self-referential import)
    import agentlens as _al
    if not callable(getattr(_al, "init", None)):
        return "FAIL", "agentlens.init is missing or not callable"

    if not CLI_COMMANDS.issuperset({"doctor", "diagnose", "evaluate"}):
        return "FAIL", "required CLI commands are missing"
    return "PASS", ""


def _doctor_local_storage() -> tuple[str, str]:
    run_id = "agentlens_doctor_storage_check"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "name": "doctor",
        "started_at": "2026-05-18T00:00:00+00:00",
        "ended_at": "2026-05-18T00:00:01+00:00",
        "status": "success",
        "spans": [],
    }
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        loaded = load_run(run_id)
        if not loaded or loaded.get("run_id") != run_id:
            return "FAIL", "run JSON could not be read back"
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return "PASS", ""


def _doctor_diagnosis_fixture() -> tuple[str, str]:
    diagnosis = diagnose_run(_doctor_tool_selection_run(), use_llm=False)
    required = {
        "root_cause_category",
        "failed_at_step",
        "confidence",
        "explanation",
        "fix",
    }
    missing = required - set(diagnosis)
    if missing:
        return "FAIL", f"diagnosis missing {', '.join(sorted(missing))}"
    if not diagnosis["root_cause_category"]:
        return "FAIL", "diagnosis did not return a category"
    if not isinstance(diagnosis["failed_at_step"], int):
        return "FAIL", "diagnosis did not return a failed step"
    if not isinstance(diagnosis["confidence"], (int, float)):
        return "FAIL", "diagnosis did not return confidence"
    if not diagnosis["explanation"] or not diagnosis["fix"]:
        return "FAIL", "diagnosis output was not readable"
    return "PASS", ""


def _doctor_messy_trace_handling() -> tuple[str, str]:
    messy_run = {
        "run_id": "agentlens_doctor_messy",
        "name": "doctor_messy",
        "status": "running",
        "spans": [
            "malformed span",
            {
                "id": "partial",
                "type": "llm_call",
                "provider": "openai",
                "input_messages": [],
                "response_content": {"unexpected": ["partial", None]},
            },
        ],
    }
    diagnosis = diagnose_run(messy_run, use_llm=False)
    if diagnosis.get("confidence", 1.0) >= 0.6:
        return "WARN", "messy trace produced medium/high confidence"
    if not diagnosis.get("low_confidence_message"):
        return "FAIL", "messy trace did not include low-confidence messaging"
    return "PASS", ""


def _doctor_anonymization() -> tuple[str, str]:
    raw = {
        "email": "alex@example.com",
        "api_key": "sk-test123456789abcdef",
        "headers": {"Authorization": "Bearer testBearerToken123456789"},
        "text": "password=hunter2 secret=supersecretvalue token=tok_live_1234567890abcdef",
        "usage": {"input_tokens": 123, "output_tokens": 45, "total_tokens": 168},
    }
    cleaned = _anonymize_value(raw)
    cleaned_text = json.dumps(cleaned, sort_keys=True)
    leaked = [
        value
        for value in [
            "alex@example.com",
            "sk-test123456789abcdef",
            "testBearerToken123456789",
            "hunter2",
            "supersecretvalue",
            "tok_live_1234567890abcdef",
        ]
        if value in cleaned_text
    ]
    if leaked:
        return "FAIL", f"secret leaked: {leaked[0]}"
    usage = cleaned.get("usage", {})
    if usage.get("input_tokens") != 123 or usage.get("output_tokens") != 45:
        return "FAIL", "token counts were redacted"
    return "PASS", ""


def _doctor_evaluation() -> tuple[str, str]:
    report = evaluate_cases()
    required = {"fixture_accuracy", "low_confidence_rate", "fixture_cases"}
    missing = required - set(report)
    if missing:
        return "FAIL", f"evaluation missing {', '.join(sorted(missing))}"
    if report["fixture_cases"] == 0:
        return "FAIL", "no fixture cases found"
    if report["fixture_accuracy"] < 1.0:
        return "FAIL", f"fixture accuracy {report['fixture_accuracy']:.0%}"
    return "PASS", ""


def _doctor_tool_selection_run() -> dict[str, Any]:
    # Prefer the real fixture so the doctor tests the same data as evaluate.
    _fixture_path = Path(__file__).resolve().parent / "tests" / "phase2_runs" / "phase2_tool_selection.json"
    if _fixture_path.exists():
        try:
            return json.loads(_fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    # Fallback inline fixture when tests/ directory is not present.
    return {
        "run_id": "agentlens_doctor_tool_selection",
        "name": "doctor_tool_selection",
        "status": "error",
        "spans": [
            {
                "type": "llm_call",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-latest",
                "input_messages": [
                    {
                        "role": "user",
                        "content": "Find the renewal status for customer:alex using local records.",
                    }
                ],
                "tools": [
                    {"name": "search_web", "description": "find info about a topic"},
                    {"name": "query_db", "description": "find info about a topic"},
                ],
                "response_content": [
                    {
                        "type": "text",
                        "text": "Both tools look similar, so I will use search_web.",
                    },
                    {
                        "type": "tool_use",
                        "name": "search_web",
                        "input": {"query": "customer:alex renewal status"},
                    },
                ],
                "usage": {"input_tokens": 100, "output_tokens": 30},
            },
            {
                "type": "tool_call",
                "tool_name": "search_web",
                "input": {"query": "customer:alex renewal status"},
                "output": {
                    "status": "error",
                    "error": "Customer records are only available in query_db.",
                },
            },
        ],
    }


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
