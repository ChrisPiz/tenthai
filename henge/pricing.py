"""Anthropic + OpenAI token pricing for Henge cost accounting.

Prices are USD per 1M tokens. Verified against published rate cards on
2026-05-01. Pricing changes occasionally — bump the constants below and the
``HENGE_PRICING_VERSION`` if Anthropic or OpenAI revise their cards. Any
report persisted to disk records the pricing version it was costed against
so historical totals remain interpretable after a price change.

Sources:
- https://docs.anthropic.com/en/docs/about-claude/pricing
- https://platform.openai.com/docs/pricing

The constants here are the only place in the codebase where dollar amounts
appear in a code path. If you need to override (enterprise pricing, custom
endpoints), set ``HENGE_PRICING_OVERRIDE`` to a JSON path or read this module
in your own wrapper.
"""
from __future__ import annotations

HENGE_PRICING_VERSION = "2026-05-01"

ANTHROPIC_PRICING_PER_MTOK = {
    "claude-sonnet-4-6":            {"input": 3.00,  "output": 15.00},
    "claude-opus-4-7":              {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001":    {"input": 1.00,  "output": 5.00},
}

EMBEDDING_PRICING_PER_MTOK = {
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
    "voyage-3-large":         0.18,
}


def anthropic_call_cost(usage: dict | None) -> float:
    """Cost in USD for one Anthropic call.

    ``usage = {"model": str, "input_tokens": int, "output_tokens": int}``.
    Returns 0.0 for unknown models or missing usage so cost accounting
    degrades gracefully instead of failing the whole run.
    """
    if not usage:
        return 0.0
    model = usage.get("model", "")
    rates = ANTHROPIC_PRICING_PER_MTOK.get(model)
    if not rates:
        return 0.0
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
    ) / 1_000_000


def embedding_cost(model: str, n_input_tokens: int) -> float:
    """Cost in USD for an embedding call. Tokens are summed across all texts.

    Henge does not directly read embedding token counts — the OpenAI/Voyage
    SDK responses include usage but the embed module does not propagate it
    yet (TODO v0.6). For now we accept an explicit token estimate; passing 0
    yields 0.0 and the cost line item simply reads as a floor.
    """
    rate = EMBEDDING_PRICING_PER_MTOK.get(model, 0.0)
    return (max(0, int(n_input_tokens)) * rate) / 1_000_000


def total_cost(
    advisor_usages: list[dict | None],
    scoping_usage: dict | None,
    consensus_usage: dict | None,
    embedding_model: str,
    embedding_input_tokens: int = 0,
) -> dict:
    """Aggregate cost breakdown across one full Henge run.

    Returns ``{"anthropic_usd", "openai_usd", "total_usd", "pricing_version"}``.
    All values are rounded to 6 decimals to keep JSON tidy without losing
    sub-cent fidelity (a single embedding call is on the order of $0.0005).
    """
    anthropic = sum(anthropic_call_cost(u) for u in advisor_usages)
    anthropic += anthropic_call_cost(scoping_usage)
    anthropic += anthropic_call_cost(consensus_usage)
    embed = embedding_cost(embedding_model, embedding_input_tokens)
    return {
        "anthropic_usd": round(anthropic, 6),
        "embedding_usd": round(embed, 6),
        "total_usd":    round(anthropic + embed, 6),
        "pricing_version": HENGE_PRICING_VERSION,
    }
