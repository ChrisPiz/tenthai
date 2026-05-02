"""Scoping phase — generates clarifying questions before running the 10 agents.

Without scoping, frames speculate or stay generic. With scoping, the user provides
the missing context (income, location, constraints) so frames apply to facts.

Uses Haiku for speed/cost: 1 call ≈ USD 0.01, returns in ~3-5s.
"""
import json

HAIKU = "claude-haiku-4-5-20251001"
SCOPING_MAX_TOKENS = 800

SCOPING_SYSTEM = """You will receive a decision question. Your job: generate 4-7 concrete questions an expert advisor would ask the user before being able to give grounded advice.

The answers will feed 9 advisors with distinct cognitive angles: empirical (data, numbers), historical (precedents, cases), first-principles (constraints), analogical, systemic (second-order), ethical (stakeholders), contrarian (assumptions), pre-mortem (failure modes), optimist (upside).

Look for questions that cover (when relevant to the domain):
- Personal quantitative data (income, savings, deadlines, debts, age, dependents)
- Constraints and deal-breakers
- Geography, community, location
- Relationships and affected stakeholders
- Subjective preferences, life philosophy, priorities
- Information NOT already in the original question

Rules:
- 4-7 questions, no more, no less.
- Each concrete, specific to the domain. NOT generic.
- One question per entry — no "and"-compound questions.
- DO NOT repeat information already in the question.
- Match the language of the original question.

Output: JSON array of strings. ONLY the JSON, no prose, no markdown fence.
Format example: ["What is your approximate net monthly income?", "Which neighborhoods would you be willing to live in?"]"""


async def generate_questions(client, question):
    """Returns ``(questions, usage)``. On any failure: ``(None, None)``.

    Tolerates 3-8 questions to handle edge cases. Strips markdown code fences
    that Haiku sometimes wraps around JSON.
    """
    try:
        msg = await client.messages.create(
            model=HAIKU,
            max_tokens=SCOPING_MAX_TOKENS,
            temperature=0,
            system=SCOPING_SYSTEM,
            messages=[{"role": "user", "content": question}],
        )
        text = msg.content[0].text.strip()
    except Exception:
        return None, None

    usage_obj = getattr(msg, "usage", None)
    usage = {
        "model": HAIKU,
        "input_tokens": int(getattr(usage_obj, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage_obj, "output_tokens", 0) or 0),
    }

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        questions = json.loads(text)
    except json.JSONDecodeError:
        return None, usage

    if not isinstance(questions, list):
        return None, usage
    if not (3 <= len(questions) <= 8):
        return None, usage
    return [str(q).strip() for q in questions if str(q).strip()], usage
