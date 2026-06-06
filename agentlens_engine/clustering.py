"""Failure clustering for AgentLens.

Groups all captured runs by their failure pattern so you can see that e.g.
"34% of your failures are tool_selection failures on search_web — fix the
description once and eliminate a third of all errors."

Cluster key
───────────
  (root_cause_category, primary_failing_tool)

Heuristics are used when a stored diagnosis is not present.
"""

from __future__ import annotations

import json
import re
from typing import Any


# ── Public API ────────────────────────────────────────────────────────────────

def cluster_failures(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group runs by failure pattern.

    Parameters
    ----------
    runs: all raw run JSON dicts (pass the output of load_runs())

    Returns a list (sorted by count desc) of::

        {
            "cluster_key": str,
            "category": str,
            "failed_tool": str | None,
            "count": int,
            "percentage": float,      # share of all error runs (0–1)
            "example_run_ids": list[str],
            "example_fix": str,
            "error_signals": list[str],
        }
    """
    error_runs = [r for r in runs if isinstance(r, dict) and r.get("status") in ("error", "failure")]
    if not error_runs:
        return []

    clusters: dict[str, dict[str, Any]] = {}
    for run in error_runs:
        fp = _fingerprint_run(run)
        key = fp["key"]
        if key not in clusters:
            clusters[key] = {
                "cluster_key": key,
                "category": fp["category"],
                "failed_tool": fp["failed_tool"],
                "count": 0,
                "example_run_ids": [],
                "example_fix": fp["fix"],
                "error_signals": fp["error_signals"],
            }
        clusters[key]["count"] += 1
        if len(clusters[key]["example_run_ids"]) < 3:
            rid = run.get("run_id") or ""
            if rid:
                clusters[key]["example_run_ids"].append(rid[:8])
        # Prefer a non-empty fix example
        if not clusters[key]["example_fix"] and fp["fix"]:
            clusters[key]["example_fix"] = fp["fix"]

    total = len(error_runs)
    result = []
    for cluster in clusters.values():
        cluster["percentage"] = round(cluster["count"] / total, 3)
        result.append(cluster)

    result.sort(key=lambda c: c["count"], reverse=True)
    return result


def print_clusters(clusters: list[dict[str, Any]], total_runs: int | None = None) -> None:
    """Pretty-print clusters to stdout."""
    if not clusters:
        print("No failure clusters found. Run more agents to build up history.")
        return

    error_total = sum(c["count"] for c in clusters)
    header = f"Failure Clusters — {error_total} failed run(s)"
    if total_runs is not None:
        header += f" out of {total_runs} total"
    print(header)
    print("=" * 60)
    print()

    for i, cluster in enumerate(clusters, start=1):
        pct = cluster["percentage"] * 100
        count = cluster["count"]
        category = cluster["category"] or "unknown"
        tool = cluster["failed_tool"] or "various tools"
        key = cluster["cluster_key"]
        print(f"#{i}  {category}  ·  {tool}")
        print(f"    {count} run(s)  ({pct:.0f}% of failures)")
        signals = cluster.get("error_signals") or []
        if signals:
            print(f"    signals: {', '.join(signals[:5])}")
        examples = cluster.get("example_run_ids") or []
        if examples:
            print(f"    example run(s): {', '.join(examples)}")
        fix = cluster.get("example_fix") or ""
        if fix:
            print(f"    fix: {fix[:120]}{'…' if len(fix) > 120 else ''}")
        print()


# ── Internal ─────────────────────────────────────────────────────────────────

def _fingerprint_run(run: dict[str, Any]) -> dict[str, Any]:
    spans = [s for s in (run.get("spans") or []) if isinstance(s, dict)]

    # --- category ---
    diag = run.get("_diagnosis") or {}
    category = diag.get("root_cause_category") or ""
    fix = diag.get("fix") or ""

    if not category:
        category = _infer_category(spans, run)

    # --- failed tool ---
    failed_tool = diag.get("failed_at_tool")
    if not failed_tool:
        failed_tool = _infer_failed_tool(spans)

    # --- error signals ---
    error_signals = _extract_signals(spans)

    key = f"{category or 'unknown'}::{failed_tool or 'none'}"
    return {
        "key": key,
        "category": category,
        "failed_tool": failed_tool,
        "fix": fix,
        "error_signals": error_signals,
    }


def _infer_category(spans: list[dict[str, Any]], run: dict[str, Any]) -> str:
    all_text = json.dumps(spans, default=str).lower()
    # Loop: same tool+input repeated
    if _tool_repeat_exists(spans):
        return "loop"
    # Overflow
    if any(kw in all_text for kw in ["context window", "truncated", "pushed out"]):
        return "overflow"
    # Tool selection: ambiguous descriptions and wrong tool used
    if _has_ambiguous_tools(spans):
        return "tool_selection"
    # Cascade: stale/corrupted data
    if any(kw in all_text for kw in ["stale", "corrupted", "invalid id"]):
        return "cascade"
    # State drift
    if any(kw in all_text for kw in ["unrelated", "lost original goal", "off-topic"]):
        return "state_drift"
    # Generic fallback
    return "tool_selection"


def _infer_failed_tool(spans: list[dict[str, Any]]) -> str | None:
    for s in reversed(spans):
        if s.get("type") == "error":
            ctx = s.get("context") or {}
            if isinstance(ctx, dict) and ctx.get("tool_name"):
                return ctx["tool_name"]
    for s in spans:
        if s.get("type") == "tool_call":
            out = s.get("output")
            if isinstance(out, dict) and (out.get("status") == "error" or out.get("error")):
                return s.get("tool_name")
    return None


def _extract_signals(spans: list[dict[str, Any]]) -> list[str]:
    signals: list[str] = []
    for s in spans:
        if s.get("type") not in ("error", "tool_call"):
            continue
        texts = [
            _to_str(s.get("error")),
            _to_str((s.get("output") or {}).get("error") if isinstance(s.get("output"), dict) else None),
        ]
        for t in texts:
            tokens = re.findall(r"\b[a-z]{4,}\b", t.lower())
            for tok in tokens:
                if tok not in _STOP_WORDS and tok not in signals:
                    signals.append(tok)
                    if len(signals) >= 8:
                        return signals
    return signals


def _tool_repeat_exists(spans: list[dict[str, Any]]) -> bool:
    seen: set[str] = set()
    for s in spans:
        if s.get("type") != "tool_call":
            continue
        key = json.dumps({"tool": s.get("tool_name"), "input": s.get("input")}, sort_keys=True, default=str)
        if key in seen:
            return True
        seen.add(key)
    return False


def _has_ambiguous_tools(spans: list[dict[str, Any]]) -> bool:
    """True if any two tools across the run have descriptions with Jaccard similarity >= 0.6.
    Uses the same threshold as the classifier so clustering matches diagnosis behaviour.
    """
    descriptions: list[str] = []
    for s in spans:
        if s.get("type") != "llm_call":
            continue
        for t in (s.get("tools") or []):
            if not isinstance(t, dict):
                continue
            desc = (t.get("description") or (t.get("function") or {}).get("description") or "").strip().lower()
            if desc and desc not in descriptions:
                descriptions.append(desc)
    for i in range(len(descriptions)):
        for j in range(i + 1, len(descriptions)):
            if _desc_similarity(descriptions[i], descriptions[j]) >= 0.6:
                return True
    return False


def _desc_similarity(a: str, b: str) -> float:
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


_STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was",
    "not", "have", "been", "will", "only", "also", "more", "into",
}
