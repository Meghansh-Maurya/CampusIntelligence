
from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MAX_ATTEMPTS = 4
EMBEDDING_INITIAL_RETRY_DELAY = 2.0
EMBEDDING_MAX_RETRY_DELAY = 60.0


def ai_is_configured() -> bool:
    return bool(settings.gemini_key_value)


def _client():
    try:
        from google import genai
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Install backend dependencies from requirements.txt to enable Gemini integration.",
        ) from exc

    api_key = settings.gemini_key_value
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="This feature requires GEMINI_API_KEY. Add it to the backend .env file and restart the server.",
        )

    return genai.Client(api_key=api_key)


def _extract_json_payload(raw_text: str) -> dict[str, Any] | list[Any]:
    """Parse a complete JSON object/list, tolerating Markdown fences and surrounding prose."""
    text = raw_text.strip()

    if not text:
        raise ValueError("The model returned an empty response.")

    fence_match = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if fence_match:
        text = fence_match.group(1).strip()

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        starts = [
            position
            for position in (text.find("{"), text.find("["))
            if position >= 0
        ]

        if not starts:
            raise

        start = min(starts)
        value, _ = json.JSONDecoder().raw_decode(text[start:])

    if not isinstance(value, (dict, list)):
        raise ValueError("Expected a JSON object or list.")

    return value


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
) -> str:
    client = _client()

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )

        text = response.text

        if not text:
            raise ValueError("The model returned an empty text response.")

        return text.strip()

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Gemini text generation failed")

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI provider could not complete the request. "
                "Check server logs and model/API configuration."
            ),
        ) from exc


def generate_json(
    prompt: str,
    system_instruction: str | None = None,
) -> dict[str, Any] | list[Any]:
    """Generate JSON and fail clearly if Gemini returns truncated or malformed output."""
    client = _client()

    try:
        from google.genai import types

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=8192,
            ),
        )

        parsed = getattr(response, "parsed", None)

        if parsed is not None:
            if hasattr(parsed, "model_dump"):
                parsed = parsed.model_dump()

            if isinstance(parsed, (dict, list)):
                return parsed

        raw_text = response.text or ""

        try:
            return _extract_json_payload(raw_text)

        except (json.JSONDecodeError, ValueError) as parse_error:
            finish_reason = None

            try:
                finish_reason = response.candidates[0].finish_reason
            except (AttributeError, IndexError, TypeError):
                pass

            logger.error(
                "Gemini returned invalid JSON (finish_reason=%s, response_chars=%s).",
                finish_reason,
                len(raw_text),
            )

            raise ValueError(
                "Gemini returned incomplete or malformed JSON. "
                "The response could not be safely parsed."
            ) from parse_error

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Gemini JSON generation failed")

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI provider returned an incomplete or unusable response. "
                "Retry once; if it persists, check the configured Gemini model "
                "and server logs."
            ),
        ) from exc


def _is_retryable_embedding_error(exc: Exception) -> bool:
    """Identify rate-limit and temporary server errors."""
    message = str(exc).lower()

    retryable_indicators = (
        "429",
        "resource_exhausted",
        "rate limit",
        "too many requests",
        "500",
        "502",
        "503",
        "504",
        "internal server error",
        "service unavailable",
        "deadline exceeded",
        "temporarily unavailable",
    )

    return any(indicator in message for indicator in retryable_indicators)


def _get_embedding_retry_delay(
    exc: Exception,
    attempt: int,
) -> float:
    """Extract a provider retry delay when available; otherwise use backoff."""
    message = str(exc)

    # Examples:
    # retry_delay { seconds: 6 }
    # retry in 6s
    # retryDelay: "6s"
    patterns = (
        r"seconds\s*:\s*(\d+(?:\.\d+)?)",
        r"retry\s+in\s+(\d+(?:\.\d+)?)\s*s",
        r"retryDelay[\"']?\s*:\s*[\"'](\d+(?:\.\d+)?)s",
    )

    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)

        if match:
            provider_delay = float(match.group(1))
            return min(
                max(provider_delay, 0.5),
                EMBEDDING_MAX_RETRY_DELAY,
            )

    # Exponential fallback: 2, 4, 8 seconds.
    fallback_delay = EMBEDDING_INITIAL_RETRY_DELAY * (2 ** (attempt - 1))

    return min(
        fallback_delay + random.uniform(0.1, 0.5),
        EMBEDDING_MAX_RETRY_DELAY,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate one embedding vector per input text.

    Retries temporary provider errors, including Gemini 429 rate limits.
    Raises RuntimeError after exhausting retries so callers can fall back
    to lexical retrieval.
    """
    if not texts:
        return []

    client = _client()

    try:
        from google.genai import types

        # Each Content represents one independent input chunk.
        contents = [
            types.Content(
                parts=[types.Part.from_text(text=text)]
            )
            for text in texts
        ]

        for attempt in range(1, EMBEDDING_MAX_ATTEMPTS + 1):
            try:
                response = client.models.embed_content(
                    model=settings.gemini_embedding_model,
                    contents=contents,
                    config=types.EmbedContentConfig(
                        output_dimensionality=settings.gemini_embedding_dimensions
                    ),
                )

                items = getattr(response, "embeddings", None) or []

                vectors: list[list[float]] = []

                for item in items:
                    values = getattr(item, "values", None)

                    if values is None and isinstance(item, dict):
                        values = item.get("values")

                    if values is None:
                        raise ValueError(
                            "The embedding provider returned a result "
                            "without vector values."
                        )

                    vectors.append(
                        [float(value) for value in values]
                    )

                if len(vectors) != len(texts):
                    raise ValueError(
                        f"Embedding response count mismatch: received "
                        f"{len(vectors)} vectors for {len(texts)} input chunks."
                    )

                return vectors

            except Exception as exc:
                if (
                    attempt >= EMBEDDING_MAX_ATTEMPTS
                    or not _is_retryable_embedding_error(exc)
                ):
                    raise

                delay = _get_embedding_retry_delay(exc, attempt)

                logger.warning(
                    "Gemini embedding request failed "
                    "(attempt %s/%s). Retrying in %.2f seconds. Error: %s",
                    attempt,
                    EMBEDDING_MAX_ATTEMPTS,
                    delay,
                    exc,
                )

                time.sleep(delay)

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Gemini embedding generation failed after retries "
            "(input_texts=%s).",
            len(texts),
        )

        raise RuntimeError(
            f"Embedding generation failed for {len(texts)} texts."
        ) from exc

    raise RuntimeError("Embedding generation failed.")
