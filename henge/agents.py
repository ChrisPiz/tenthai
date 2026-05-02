"""Loads prompts at import, runs 9 cognitive frames in parallel + tenth-man dissenter sequentially."""
import asyncio
import hashlib
from pathlib import Path

FRAMES = [
    "empirical",
    "historical",
    "first-principles",
    "analogical",
    "systemic",
    "ethical",
    "soft-contrarian",
    "radical-optimist",
    "pre-mortem",
]
TENTH_MAN = "tenth-man"

_FILE_MAP = {
    "empirical": "01-empirical.md",
    "historical": "02-historical.md",
    "first-principles": "03-first-principles.md",
    "analogical": "04-analogical.md",
    "systemic": "05-systemic.md",
    "ethical": "06-ethical.md",
    "soft-contrarian": "07-soft-contrarian.md",
    "radical-optimist": "08-radical-optimist.md",
    "pre-mortem": "09-pre-mortem.md",
    "tenth-man": "10-tenth-man-steelman.md",
}

_PROMPT_DIR = Path(__file__).parent / "prompts"


def _load_prompts() -> dict:
    """Load all prompt markdowns once at module import. Single source of truth.

    Loaded eagerly so disk reads never happen on the hot path, and prompts
    cannot drift between concurrent invocations.
    """
    prompts = {}
    for name, filename in _FILE_MAP.items():
        path = _PROMPT_DIR / filename
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Prompt file empty: {filename}")
        prompts[name] = text
    return prompts


PROMPTS = _load_prompts()


def _compute_prompts_hash() -> str:
    """SHA256 over ordered concat of the 10 prompt files. Short prefix for readability.

    Persisted in every report so any future change to prompts is traceable —
    reports with a different hash are not directly comparable.
    """
    blob = "".join(PROMPTS[name] for name in [*FRAMES, TENTH_MAN]).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


PROMPTS_HASH = _compute_prompts_hash()

SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-7"
FRAME_MAX_TOKENS = 1500   # 4-6 paragraphs of reasoning per frame
TENTH_MAX_TOKENS = 3500   # 5-7 paragraphs for tenth-man (more cognitively demanding)

# v0.5: temperature=0 pinned across all calls. Reproducibility > stylistic
# variance — see WHITEPAPER.md "Pre-registered runtime decisions".
TEMPERATURE = 0

# Reasoning-tier models (e.g. Opus 4.7 with extended thinking enabled by
# default) reject the ``temperature`` parameter outright. We omit it for
# those models and rely on the model's built-in determinism for the
# tenth-man dissent. Sonnet 4.6 and Haiku 4.5 still accept temperature=0.
# Add models to this set as Anthropic ships new reasoning models that
# refuse temperature; the runtime fallback below will also catch unknown
# cases gracefully.
MODELS_WITHOUT_TEMPERATURE = {OPUS}


def _extract_usage(msg, model):
    """Read token counts from an Anthropic message. Tolerant to mock objects.

    Real Anthropic responses always populate ``usage``. Tests may stub messages
    without it; in that case we record zeros so cost accounting still works.
    """
    usage = getattr(msg, "usage", None)
    return {
        "model": model,
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
    }


async def _call_anthropic(client, model, system, user, max_tokens, temperature=TEMPERATURE):
    """Run a single Anthropic call. Returns ``(text, usage_dict)``.

    Usage dict: ``{"model": ..., "input_tokens": int, "output_tokens": int}``.

    ``temperature`` defaults to the pre-registered ``TEMPERATURE = 0`` so any
    caller that does not opt in still gets reproducible runs. K-runs mode
    (server.decide(k_runs=K, run_temperature=T)) overrides per call.

    Models in ``MODELS_WITHOUT_TEMPERATURE`` reject the parameter (reasoning-
    tier with mandatory extended thinking) — we omit it for those. Any other
    model that surfaces a temperature-related API error triggers a one-shot
    retry without the parameter so we degrade gracefully when Anthropic adds
    new reasoning models without us shipping a code update.
    """
    base_kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }

    if model in MODELS_WITHOUT_TEMPERATURE:
        msg = await client.messages.create(**base_kwargs)
    else:
        try:
            msg = await client.messages.create(**base_kwargs, temperature=temperature)
        except Exception as exc:
            err = str(exc).lower()
            temperature_rejected = any(
                kw in err
                for kw in ("temperature", "extended thinking", "thinking is enabled")
            )
            if not temperature_rejected:
                raise
            msg = await client.messages.create(**base_kwargs)

    return msg.content[0].text, _extract_usage(msg, model)


async def run_agent(client, frame, question, context=None, temperature=TEMPERATURE):
    """Run one cognitive frame. Returns ``(text, usage_dict)``."""
    system = PROMPTS[frame]
    user = question if not context else f"{question}\n\nAdditional context:\n{context}"
    return await _call_anthropic(client, SONNET, system, user, FRAME_MAX_TOKENS, temperature)


async def run_tenth_man(client, successful_frames, question, temperature=TEMPERATURE):
    """Receives only successful frame responses, returns ``(text, usage_dict)``.

    successful_frames: list of (frame_name, response_text) tuples.
    """
    consensus_block = "\n\n".join(
        f"### Advisor {i+1} — {frame}\n{resp}"
        for i, (frame, resp) in enumerate(successful_frames)
    )
    user = (
        f"Original question:\n{question}\n\n"
        f"The following analyses converge on a consensus. "
        f"Your job: assume they are ALL wrong and build the strongest, most coherent counter-argument possible. "
        f"Steel-man the dissent, never straw-man.\n\n"
        f"{consensus_block}"
    )
    return await _call_anthropic(client, OPUS, PROMPTS[TENTH_MAN], user, TENTH_MAX_TOKENS, temperature)


async def run_agents(client, question, context=None, temperature=TEMPERATURE):
    """Run all 9 frames in parallel, then tenth-man.

    Returns: list of (frame_name, response_text, status, usage_dict) tuples, length 10.
    status is "ok" or "failed". On "failed", usage_dict is None.

    Raises RuntimeError if fewer than 8/9 frames succeeded — without enough
    cognitive coverage, the dissenter has no real consensus to attack.
    """
    tasks = [run_agent(client, frame, question, context, temperature) for frame in FRAMES]
    raw = await asyncio.gather(*tasks, return_exceptions=True)

    nine = []
    for frame, res in zip(FRAMES, raw):
        if isinstance(res, BaseException):
            nine.append((frame, f"[failed: {type(res).__name__}: {res}]", "failed", None))
        else:
            text, usage = res
            nine.append((frame, text, "ok", usage))

    n_ok = sum(1 for _, _, s, _ in nine if s == "ok")
    if n_ok < 8:
        failed_frames = [f for f, _, s, _ in nine if s == "failed"]
        raise RuntimeError(
            f"Only {n_ok}/9 advisors succeeded. Aborting (minimum required: 8). "
            f"Failed advisors: {failed_frames}"
        )

    successful = [(f, r) for f, r, s, _ in nine if s == "ok"]
    tenth_text, tenth_usage = await run_tenth_man(client, successful, question, temperature)

    return nine + [(TENTH_MAN, tenth_text, "ok", tenth_usage)]
