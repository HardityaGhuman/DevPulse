"""
Digest generation — model-agnostic via LiteLLM.

A single `_MODELS` list is tried in order (primary first, fallback after). Swapping models
or providers is a one-line change with no other code impact. The prompt follows the PTCF
framework (Persona, Task, Context, Format); output is validated against `DigestResult`, and
a model that errors OR returns unparseable/invalid JSON falls through to the next model.
"""

import json
import logging
import litellm
from app.schemas import DigestContext, DigestResult

logger = logging.getLogger("devpulse.ai")

# Ordered: primary first, fallback(s) after. Any LiteLLM-supported model id works.
_MODELS = ["gemini/gemini-2.5-flash", "groq/openai/gpt-oss-120b"]  

# ── PTCF prompt ────────────────────────────────────────────────
_PERSONA = ("You are a senior developer coach reviewing a peer's week of GitHub activity. "
            "You are specific, encouraging, and never generic.")
_TASK = ("Write ONE short, specific sentence summarizing the developer's period — reference "
         "real numbers or a repo where notable. Then judge overall momentum. No advice, no "
         "lists, no filler.")
_FORMAT = ('Return ONLY valid JSON matching exactly: '
           '{"headline": string (one sentence, <= 140 chars), '
           '"momentum": "rising"|"steady"|"declining"}. No prose, no markdown.')


def _build_prompt(ctx: DigestContext) -> str:
    context_json = json.dumps(ctx.model_dump(), indent=2, default=str)
    return (f"# Persona\n{_PERSONA}\n\n# Task\n{_TASK}\n\n"
            f"# Context\n```json\n{context_json}\n```\n\n# Format\n{_FORMAT}\n")


def _parse(text: str) -> DigestResult:
    """Strict parse -> validate. Strips markdown fences if a model adds them."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```", 2)[1].removeprefix("json").strip()
    return DigestResult.model_validate_json(cleaned)


async def _complete(model: str, prompt: str) -> str:
    """Single LiteLLM call in JSON mode. Returns the raw content string."""
    resp = await litellm.acompletion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
    )
    return resp["choices"][0]["message"]["content"]


async def generate_digest(context: DigestContext) -> DigestResult:
    """Try each model in _MODELS. Raise only if all fail (no half-baked digest)."""
    prompt = _build_prompt(context)
    for model in _MODELS:
        try:
            raw = await _complete(model, prompt)
            return _parse(raw)
        except Exception as e:  # model error OR parse/validation failure -> next model
            logger.warning("[ai] model %s failed: %s", model, e)
    raise RuntimeError("All LLM models failed to produce a valid digest")
