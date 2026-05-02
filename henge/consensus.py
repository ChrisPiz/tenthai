"""Consensus synthesis — Haiku reads the 9 frames and extracts what they agree on.

Why: a reader needs to see consensus BEFORE the dissent. Otherwise the tenth-man
has no anchor to attack, narratively. Cost: ~USD 0.04, +3-5s latency.
"""

HAIKU = "claude-haiku-4-5-20251001"
CONSENSUS_MAX_TOKENS = 800

CONSENSUS_SYSTEM = """You will receive 9 analyses of a decision, each from a different cognitive angle (each is an advisor). Your job: synthesize the emerging consensus between them.

LANGUAGE (critical): Match the language of the original question (Spanish question → Spanish answer; English question → English answer; Portuguese → Portuguese; etc.). This applies to the headline, ALL headings, and ALL body text — translate the structural labels too. Do NOT keep any heading in English if the question is not in English.

OUTPUT FORMAT (strict):

1. **Start with a markdown h1 headline (`# ...`)** of 6–14 words that synthesizes the angle of the consensus for this specific question, written in the question's language. No frame numbers or system labels. Examples — English: `# Validate before hiring — asymmetric risk dominates`. Spanish: `# Validar antes de contratar — el riesgo asimétrico domina`.
2. Section 1 — use heading `## (1) <translated label>`, where `<translated label>` is "Where the nine converge" in English / "Donde los nueve coinciden" in Spanish / equivalent in the question's language. 1 paragraph describing the points in common.
3. Section 2 — `## (2) <translated label>` where the label is "Internal tension" / "Tensión interna" / equivalent. 1 paragraph about the disagreement or nuance that persists between the 9 (if any; if there is none, write the equivalent of "No substantial tension — all frames point the same way." in the question's language).
4. Section 3 — `## (3) <translated label>` where the label is "Net lean" / "Inclinación neta" / equivalent. 1 paragraph closing with the direction the consensus points to. Start the paragraph with the bold prefix translated too: `**Net lean:**` in English / `**Inclinación neta:**` in Spanish / equivalent.

Content rules:
- 2-4 points where the 9 converge (even if each justifies them differently).
- DO NOT list advisors by name. DO NOT cite each one.
- Focus: what the 9 believe IN COMMON. What net tendency emerges.
- DO NOT interpret the decision for the user. DO NOT recommend anything new. Only synthesize.

Total: headline + 3 sections (~3 paragraphs), all in the question's language."""


async def synthesize_consensus(client, frames_responses, question):
    """Synthesize consensus from the 9 frame responses. Returns ``(text, usage)``
    or ``(None, None)`` on failure.

    Args:
        client: AsyncAnthropic instance.
        frames_responses: list of (frame_name, response_text) tuples.
        question: original user question.
    """
    if not frames_responses:
        return None, None

    block = "\n\n".join(
        f"### {name}\n{resp}" for name, resp in frames_responses
    )
    user = f"Original question:\n{question}\n\n9 analyses:\n\n{block}"

    try:
        msg = await client.messages.create(
            model=HAIKU,
            max_tokens=CONSENSUS_MAX_TOKENS,
            temperature=0,
            system=CONSENSUS_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
    except Exception:
        return None, None

    usage_obj = getattr(msg, "usage", None)
    usage = {
        "model": HAIKU,
        "input_tokens": int(getattr(usage_obj, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage_obj, "output_tokens", 0) or 0),
    }
    return msg.content[0].text.strip(), usage
