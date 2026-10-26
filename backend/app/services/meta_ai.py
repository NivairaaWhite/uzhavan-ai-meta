"""
Single gateway for every Meta Model API call. Budget cap, timeouts and
fallbacks live in one place. Uses the synchronous OpenAI client because
routes and Celery tasks are synchronous.
"""
import base64
import logging
from datetime import date
from typing import Optional, Type, TypeVar

from pydantic import BaseModel
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()
T = TypeVar("T", bound=BaseModel)

_client = None


class MetaAIUnavailable(RuntimeError):
    pass


def get_redis_connection():
    try:
        import redis
        return redis.Redis.from_url(settings.REDIS_URL)
    except Exception as exc:
        log.warning("Redis connection failed, continuing without distributed rate limiter: %s", exc)
        return None


def client():
    global _client
    if not settings.META_AI_ENABLED or not settings.MODEL_API_KEY:
        raise MetaAIUnavailable("Meta AI is disabled or MODEL_API_KEY is missing")
    if _client is None:
        try:
            from openai import OpenAI
            _client = OpenAI(
                api_key=settings.MODEL_API_KEY,
                base_url=settings.META_API_BASE,
                timeout=settings.META_TIMEOUT_S,
                max_retries=1,
            )
        except ImportError:
            raise MetaAIUnavailable("openai package is not installed")
    return _client


def budget_guard() -> None:
    r = get_redis_connection()
    if r is not None:
        try:
            key = f"meta_calls:{date.today().isoformat()}"
            n = r.incr(key)
            r.expire(key, 172800)
            if n > settings.META_DAILY_CALL_CAP:
                raise MetaAIUnavailable("daily call cap reached")
        except MetaAIUnavailable:
            raise
        except Exception as exc:
            log.warning("Could not increment daily call cap counter in Redis: %s", exc)


def ask_text(system: str, user: str, model: Optional[str] = None) -> str:
    c = client()
    budget_guard()
    r = c.chat.completions.create(
        model=model or settings.META_MODEL_FAST,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    log.info("meta_ai model=%s usage=%s", r.model, getattr(r, "usage", None))
    return r.choices[0].message.content or ""


def ask_json(schema: Type[T], system: str, user_content, model: Optional[str] = None) -> T:
    """user_content is a string, or a list of parts when you send an image."""
    c = client()
    budget_guard()
    last_err = None
    for _ in range(2):  # one retry on malformed JSON
        r = c.chat.completions.create(
            model=model or settings.META_MODEL_FAST,
            messages=[
                {"role": "system", "content": system + " Reply with JSON only."},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            },
        )
        log.info("meta_ai model=%s usage=%s", r.model, getattr(r, "usage", None))
        text = (r.choices[0].message.content or "").strip().strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
        try:
            return schema.model_validate_json(text)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    raise MetaAIUnavailable(f"model returned invalid JSON: {last_err}")


def segment(jpeg_bytes: bytes, concept: str):
    """SAM 3.1 segmentation. One noun phrase per call."""
    c = client()
    budget_guard()
    data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode()
    r = c.responses.create(
        model=settings.META_MODEL_SAM,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": data_url},
                    {"type": "input_text", "text": concept},
                ],
            }
        ],
    )
    return getattr(r, "output_text", str(r))
