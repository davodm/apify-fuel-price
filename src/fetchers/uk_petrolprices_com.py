"""
Fallback UK averages via the same public Google Sheet used on PetrolPrices.com.

The marketing page loads averages with ``google.visualization.Query``; we call
the documented ``gviz/tq`` JSON endpoint directly (no browser, no API key).

Human-readable page (for reference only): https://www.petrolprices.com/latest-fuel-price-data-across-the-uk/
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import TYPE_CHECKING

from src.config import UK_FALLBACK_HUMAN_PAGE, UK_GVIZ_DIESEL_AVERAGE_URL, UK_GVIZ_UNLEADED_AVERAGE_URL
from src.datetime_util import parse_uk_day_month_year, to_iso_utc
from src.exceptions import ParseError
from src.http_util import get_text
from src.models import ParsedFuelPrices

if TYPE_CHECKING:
    import httpx

_GVIZ_PREFIX = re.compile(
    r"^\s*(?:/\*.*?\*/\s*)?google\.visualization\.Query\.setResponse\(",
    re.DOTALL,
)


def _unwrap_gviz_json(body: str) -> dict:
    """Strip the JS wrapper and parse the inner JSON object."""
    body = body.strip()
    m = _GVIZ_PREFIX.search(body)
    if not m:
        raise ParseError("Unexpected gviz response wrapper.")
    inner = body[m.end() :].rstrip()
    if inner.endswith(");"):
        inner = inner[:-2].strip()
    elif inner.endswith(")"):
        inner = inner[:-1].strip()
    try:
        return json.loads(inner)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid gviz JSON: {e}") from e


def _last_row_values(table: dict) -> list[dict | None]:
    rows = table.get("rows") or []
    if not rows:
        raise ParseError("gviz table has no rows.")
    last = rows[-1]
    cells = last.get("c") or []
    return list(cells)


def _cell_number(cell: dict | None) -> float | None:
    if not cell or "v" not in cell:
        return None
    v = cell["v"]
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def _cell_string(cell: dict | None) -> str | None:
    if not cell:
        return None
    v = cell.get("v")
    if isinstance(v, str) and v.strip():
        return v.strip()
    f = cell.get("f")
    if isinstance(f, str) and f.strip():
        return f.strip()
    return None


def parse_gviz_average(body: str) -> tuple[float, str | None]:
    """
    Parse one gviz JSON response: returns (price_pence, iso_last_update_or_none).

    Column layout from the sheet: A = average ppl, C = human date string.
    """
    payload = _unwrap_gviz_json(body)
    if payload.get("status") != "ok":
        raise ParseError(f"gviz status not ok: {payload.get('status')!r}")
    table = payload.get("table") or {}
    cells = _last_row_values(table)
    price = _cell_number(cells[0] if cells else None)
    if price is None:
        raise ParseError("gviz row missing numeric price.")
    date_str = _cell_string(cells[2] if len(cells) > 2 else None)
    last_iso: str | None = None
    if date_str:
        dt = parse_uk_day_month_year(date_str, end_of_day=False)
        if dt is not None:
            last_iso = to_iso_utc(dt.replace(hour=12, minute=0, second=0))
    return price, last_iso


async def fetch_uk_from_gviz_fallback(client: "httpx.AsyncClient") -> ParsedFuelPrices:
    """Fetch unleaded + diesel averages from two gviz endpoints."""
    unleaded_body, diesel_body = await _fetch_both(client)
    petrol, pu = parse_gviz_average(unleaded_body)
    diesel, du = parse_gviz_average(diesel_body)
    last_raw = pu or du
    return ParsedFuelPrices(
        petrol_ppl=petrol,
        diesel_ppl=diesel,
        last_update_raw=last_raw,
        source_url=UK_FALLBACK_HUMAN_PAGE,
    )


async def _fetch_both(client: "httpx.AsyncClient") -> tuple[str, str]:
    """Fetch unleaded and diesel gviz endpoints concurrently (same client timeout each)."""
    return await asyncio.gather(
        get_text(client, UK_GVIZ_UNLEADED_AVERAGE_URL),
        get_text(client, UK_GVIZ_DIESEL_AVERAGE_URL),
    )
