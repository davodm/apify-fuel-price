"""
Central configuration for URLs, timeouts, cache, and fallback data sources.

Keeping magic strings here makes the Actor easier to tune without hunting
through parsing logic.
"""

from __future__ import annotations

# --- HTTP ---
# Per-request ceiling (connect + read + write + pool) for upstream GETs.
DEFAULT_TIMEOUT_SECONDS = 10.0
USER_AGENT = (
    "FuelPriceActor/1.0 (+https://apify.com) "
    "httpx; respectful public data fetch for national fuel averages"
)

# --- Primary source (HTML): PetrolPrices.co.uk live UK page ---
UK_LIVE_PAGE_URL = "https://petrolprices.co.uk/uk-fuel-prices-live.php"

# --- Fallback: Google Sheet behind PetrolPrices.com (same underlying averages) ---
# These gids are embedded in the public page script at petrolprices.com.
UK_GVIZ_UNLEADED_AVERAGE_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1pUPeCiR0DFJtwC7r0RgMqE-2DW7GWsQAB0YgTS_TP7k"
    "/gviz/tq?tqx=out:json&gid=894617656"
)
UK_GVIZ_DIESEL_AVERAGE_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1pUPeCiR0DFJtwC7r0RgMqE-2DW7GWsQAB0YgTS_TP7k"
    "/gviz/tq?tqx=out:json&gid=1992653908"
)
UK_FALLBACK_HUMAN_PAGE = "https://www.petrolprices.com/latest-fuel-price-data-across-the-uk/"

# --- Cache (named key-value store, shared across Actor runs for the user) ---
CACHE_KV_STORE_NAME = "fuel-price-actor-cache"
CACHE_KEY_PREFIX = "fuel_avg"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# --- Supported countries (extend when adding fetchers) ---
SUPPORTED_COUNTRIES = frozenset({"uk"})

# Per-country output: ISO ``currency`` and ``volumeUnit`` for the row.
# ``petrol`` / ``diesel`` are always that currency's major unit per ``volumeUnit``
# (no separate amount unit in the API). Fetchers may read local conventions;
# the service layer normalizes before ``ActorOutputRecord`` (e.g. UK pence/L → GBP/L).
COUNTRY_OUTPUT_PRICING: dict[str, dict[str, str]] = {
    "uk": {
        "currency": "GBP",
        "volumeUnit": "litre",
    },
}
