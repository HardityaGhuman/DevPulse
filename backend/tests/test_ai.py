import pytest
from app.schemas import DigestContext, DigestResult
from app.services import ai

CTX = DigestContext(github_username="me", period_start="2026-06-24", period_end="2026-07-01",
                    commits=10, prs_opened=2, prs_merged=1, issues_opened=0, reviews=3,
                    repos_active=["me/app"], streak_days=5)

VALID_JSON = '{"headline":"Steady day — 2 commits on aria.","momentum":"rising"}'


@pytest.mark.asyncio
async def test_falls_back_to_next_model_when_primary_fails(monkeypatch):
    calls = []

    async def fake_complete(model, prompt):
        calls.append(model)
        if model == ai._MODELS[0]:
            raise RuntimeError("primary down")
        return VALID_JSON

    monkeypatch.setattr(ai, "_complete", fake_complete)
    result = await ai.generate_digest(CTX)
    assert isinstance(result, DigestResult)
    assert result.momentum == "rising"
    # stops at the first model that succeeds: primary failed, second returned valid JSON
    assert calls == ai._MODELS[:2]


@pytest.mark.asyncio
async def test_invalid_primary_output_triggers_fallback(monkeypatch):
    async def fake_complete(model, prompt):
        return "not json" if model == ai._MODELS[0] else VALID_JSON

    monkeypatch.setattr(ai, "_complete", fake_complete)
    result = await ai.generate_digest(CTX)
    assert result.headline.startswith("Steady day")


@pytest.mark.asyncio
async def test_falls_back_to_facts_when_all_models_fail(monkeypatch):
    """LLM outage must never mean a silent no-send — a deterministic facts-only digest
    is produced from the context counts instead."""
    async def fake_complete(model, prompt):
        raise RuntimeError("down")

    monkeypatch.setattr(ai, "_complete", fake_complete)
    result = await ai.generate_digest(CTX)
    assert isinstance(result, DigestResult)
    # Facts assembled from CTX (10 commits, 1 merged, 2 opened, 3 reviews, 1 repo).
    assert "10 commits" in result.headline
    assert "1 PR merged" in result.headline
    assert result.momentum in ("rising", "steady", "declining")


@pytest.mark.asyncio
async def test_fallback_headline_when_no_activity():
    quiet = DigestContext(github_username="me", period_start="2026-06-24",
                          period_end="2026-07-01", commits=0, prs_opened=0, prs_merged=0,
                          issues_opened=0, reviews=0, repos_active=[], streak_days=0)
    result = ai._fallback_result(quiet)
    assert result.headline == "A quiet period — no tracked activity."
    assert result.momentum == "steady"
