"""Simple local diagnosis evaluation for fixture and real-world cases."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .diagnose import diagnose_run


FIXTURE_EXPECTED = {
    "phase2_tool_selection": ("tool_selection", 2),
    "phase2_context_pollution": ("context_pollution", 1),
    "phase2_loop": ("loop", 4),
    "phase2_state_drift": ("state_drift", 1),
    "phase2_cascade": ("cascade", 2),
    "phase2_overflow": ("overflow", 4),
}


def evaluate_cases(
    fixture_dir: Path = Path("tests/phase2_runs"),
    real_world_dir: Path = Path("real_world_cases"),
) -> dict[str, Any]:
    results = []
    results.extend(_evaluate_directory(fixture_dir, FIXTURE_EXPECTED, source="fixture"))
    results.extend(_evaluate_directory(real_world_dir, {}, source="real_world"))
    return _summarize(results)


def print_evaluation(report: dict[str, Any]) -> None:
    print("AgentLens Diagnosis Evaluation")
    print()
    print(f"Cases: {report['total_cases']}")
    print(f"Scored cases: {report['scored_cases']}")
    print(f"Overall accuracy: {report['overall_accuracy']:.0%}")
    print(f"Low-confidence rate: {report['low_confidence_rate']:.0%}")
    print(f"Average latency: {report['average_latency_ms']:.2f} ms")
    print()
    print("Accuracy by category:")
    for category, accuracy in sorted(report["accuracy_by_category"].items()):
        print(f"- {category}: {accuracy:.0%}")
    if report["unscored_real_world_cases"]:
        print()
        print("Unscored real-world cases:")
        for case in report["unscored_real_world_cases"]:
            print(f"- {case}")


def _evaluate_directory(
    directory: Path, expected: dict[str, tuple[str, int]], source: str
) -> list[dict[str, Any]]:
    if not directory.exists():
        return []

    results = []
    for path in sorted(directory.glob("*.json")):
        run = _load_json(path)
        if run is None:
            continue
        run_id = str(run.get("run_id") or path.stem)
        expected_category, expected_step = _expected_for(run, expected.get(run_id))

        started = time.perf_counter()
        diagnosis = diagnose_run(run, use_llm=False)
        latency_ms = (time.perf_counter() - started) * 1000

        scored = expected_category is not None and expected_step is not None
        correct = (
            scored
            and diagnosis["root_cause_category"] == expected_category
            and diagnosis["failed_at_step"] == expected_step
        )
        results.append(
            {
                "source": source,
                "path": str(path),
                "run_id": run_id,
                "expected_category": expected_category,
                "expected_step": expected_step,
                "actual_category": diagnosis["root_cause_category"],
                "actual_step": diagnosis["failed_at_step"],
                "confidence": diagnosis["confidence"],
                "latency_ms": latency_ms,
                "scored": scored,
                "correct": bool(correct),
            }
        )
    return results


def _summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [result for result in results if result["scored"]]
    low_confidence = [result for result in results if result["confidence"] < 0.6]
    latency_values = [result["latency_ms"] for result in results]
    by_category: dict[str, list[bool]] = {}
    for result in scored:
        by_category.setdefault(result["expected_category"], []).append(result["correct"])

    return {
        "total_cases": len(results),
        "scored_cases": len(scored),
        "overall_accuracy": _rate([result["correct"] for result in scored]),
        "low_confidence_rate": len(low_confidence) / len(results) if results else 0.0,
        "average_latency_ms": sum(latency_values) / len(latency_values) if latency_values else 0.0,
        "accuracy_by_category": {
            category: _rate(values) for category, values in by_category.items()
        },
        "unscored_real_world_cases": [
            result["path"]
            for result in results
            if result["source"] == "real_world" and not result["scored"]
        ],
    }


def _expected_for(run: dict[str, Any], fallback: tuple[str, int] | None) -> tuple[str | None, int | None]:
    expected = run.get("expected_diagnosis") or run.get("expected")
    if isinstance(expected, dict):
        return expected.get("root_cause_category"), expected.get("failed_at_step")
    if fallback:
        return fallback
    return None, None


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _rate(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0
