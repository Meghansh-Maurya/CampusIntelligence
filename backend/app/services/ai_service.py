from __future__ import annotations
import json, logging, random, re, time
from typing import Any
from fastapi import HTTPException
from app.core.config import settings
logger = logging.getLogger(__name__)
MAX_ATTEMPTS, INITIAL_DELAY, MAX_DELAY = 3, 2.0, 20.0

def ai_is_configured() -> bool:
    return bool(settings.gemini_key_value)

_CLIENT = None

def _client():
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        from google import genai
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Install backend requirements.txt to enable Gemini.") from exc
    if not settings.gemini_key_value:
        raise HTTPException(status_code=503, detail="Configure GEMINI_API_KEY in backend .env.")
    _CLIENT = genai.Client(api_key=settings.gemini_key_value)
    logger.info("Gemini client created: key ending ...%s, model %s, fallback %s", settings.gemini_key_value[-4:], settings.gemini_model, settings.gemini_fallback_model)
    return _CLIENT

def _extract_json_payload(raw_text: str) -> dict[str, Any] | list[Any]:
    text = raw_text.strip()
    if not text: raise ValueError("The model returned an empty response.")
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.I | re.S)
    if match: text = match.group(1).strip()
    try: value = json.loads(text)
    except json.JSONDecodeError:
        starts = [p for p in (text.find("{"), text.find("[")) if p >= 0]
        if not starts: raise
        value, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    if not isinstance(value, (dict, list)): raise ValueError("Expected a JSON object or list.")
    return value

def _models_to_try() -> list[str]:
    models = [settings.gemini_model]
    fallback = (settings.gemini_fallback_model or "").strip()
    if fallback and fallback != settings.gemini_model:
        models.append(fallback)
    return models


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


def _quota_http_error(exc: Exception | None) -> HTTPException:
    hint = ""
    match = re.search(r"retry in ([0-9hms.]+)", str(exc or ""), flags=re.I)
    if match:
        hint = f" Google says to retry in about {match.group(1).rstrip('.')}."
    return HTTPException(
        status_code=429,
        detail=(
            "The Gemini quota for this API key's project is used up (free-tier limits are per Google Cloud "
            "project and per model, so another key from the same project will not help)." + hint +
            " Options: wait for the reset, enable billing on the project, or set GEMINI_MODEL / "
            "GEMINI_FALLBACK_MODEL in backend/.env to a model that still has quota, then restart the backend."
        ),
    )


def _overloaded_http_error() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "The Gemini model is overloaded right now (Google returned 'high demand'). It was retried automatically. "
            "Please try again in a minute, or set GEMINI_FALLBACK_MODEL in backend/.env to use a second model when this happens."
        ),
    )


def _generate(prompt: str, **config_kwargs):
    """Call generate_content with retries for transient errors (503/500/per-minute 429),
    then try the fallback model. Daily-quota errors skip straight to the next model."""
    from google.genai import types
    client = _client()
    last_exc: Exception | None = None
    last_was_quota = False
    for model in _models_to_try():
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(**config_kwargs))
            except Exception as exc:
                last_exc, last_was_quota = exc, _is_quota_error(exc)
                if not _retryable(exc):
                    if last_was_quota:
                        logger.warning("Gemini quota exhausted for model %s: %s", model, str(exc)[:300])
                        break  # try the next model
                    raise
                if attempt == MAX_ATTEMPTS:
                    logger.warning("Gemini model %s still failing after %s attempts: %s", model, attempt, str(exc)[:200])
                    break  # try the next model
                delay = _delay(exc, attempt)
                logger.warning("Gemini model %s failed (attempt %s/%s); retrying in %.1fs: %s", model, attempt, MAX_ATTEMPTS, delay, str(exc)[:200])
                time.sleep(delay)
    raise _quota_http_error(last_exc) if last_was_quota else _overloaded_http_error()


def generate_text(prompt: str, system_instruction: str | None = None) -> str:
    try:
        response = _generate(prompt, system_instruction=system_instruction, temperature=.2, max_output_tokens=4096)
        if not response.text: raise ValueError("Empty model response.")
        return response.text.strip()
    except HTTPException: raise
    except Exception as exc:
        logger.exception("Gemini text generation failed")
        raise HTTPException(status_code=502, detail="The AI provider could not complete the request. Check server logs.") from exc

def generate_json(prompt: str, system_instruction: str | None = None) -> dict[str, Any] | list[Any]:
    try:
        response = _generate(prompt, system_instruction=system_instruction, response_mime_type="application/json", temperature=.1, max_output_tokens=8192)
        parsed = getattr(response, "parsed", None)
        if hasattr(parsed, "model_dump"): parsed = parsed.model_dump()
        if isinstance(parsed, (dict, list)): return parsed
        return _extract_json_payload(response.text or "")
    except HTTPException: raise
    except Exception as exc:
        logger.exception("Gemini JSON generation failed")
        raise HTTPException(status_code=502, detail="Gemini returned an unusable response. Check the configured model and logs.") from exc

def _retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    if "perday" in msg or "per day" in msg:
        return False  # a daily quota will not recover within a retry window
    return any(x in msg for x in ("429","resource_exhausted","rate limit","too many requests","500","502","503","504","internal server error","service unavailable","deadline exceeded","temporarily unavailable"))

def _delay(exc: Exception, attempt: int) -> float:
    msg = str(exc)
    for pattern in (r"seconds\s*:\s*(\d+(?:\.\d+)?)", r"retry\s+in\s+(\d+(?:\.\d+)?)\s*s", r"retryDelay[\"']?\s*:\s*[\"'](\d+(?:\.\d+)?)s"):
        m = re.search(pattern, msg, flags=re.I)
        if m: return min(max(float(m.group(1)), .5), MAX_DELAY)
    return min(INITIAL_DELAY * (2 ** (attempt - 1)) + random.uniform(.1, .5), MAX_DELAY)

def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    if not texts: return []
    client = _client()
    try:
        from google.genai import types
        contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = client.models.embed_content(model=settings.gemini_embedding_model, contents=contents, config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=settings.gemini_embedding_dimensions))
                items = getattr(response, "embeddings", None) or []
                vectors = []
                for item in items:
                    vals = getattr(item, "values", None)
                    if vals is None and isinstance(item, dict): vals = item.get("values")
                    if vals is None: raise ValueError("Embedding response omitted vector values.")
                    vectors.append([float(v) for v in vals])
                if len(vectors) != len(texts): raise ValueError(f"Expected {len(texts)} vectors, got {len(vectors)}.")
                return vectors
            except Exception as exc:
                if attempt == MAX_ATTEMPTS or not _retryable(exc): raise
                delay = _delay(exc, attempt)
                logger.warning("Embedding request failed (attempt %s/%s); retrying in %.2fs: %s", attempt, MAX_ATTEMPTS, delay, exc)
                time.sleep(delay)
    except HTTPException: raise
    except Exception as exc:
        logger.exception("Gemini embedding failed for %s inputs.", len(texts))
        raise RuntimeError(f"Embedding generation failed for {len(texts)} texts.") from exc
    raise RuntimeError("Embedding generation failed.")
