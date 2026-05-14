"""
Apify Actor entrypoint.

Run locally:

    apify run

Or:

    python -m src.main

Input is read from ``INPUT.json`` (Apify default key-value store) when using the
CLI; on the platform it is injected automatically.
"""

from __future__ import annotations

import asyncio

from apify import Actor

from src.exceptions import FuelPriceError, UnsupportedCountryError
from src.services.fuel_service import resolve_fuel_averages


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        country = str(actor_input.get("country", "uk")).strip()
        Actor.log.info(
            "Actor started for country=%r (matching is case-insensitive).",
            country,
        )

        try:
            record = await resolve_fuel_averages(country)
        except UnsupportedCountryError as e:
            Actor.log.error(str(e))
            err = {
                "error": "unsupported_country",
                "message": str(e),
                "country": country,
            }
            await Actor.push_data(err)
            await Actor.set_value("OUTPUT", err)
            raise
        except FuelPriceError as e:
            Actor.log.error(str(e))
            err = {
                "error": "upstream_failed",
                "message": str(e),
                "country": country,
            }
            await Actor.push_data(err)
            await Actor.set_value("OUTPUT", err)
            raise

        payload = record.to_push_dict()
        await Actor.push_data(payload)
        await Actor.set_value("OUTPUT", payload)
        Actor.log.info(
            "Pushed result: country=%s petrol=%.3f diesel=%.3f %s per %s lastUpdate=%s",
            record.country,
            record.petrol,
            record.diesel,
            record.currency,
            record.volumeUnit,
            record.lastUpdate,
        )


if __name__ == "__main__":
    asyncio.run(main())
