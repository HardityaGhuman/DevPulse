"""
DevPulse — Gemini AI Service
Handles all interactions with Google Gemini API for code review,
PR review, and digest generation.
"""

import json
import re
import google.generativeai as genai
from app.config import settings

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# ── Prompt Templates ────────────────────────────────────────────

CODE_REVIEW_PROMPT = """
You are an expert code reviewer. Analyze the following {language} code and return a structured JSON review.

Code:
{code}

Return ONLY valid JSON:
{{
  "summary": "2-3 sentence overall assessment",
  "score": <integer 1-10>,
  "bugs": [{{"line": <int|null>, "severity": "critical|high|medium|low", "description": "..."}}],
  "security": [{{"issue": "...", "severity": "critical|high|medium|low", "recommendation": "..."}}],
  "suggestions": [{{"category": "performance|readability|maintainability|best-practice", "description": "...", "improved_snippet": "..."}}],
  "positive": ["..."],
  "complexity": {{"rating": "low|medium|high", "explanation": "..."}}
}}
"""

PR_REVIEW_PROMPT = """
You are an expert code reviewer. Analyze the following pull request diff and return a structured JSON review.

PR Title: {title}
PR Description: {description}
Diff:
{diff}

Return ONLY valid JSON:
{{
  "summary": "2-3 sentence overall assessment",
  "score": <integer 1-10>,
  "risk_level": "low|medium|high",
  "files_reviewed": [{{"filename": "...", "verdict": "approve|request-changes|comment", "comments": ["..."]}}],
  "bugs": [{{"description": "...", "severity": "critical|high|medium|low"}}],
  "suggestions": [{{"description": "...", "category": "..."}}],
  "positive": ["..."],
  "merge_recommendation": "approve|request-changes|needs-discussion"
}}
"""

DIGEST_PROMPT = """
You are a developer coach. Based on the following GitHub activity, write a personalized digest.

Developer: {github_username}
Period: {period_start} to {period_end}
Activity: {activity_json}

Return ONLY valid JSON:
{{
  "headline": "one punchy sentence summarizing the period",
  "highlights": ["3-5 notable things they did"],
  "streak_comment": "...",
  "top_repo": "...",
  "coaching_tip": "one actionable improvement tip",
  "momentum": "rising|steady|declining"
}}
"""


def _parse_json_response(text: str) -> dict:
    """Parse JSON from Gemini response, stripping markdown fences if present."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response as JSON: {e}")


async def review_code(code: str, language: str) -> dict:
    """
    Send code to Gemini for review and return structured JSON result.
    """
    prompt = CODE_REVIEW_PROMPT.format(language=language, code=code)

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    return _parse_json_response(response.text)


async def review_pr(title: str, description: str, diff: str) -> dict:
    """
    Send PR diff to Gemini for review and return structured JSON result.
    """
    # Truncate diff if too large (Gemini context limit)
    max_diff_chars = 100_000
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n\n... [diff truncated due to size]"

    prompt = PR_REVIEW_PROMPT.format(
        title=title,
        description=description or "No description provided",
        diff=diff,
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    return _parse_json_response(response.text)


async def generate_digest(
    github_username: str,
    period_start: str,
    period_end: str,
    activity_json: str,
) -> dict:
    """
    Generate a personalized developer digest using Gemini.
    """
    prompt = DIGEST_PROMPT.format(
        github_username=github_username,
        period_start=period_start,
        period_end=period_end,
        activity_json=activity_json,
    )

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.5,
        ),
    )

    return _parse_json_response(response.text)
