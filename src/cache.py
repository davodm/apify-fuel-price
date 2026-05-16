"""
Key-value store cache for per-country fuel averages.

Uses a **named** key-value store so entries can be reused across Actor runs
(unlike the default per-run store). TTL is enforced in code (1 hour).

Each stored record includes ``fetchedAt`` (ISO UTC) for TTL only; that key is
not part of the default dataset payload (see ``ActorOutputRecord``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apify import Actor

from src.config import (
    CACHE_KEY_PREFIX,
    CACHE_KV_STORE_NAME,
    CACHE_TTL_SECONDS,
    COUNTRY_OUTPUT_PRICING,
)
from src.models import ActorOutputRecord

# KV-only: used for age check; not returned from ``to_push_dict``.
_CACHE_FETCHED_AT_KEY = "fetchedAt"


def _cache_record_key(country: str) -> str:
    """Stable KV key for a country (no extension required)."""
    return f"{CACHE_KEY_PREFIX}_{country.lower()}"


def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO timestamps produced by this Actor (``...Z`` or offset)."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def try_get_fresh_cached_record(country: str) -> ActorOutputRecord | None:
    """Return a dataset-ready record if a non-expired cache entry exists."""
    kvs = await Actor.open_key_value_store(name=CACHE_KV_STORE_NAME)
    key = _cache_record_key(country)
    stored: Any = await kvs.get_value(key)
    if not stored or not isinstance(stored, dict):
        return None
    fetched_raw = stored.get(_CACHE_FETCHED_AT_KEY)
    if not isinstance(fetched_raw, str):
        return None
    try:
        fetched_at = _parse_iso_datetime(fetched_raw)
    except ValueError:
        Actor.log.warning("Cache entry %r has invalid fetchedAt; ignoring.", key)
        return None
    age_seconds = (datetime.now(timezone.utc) - fetched_at.astimezone(timezone.utc)).total_seconds()
    if age_seconds > CACHE_TTL_SECONDS:
        Actor.log.info(
            "Cache miss for %r (stale by %.0fs > ttl=%ss).",
            key,
            age_seconds,
            CACHE_TTL_SECONDS,
        )
        return None

    try:
        pricing = COUNTRY_OUTPUT_PRICING.get(country, {})
        return ActorOutputRecord(
            country=str(stored["country"]),
            petrol=float(stored["petrol"]),
            diesel=float(stored["diesel"]),
            lastUpdate=str(stored["lastUpdate"]),
            currency=str(stored.get("currency", pricing.get("currency", ""))),
            volumeUnit=str(stored.get("volumeUnit", pricing.get("volumeUnit", ""))),
        )
    except (KeyError, TypeError, ValueError) as e:
        Actor.log.warning("Malformed cache payload for %r: %s", key, e)
        return None


async def write_cache_record(country: str, record: ActorOutputRecord, fetched_at_iso: str) -> None:
    """Persist dataset fields plus ``fetchedAt`` for TTL under the country key."""
    kvs = await Actor.open_key_value_store(name=CACHE_KV_STORE_NAME)
    key = _cache_record_key(country)
    payload = {**record.to_push_dict(), _CACHE_FETCHED_AT_KEY: fetched_at_iso}
    await kvs.set_value(key, payload, content_type="application/json")
    Actor.log.info("Wrote cache key %r (fetchedAt=%s).", key, fetched_at_iso)
