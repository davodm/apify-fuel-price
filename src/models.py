"""Domain models and typed structures for API responses and cache records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedFuelPrices:
    """Normalized fuel averages from any upstream parser."""

    petrol_ppl: float
    diesel_ppl: float
    last_update_raw: str | None
    source_url: str


@dataclass(frozen=True)
class ActorOutputRecord:
    """
    One dataset item pushed by the Actor (default dataset).

    ``petrol`` and ``diesel`` are expressed in ``amountUnit`` per ``volumeUnit``
    in ``currency`` (e.g. UK: pence per litre in GBP).

    Cache storage may add ``fetchedAt`` for TTL only (see ``src/cache.py``).
    """

    country: str
    petrol: float
    diesel: float
    lastUpdate: str
    currency: str
    amountUnit: str
    volumeUnit: str

    def to_push_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for ``Actor.push_data``."""
        return {
            "country": self.country,
            "petrol": self.petrol,
            "diesel": self.diesel,
            "currency": self.currency,
            "amountUnit": self.amountUnit,
            "volumeUnit": self.volumeUnit,
            "lastUpdate": self.lastUpdate,
        }
