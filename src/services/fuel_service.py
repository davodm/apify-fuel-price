"""Service layer: country routing, cache, upstream fallback chain."""

from __future__ import annotations

import traceback
from datetime import datetime, timezone

from apify import Actor

from src.config import COUNTRY_OUTPUT_PRICING, SUPPORTED_COUNTRIES
from src.datetime_util import to_iso_utc
from src.exceptions import FuelPriceError, UnsupportedCountryError
from src.fetchers.uk_petrolprices_com import fetch_uk_from_gviz_fallback
from src.fetchers.uk_petrolprices_co_uk import fetch_uk_live
from src.http_util import build_async_client
from src.models import ActorOutputRecord, ParsedFuelPrices
from src import cache as cache_layer


def _parsed_to_output_record(
    country: str, parsed: ParsedFuelPrices, last_update: str
) -> ActorOutputRecord:
    """Map parsed upstream numbers to a row: major ``currency`` per ``volumeUnit`` only."""
    pricing = COUNTRY_OUTPUT_PRICING[country]
    if country == "uk":
        # Public UK sources quote pence per litre; row uses ISO GBP (pounds) per litre.
        petrol = round(parsed.petrol_ppl / 100, 3)
        diesel = round(parsed.diesel_ppl / 100, 3)
    else:
        raise NotImplementedError(f"No output mapping for country {country!r}")

    return ActorOutputRecord(
        country=country,
        petrol=petrol,
        diesel=diesel,
        lastUpdate=last_update,
        currency=pricing["currency"],
        volumeUnit=pricing["volumeUnit"],
    )


async def resolve_fuel_averages(country: str) -> ActorOutputRecord:
    """
    End-to-end resolution for one run: cache hit, else fetch with fallback.

    Raises:
        UnsupportedCountryError: if ``country`` is not implemented.
        FuelPriceError: if all upstream strategies fail.
    """
    # Case-insensitive (e.g. UK, uk, Uk) — output always uses lowercase codes.
    normalized = country.strip().lower()
    if normalized not in SUPPORTED_COUNTRIES:
        raise UnsupportedCountryError(
            f"Country {country!r} is not supported yet. "
            f"This Actor will grow to more countries; currently supported (case-insensitive): "
            f"{', '.join(sorted(SUPPORTED_COUNTRIES))}"
        )

    hit = await cache_layer.try_get_fresh_cached_record(normalized)
    if hit is not None:
        Actor.log.info("Returning cached fuel averages for %r.", normalized)
        return hit

    parsed = await _fetch_with_fallback()
    now = datetime.now(timezone.utc)
    fetched_iso = to_iso_utc(now)
    last_update = parsed.last_update_raw or fetched_iso

    record = _parsed_to_output_record(normalized, parsed, last_update)
    await cache_layer.write_cache_record(normalized, record, fetched_iso)
    return record


async def _fetch_with_fallback() -> ParsedFuelPrices:
    """
    Try the lightweight HTML source first, then the public gviz endpoints.

    Logs each failure with stack traces at debug level for Apify support.
    """
    async with build_async_client() as client:
        try:
            Actor.log.info("Fetching UK averages from primary HTML source.")
            return await fetch_uk_live(client)
        except Exception as primary_exc:
            Actor.log.warning(
                "Primary UK source failed (%s). Falling back to gviz sheet endpoints.",
                primary_exc,
            )
            Actor.log.debug("Primary traceback:\n%s", traceback.format_exc())
            try:
                Actor.log.info("Fetching UK averages from gviz fallback.")
                return await fetch_uk_from_gviz_fallback(client)
            except Exception as fallback_exc:
                Actor.log.error(
                    "Fallback UK source failed (%s). No averages available.",
                    fallback_exc,
                )
                Actor.log.debug("Fallback traceback:\n%s", traceback.format_exc())
                raise FuelPriceError(
                    "Could not obtain UK fuel averages from primary or fallback sources."
                ) from fallback_exc
