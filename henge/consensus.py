"""Consensus synthesis — Haiku reads the 9 frames and extracts what they agree on.

Why: a reader needs to see consensus BEFORE the dissent. Otherwise the tenth-man
has no anchor to attack, narratively. Cost: ~CLP 30, +3-5s latency.
"""

HAIKU = "claude-haiku-4-5-20251001"
CONSENSUS_MAX_TOKENS = 800

CONSENSUS_SYSTEM = """You will receive 9 analyses of a decision, each from a different cognitive angle (each is an advisor). Your job: synthesize the emerging consensus between them.

OUTPUT FORMAT (strict):

1. **Start with a markdown h1 headline (`# ...`)** of 6–14 words that synthesizes the angle of the consensus for this specific question. No frame numbers or system labels. Example: "# Validate before hiring — asymmetric risk dominates".
2. **(1) Where the nine converge** — use exactly this heading as `## (1) Where the nine converge`. 1 paragraph describing the points in common.
3. **(2) Internal tension** — use `## (2) Internal tension`. 1 paragraph about the disagreement or nuance that persists between the 9 (if any; if there is none, write "No substantial tension — all frames point the same way.").
4. **(3) Net lean** — use `## (3) Net lean`. 1 paragraph closing with the direction the consensus points to. Start with `**Net lean:**` in bold.

Content rules:
- 2-4 points where the 9 converge (even if each justifies them differently).
- DO NOT list advisors by name. DO NOT cite each one.
- Focus: what the 9 believe IN COMMON. What net tendency emerges.
- DO NOT interpret the decision for the user. DO NOT recommend anything new. Only synthesize.

Match the language of the question. Total: headline + 3 sections (~3 paragraphs)."""


async def synthesize_consensus(client, frames_responses, question):
    """Synthesize consensus from the 9 frame responses. Returns text or None on failure.

    Args:
        client: AsyncAnthropic instance.
        frames_responses: list of (frame_name, response_text) tuples.
        question: original user question.
    """
    if not frames_responses:
        return None

    block = "\n\n".join(
        f"### {name}\n{resp}" for name, resp in frames_responses
    )
    user = f"Original question:\n{question}\n\n9 analyses:\n\n{block}"

    try:
        msg = await client.messages.create(
            model=HAIKU,
            max_tokens=CONSENSUS_MAX_TOKENS,
            system=CONSENSUS_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None
