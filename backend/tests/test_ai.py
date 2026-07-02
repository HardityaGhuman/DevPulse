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
    assert calls == ai._MODELS  # tried primary then fallback


@pytest.mark.asyncio
async def test_invalid_primary_output_triggers_fallback(monkeypatch):
    async def fake_complete(model, prompt):
        return "not json" if model == ai._MODELS[0] else VALID_JSON

    monkeypatch.setattr(ai, "_complete", fake_complete)
    result = await ai.generate_digest(CTX)
    assert result.headline.startswith("Steady day")


@pytest.mark.asyncio
async def test_raises_when_all_models_fail(monkeypatch):
    async def fake_complete(model, prompt):
        raise RuntimeError("down")

    monkeypatch.setattr(ai, "_complete", fake_complete)
    with pytest.raises(RuntimeError):
        await ai.generate_digest(CTX)
