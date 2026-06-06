"""Model pricing table and cost computation helpers."""

from __future__ import annotations

from typing import Any

# Prices per million tokens (USD).  (input $/M, output $/M)
_PRICE_TABLE: dict[str, tuple[float, float]] = {
    # Anthropic
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
    # OpenAI
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "o1-mini": (3.00, 12.00),
    "o1": (15.00, 60.00),
    "o3-mini": (1.10, 4.40),
    "o3": (10.00, 40.00),
}


def _lookup_price(model: str | None) -> tuple[float, float] | None:
    if not model:
        return None
    m = model.lower()
    best = ""
    for key in _PRICE_TABLE:
        if m.startswith(key) and len(key) > len(best):
            best = key
    return _PRICE_TABLE.get(best)


def compute_cost_usd(model: str | None, usage: Any) -> float:
    """Estimate cost in USD for one LLM call. Returns 0.0 when model/usage is unknown."""
    if not isinstance(usage, dict) or not model:
        return 0.0
    price = _lookup_price(model)
    if price is None:
        return 0.0
    in_price, out_price = price
    input_tok = _n(usage.get("input_tokens")) + _n(usage.get("prompt_tokens"))
    output_tok = _n(usage.get("output_tokens")) + _n(usage.get("completion_tokens"))
    return round((input_tok * in_price + output_tok * out_price) / 1_000_000, 8)


def _n(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0
